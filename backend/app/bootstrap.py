"""
Raiz de composição do back.

Liga as camadas e devolve a aplicação FastAPI pronta: a API em /api e o front
buildado (frontend/dist) no resto dos endereços. O main.py chama criar_app().
A configuração vem do módulo único (backend/infrastructure/configuracao) e as tabelas
são criadas pelas migrações do Alembic, que o main.py roda antes de subir o servidor.
"""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from fastapi import FastAPI
from sqlalchemy.orm import Session

from backend.application.casos_de_uso import (
    AutenticarUsuario,
    CasosDeUso,
    ConectarMarketplace,
    DesconectarMarketplace,
    GerenciarProdutos,
    ListarMarketplaces,
    ListarPlanos,
    ObterUsuarioAtual,
    ObterVendedorAtual,
    PublicarNoMercadoLivre,
    RegistrarUsuario,
    TrocarPlano,
)
from backend.application.ia.contas import ContasPelosCasosDeUso
from backend.application.ia.escolha import ProvedoresDeIA
from backend.application.ia.etapas import DependenciasDaAnalise
from backend.application.ia.modelos import ConfiguracaoDaIA
from backend.application.ia.portas import Executor, FontePrecosMarketplace
from backend.application.ia.servico import ServicoDeAnalises
from backend.domain.ia.capacidade import ORCAMENTO_DIARIO_PADRAO_USD
from backend.infrastructure.banco import models  # noqa: F401
from backend.infrastructure.banco.repositorio_contas import RepositorioContasVinculadasSQL
from backend.infrastructure.banco.repositorio_ia import (
    CacheDeCategoriasMLSQL,
    CacheDePesquisasSQL,
    RegistroDeUsoSQL,
    RepositorioDeAnalisesSQL,
)
from backend.infrastructure.banco.repositorio_produtos import RepositorioDeProdutosSQL
from backend.infrastructure.banco.repositorio_usuarios import RepositorioUsuariosSQL
from backend.infrastructure.banco.repositorio_vendedores import RepositorioVendedoresSQL
from backend.infrastructure.configuracao import (
    RAIZ_DO_PROJETO,
    Config,
    LeitorDeConfiguracao,
    carregar_config,
    configuracao,
    segredo_jwt,
)
from backend.infrastructure.database import SessionLocal
from backend.infrastructure.ia.fabrica import criar_provedores
from backend.infrastructure.ia.preparador_pillow import PillowPreparador
from backend.infrastructure.ia.sem_tratamento import SemTratamento, SemVerificacaoDeFidelidade
from backend.infrastructure.marketplaces.fonte_precos_ml import FontePrecosMercadoLivre
from backend.infrastructure.marketplaces.registro import criar_gateways
from backend.infrastructure.seguranca.cripto_tokens import CifradorDeTokens
from backend.infrastructure.seguranca.hasher import HasherPBKDF2
from backend.infrastructure.seguranca.token_jwt import ServicoJWT
from backend.presentation.http.api import criar_api
from backend.presentation.http.front import montar_front

log = logging.getLogger("quickclick.app")

TRABALHADORES_DA_ANALISE = 2  # uma instância só no App Service: poucas análises ao mesmo tempo


def agora_utc() -> datetime:
    return datetime.now(UTC)


def configuracao_da_ia(leitor: LeitorDeConfiguracao) -> ConfiguracaoDaIA:
    return ConfiguracaoDaIA(
        ia_ativa=leitor.booleano("IA_ATIVA", True),
        pesquisa_web_ativa=leitor.booleano("PESQUISA_WEB_ATIVA", True),
        tratamento_foto_ativo=leitor.booleano("TRATAMENTO_FOTO_ATIVO", False),
        orcamento_diario_usd=leitor.decimal("IA_ORCAMENTO_DIARIO_USD", ORCAMENTO_DIARIO_PADRAO_USD),
    )


def criar_app(
    config: Config | None = None,
    session_factory: Callable[[], Session] = SessionLocal,
    identificar_vendedor=None,
    leitor: LeitorDeConfiguracao | None = None,
    provedores: ProvedoresDeIA | None = None,
    fonte_ml: FontePrecosMarketplace | None = None,
    executor: Executor | None = None,
    relogio: Callable[[], datetime] = agora_utc,
) -> FastAPI:
    """Os parâmetros opcionais existem para os testes (provedores falsos, sem rede, e executor na hora)."""
    leitor = leitor or configuracao()
    config = config or carregar_config(RAIZ_DO_PROJETO)

    cifrador = CifradorDeTokens(leitor.texto("TOKENS_CHAVE_CRIPTO"))
    vendedores = RepositorioVendedoresSQL(session_factory)
    contas = RepositorioContasVinculadasSQL(session_factory, cifrador)
    usuarios = RepositorioUsuariosSQL(session_factory)

    hasher = HasherPBKDF2()
    token_service = ServicoJWT(segredo_jwt(leitor))
    gateways = criar_gateways(leitor)
    conectar = ConectarMarketplace(vendedores, contas, gateways)

    registro_de_uso = RegistroDeUsoSQL(session_factory)
    if fonte_ml is None:
        fonte_ml = FontePrecosMercadoLivre(gateways["mercado-livre"], CacheDeCategoriasMLSQL(session_factory),
                                           relogio=relogio)
    executor_padrao = executor is None
    executor = executor or ThreadPoolExecutor(max_workers=TRABALHADORES_DA_ANALISE, thread_name_prefix="analise")
    analises = RepositorioDeAnalisesSQL(session_factory)
    preparador = PillowPreparador()
    analises_ia = ServicoDeAnalises(
        DependenciasDaAnalise(
            analises=analises,
            preparador=preparador,
            tratador=SemTratamento(),
            guardiao=SemVerificacaoDeFidelidade(),
            provedores=provedores if provedores is not None else criar_provedores(leitor, registro_de_uso),
            fonte_ml=fonte_ml,
            contas=ContasPelosCasosDeUso(contas, conectar),
            pesquisas=CacheDePesquisasSQL(session_factory),
            config=configuracao_da_ia(leitor),
            relogio=relogio,
            fontes_de_esquema={"mercado-livre": fonte_ml},
            orcamento=registro_de_uso,
        ),
        vendedores=vendedores,
        orcamento=registro_de_uso,
        executor=executor,
    )
    try:
        analises_ia.ao_iniciar()
    except Exception as erro:  # banco fora do ar na partida: o site sobe e o que usa o banco avisa
        log.warning("Não deu para conferir as análises interrompidas (%s).", type(erro).__name__)

    casos = CasosDeUso(
        listar_planos=ListarPlanos(),
        obter_vendedor_atual=ObterVendedorAtual(vendedores, contas),
        listar_marketplaces=ListarMarketplaces(contas),
        conectar_marketplace=conectar,
        desconectar_marketplace=DesconectarMarketplace(contas),
        autenticar_usuario=AutenticarUsuario(usuarios, hasher, token_service),
        registrar_usuario=RegistrarUsuario(usuarios, hasher, token_service),
        obter_usuario_atual=ObterUsuarioAtual(usuarios),
        trocar_plano=TrocarPlano(vendedores, usuarios, livre=leitor.booleano("TROCA_DE_PLANO_LIVRE", True)),
        analises_ia=analises_ia,
        publicar_no_mercado_livre=PublicarNoMercadoLivre(conectar, gateways["mercado-livre"], fonte_ml, analises,
                                                         preparador),
        produtos=GerenciarProdutos(RepositorioDeProdutosSQL(session_factory), relogio),
    )

    documentacao_ativa = leitor.booleano("DOCUMENTACAO_API_ATIVA", False)
    app = criar_api(
        casos,
        identificar_vendedor=identificar_vendedor,
        servico_token=token_service,
        documentacao_ativa=documentacao_ativa,
    )
    if executor_padrao:
        app.router.on_shutdown.append(lambda: executor.shutdown(wait=False, cancel_futures=True))
    montar_front(app, config.pasta_front)
    return app
