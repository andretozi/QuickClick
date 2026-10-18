"""
Apresentação · Rotas da API

Todas ficam debaixo de /api (o prefixo é aplicado em api.py). Cada rota só traduz
HTTP para um caso de uso e o resultado de volta para JSON: a regra mora no domínio.
"""

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from backend.application.casos_de_uso import CasosDeUso
from backend.application.portas import ServicoToken
from backend.presentation.http.autenticacao import dependencia_do_vendedor
from backend.presentation.http.esquemas import (
    ListaDeMarketplaces,
    ListaDePlanos,
    MarketplaceSaida,
    RequisicaoCadastro,
    RequisicaoConectar,
    RequisicaoLogin,
    RequisicaoTrocarPlano,
    RespostaAutenticacao,
    RespostaDeErro,
    Saude,
    UrlAutorizacaoSaida,
    UsuarioSaida,
    VendedorSaida,
    marketplace_saida,
    plano_saida,
    usuario_saida,
    vendedor_saida,
)

FINALIDADE_ESTADO_OAUTH = "estado_oauth"  # o state do OAuth não serve como token de login

ERRO_401 = {401: {"model": RespostaDeErro, "description": "Token inválido, expirado ou ausente"}}
ERRO_404 = {404: {"model": RespostaDeErro, "description": "Marketplace ou vendedor não encontrado"}}
ERROS_AO_CONECTAR = {
    **ERRO_401,
    **ERRO_404,
    400: {"model": RespostaDeErro, "description": "Código de autorização OAuth ausente"},
    403: {"model": RespostaDeErro, "description": "Limite de marketplaces do plano atingido"},
    409: {"model": RespostaDeErro, "description": "Marketplace ainda em breve"},
}
ERROS_CADASTRO = {
    400: {"model": RespostaDeErro, "description": "Dados de cadastro inválidos"},
    409: {"model": RespostaDeErro, "description": "Email já cadastrado"},
}
ERROS_LOGIN = {
    401: {"model": RespostaDeErro, "description": "Email ou senha incorretos"},
}


def criar_rotas(
    casos: CasosDeUso,
    identificar_vendedor: Callable[..., int] | None = None,
    servico_token: ServicoToken | None = None,
) -> APIRouter:
    rotas = APIRouter()
    VendedorAtual = Annotated[int, Depends(dependencia_do_vendedor(servico_token, identificar_vendedor))]

    # -----------------------------------------------------------------------
    # Sistema
    # -----------------------------------------------------------------------

    @rotas.get("/health", tags=["sistema"], summary="Confere se a API está no ar", response_model=Saude)
    def health() -> Saude:
        return Saude(status="ok")

    @rotas.get("/plans", tags=["planos"], summary="Planos de assinatura, do Grátis ao Business", response_model=ListaDePlanos)
    def listar_planos() -> ListaDePlanos:
        livre = casos.trocar_plano.livre if casos.trocar_plano is not None else False
        return ListaDePlanos(planos=[plano_saida(plano) for plano in casos.listar_planos.executar()],
                             troca_de_plano_livre=livre)

    # -----------------------------------------------------------------------
    # Autenticação (JWT)
    # -----------------------------------------------------------------------

    @rotas.post(
        "/auth/register",
        tags=["autenticacao"],
        summary="Cria uma nova conta e devolve o token JWT",
        response_model=RespostaAutenticacao,
        responses=ERROS_CADASTRO,
    )
    @rotas.post("/contas", include_in_schema=False)
    def cadastrar(dados: RequisicaoCadastro) -> RespostaAutenticacao:
        if casos.registrar_usuario is None:
            raise HTTPException(status_code=501, detail="Serviço de cadastro não disponível.")
        resultado = casos.registrar_usuario.executar(
            nome=dados.nome,
            email=dados.email,
            loja=dados.loja,
            senha=dados.senha,
            maior_de_idade=dados.maior_de_idade,
        )
        return RespostaAutenticacao(
            token=resultado.token,
            usuario=usuario_saida(resultado.usuario),
        )

    @rotas.post(
        "/auth/login",
        tags=["autenticacao"],
        summary="Autentica com email e senha e devolve o token JWT",
        response_model=RespostaAutenticacao,
        responses=ERROS_LOGIN,
    )
    @rotas.post("/sessao", include_in_schema=False)
    def login(dados: RequisicaoLogin) -> RespostaAutenticacao:
        if casos.autenticar_usuario is None:
            raise HTTPException(status_code=501, detail="Serviço de autenticação não disponível.")
        resultado = casos.autenticar_usuario.executar(
            email=dados.email,
            senha=dados.senha,
        )
        return RespostaAutenticacao(
            token=resultado.token,
            usuario=usuario_saida(resultado.usuario),
        )

    @rotas.get(
        "/auth/me",
        tags=["autenticacao"],
        summary="Retorna os dados do usuário atual autenticado via token JWT",
        response_model=UsuarioSaida,
        responses={**ERRO_401, **ERRO_404},
    )
    def usuario_atual(vendedor_id: VendedorAtual) -> UsuarioSaida:
        if casos.obter_usuario_atual is None:
            raise HTTPException(status_code=501, detail="Serviço indisponível.")
        return usuario_saida(casos.obter_usuario_atual.executar(vendedor_id))

    # -----------------------------------------------------------------------
    # Vendedor e Marketplaces (Rotas Protegidas por JWT)
    # -----------------------------------------------------------------------

    @rotas.get(
        "/me",
        tags=["vendedor"],
        summary="Vendedor atual autenticado pelo token JWT",
        response_model=VendedorSaida,
        responses={**ERRO_401, **ERRO_404},
    )
    def vendedor_atual(vendedor_id: VendedorAtual) -> VendedorSaida:
        return vendedor_saida(casos.obter_vendedor_atual.executar(vendedor_id))

    @rotas.put(
        "/me/plano",
        tags=["vendedor"],
        summary="O vendedor do token troca o próprio plano (MVP: na hora e sem pagamento)",
        response_model=UsuarioSaida,
        responses={
            **ERRO_401,
            **ERRO_404,
            400: {"model": RespostaDeErro, "description": "Plano que não existe"},
            402: {"model": RespostaDeErro, "description": "Troca livre desligada (TROCA_DE_PLANO_LIVRE=false)"},
        },
    )
    def trocar_plano(dados: RequisicaoTrocarPlano, vendedor_id: VendedorAtual) -> UsuarioSaida:
        if casos.trocar_plano is None:
            raise HTTPException(status_code=501, detail="Serviço indisponível.")
        return usuario_saida(casos.trocar_plano.executar(vendedor_id, dados.plano))

    @rotas.get(
        "/marketplaces",
        tags=["marketplaces"],
        summary="Catálogo de marketplaces, com o que o vendedor já conectou",
        response_model=ListaDeMarketplaces,
        responses=ERRO_401,
    )
    def listar_marketplaces(vendedor_id: VendedorAtual) -> ListaDeMarketplaces:
        itens = casos.listar_marketplaces.executar(vendedor_id)
        return ListaDeMarketplaces(marketplaces=[marketplace_saida(item) for item in itens])

    @rotas.get(
        "/marketplaces/{slug}/authorize-url",
        tags=["marketplaces"],
        summary="Gera a URL de consentimento OAuth oficial no marketplace",
        response_model=UrlAutorizacaoSaida,
        responses=ERROS_AO_CONECTAR,
    )
    def obter_url_autorizacao(slug: str, vendedor_id: VendedorAtual) -> UrlAutorizacaoSaida:
        estado = (
            servico_token.gerar_token(user_id=vendedor_id, email=f"oauth:{slug}", finalidade=FINALIDADE_ESTADO_OAUTH)
            if servico_token is not None
            else str(vendedor_id)
        )
        url = casos.conectar_marketplace.gerar_url_autorizacao(vendedor_id, slug, estado)
        return UrlAutorizacaoSaida(url=url)

    @rotas.get(
        "/marketplaces/{slug}/callback",
        tags=["marketplaces"],
        summary="Callback OAuth 2.0 que recebe o retorno de autorização do marketplace",
    )
    def callback_marketplace(
        slug: str,
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
        error_description: str | None = None,
    ) -> RedirectResponse:
        if error:
            return RedirectResponse(url=f"/#/marketplaces?erro={error}", status_code=302)

        if not code or not state:
            return RedirectResponse(url="/#/marketplaces?erro=parametros_invalidos", status_code=302)

        vendedor_id = None
        if servico_token is not None:
            try:
                payload = servico_token.validar_token(state, finalidade=FINALIDADE_ESTADO_OAUTH)
                vendedor_id = int(payload["sub"])
            except Exception:
                return RedirectResponse(url="/#/marketplaces?erro=state_invalido", status_code=302)
        elif state.isdigit():
            vendedor_id = int(state)

        if vendedor_id is None:
            return RedirectResponse(url="/#/marketplaces?erro=nao_autenticado", status_code=302)

        try:
            casos.conectar_marketplace.executar(vendedor_id, slug, codigo_autorizacao=code)
            return RedirectResponse(url=f"/#/marketplaces?conectado={slug}", status_code=302)
        except Exception as erro:
            return RedirectResponse(url=f"/#/marketplaces?erro={str(erro)}", status_code=302)

    @rotas.post(
        "/marketplaces/{slug}/connection",
        tags=["marketplaces"],
        summary="Conecta uma conta que o vendedor já tem no marketplace",
        response_model=MarketplaceSaida,
        responses=ERROS_AO_CONECTAR,
    )
    def conectar(
        slug: str,
        vendedor_id: VendedorAtual,
        dados: RequisicaoConectar | None = None,
    ) -> MarketplaceSaida:
        codigo = dados.codigo_autorizacao if dados and dados.codigo_autorizacao else ""
        return marketplace_saida(
            casos.conectar_marketplace.executar(vendedor_id, slug, codigo_autorizacao=codigo)
        )

    @rotas.delete(
        "/marketplaces/{slug}/connection",
        tags=["marketplaces"],
        summary="Desconecta o marketplace e libera a vaga do plano",
        response_model=MarketplaceSaida,
        responses={**ERRO_401, **ERRO_404},
    )
    def desconectar(slug: str, vendedor_id: VendedorAtual) -> MarketplaceSaida:
        return marketplace_saida(casos.desconectar_marketplace.executar(vendedor_id, slug))

    @rotas.get(
        "/marketplaces/{slug}/products",
        tags=["marketplaces"],
        summary="Lista os produtos/anúncios do marketplace para monitoramento",
        responses={**ERRO_401, **ERRO_404},
    )
    def listar_produtos(slug: str, vendedor_id: VendedorAtual) -> list[dict[str, Any]]:
        return casos.conectar_marketplace.listar_produtos(vendedor_id, slug)

    # POST /marketplaces/{slug}/products (publicava um dict qualquer) foi desativada: a publicação agora
    # é montada no back, em POST /api/anuncios/publicar/mercado-livre (rotas_anuncios.py).

    return rotas
