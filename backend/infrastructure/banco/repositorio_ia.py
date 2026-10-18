"""
Infraestrutura · Banco · Análises da IA, uso das IAs (e o orçamento do dia) e os caches

Datas em UTC no banco. "Mês" da cota e "dia" do orçamento contam no horário de Brasília
(UTC−3, sem horário de verão desde 2019). O SQLite dos testes devolve datas sem fuso: valem como UTC.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.application.ia.modelos import UsoDeIA
from backend.domain.ia.analise import EM_PROCESSAMENTO, TEMPO_PARA_CONSIDERAR_PARADA, StatusAnalise
from backend.infrastructure.banco.models import AnaliseIAModel, CategoriaMLCacheModel, PesquisaMercadoModel, UsoIAModel
from backend.infrastructure.database import SessionLocal

BRASILIA = timezone(timedelta(hours=-3))
CAMPOS_DA_ANALISE = (
    "id", "vendedor_id", "plano_no_momento", "nivel", "status", "etapa_atual", "fotos_meta", "leitura",
    "atributos_confirmados", "ml_categoria_id", "pesquisa_chave", "preco", "texto", "canais", "avisos",
    "erro_codigo", "erro_mensagem_usuario", "criado_em", "atualizado_em", "concluida_em",
)


def _utc(valor: datetime | None) -> datetime | None:
    if valor is None:
        return None
    return valor.replace(tzinfo=UTC) if valor.tzinfo is None else valor.astimezone(UTC)


def inicio_do_mes(agora: datetime) -> datetime:
    local = agora.astimezone(BRASILIA)
    return local.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


def inicio_do_dia(agora: datetime) -> datetime:
    local = agora.astimezone(BRASILIA)
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


class RepositorioDeAnalisesSQL:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal):
        self._session_factory = session_factory

    def criar(self, dados: dict[str, Any]) -> None:
        with self._session_factory() as session:
            session.add(AnaliseIAModel(**{k: v for k, v in dados.items() if k in CAMPOS_DA_ANALISE}))
            session.commit()

    def obter(self, analise_id: str) -> dict[str, Any] | None:
        with self._session_factory() as session:
            linha = session.get(AnaliseIAModel, analise_id)
            if linha is None:
                return None
            dados = {campo: getattr(linha, campo) for campo in CAMPOS_DA_ANALISE}
            for campo in ("criado_em", "atualizado_em", "concluida_em"):
                dados[campo] = _utc(dados[campo])
            return dados

    def atualizar(self, analise_id: str, campos: dict[str, Any]) -> None:
        with self._session_factory() as session:
            linha = session.get(AnaliseIAModel, analise_id)
            if linha is None:
                return
            for campo, valor in campos.items():
                if campo in CAMPOS_DA_ANALISE and campo != "id":
                    setattr(linha, campo, valor)
            session.commit()

    def prontas_no_mes(self, vendedor_id: int, agora: datetime) -> int:
        with self._session_factory() as session:
            return session.query(func.count(AnaliseIAModel.id)).filter(
                AnaliseIAModel.vendedor_id == vendedor_id,
                AnaliseIAModel.status == StatusAnalise.PRONTA.value,
                AnaliseIAModel.concluida_em >= inicio_do_mes(agora),
            ).scalar() or 0

    def em_andamento(self, vendedor_id: int) -> int:
        with self._session_factory() as session:
            return session.query(func.count(AnaliseIAModel.id)).filter(
                AnaliseIAModel.vendedor_id == vendedor_id,
                AnaliseIAModel.status.in_([s.value for s in EM_PROCESSAMENTO]),
            ).scalar() or 0

    def criadas_desde(self, vendedor_id: int, desde: datetime) -> int:
        with self._session_factory() as session:
            return session.query(func.count(AnaliseIAModel.id)).filter(
                AnaliseIAModel.vendedor_id == vendedor_id, AnaliseIAModel.criado_em >= desde,
            ).scalar() or 0

    def marcar_paradas_como_interrompidas(self, agora: datetime) -> int:
        limite = agora - TEMPO_PARA_CONSIDERAR_PARADA
        with self._session_factory() as session:
            linhas = session.query(AnaliseIAModel).filter(
                AnaliseIAModel.status.in_([s.value for s in EM_PROCESSAMENTO]),
                AnaliseIAModel.atualizado_em < limite,
            ).all()
            for linha in linhas:
                linha.etapa_atual = linha.etapa_atual or linha.status
                linha.status = StatusAnalise.INTERROMPIDA.value
                linha.atualizado_em = agora
            session.commit()
            return len(linhas)


class RegistroDeUsoSQL:
    """Grava cada chamada em ia_uso e soma o gasto do dia para o orçamento."""

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal):
        self._session_factory = session_factory

    def registrar(self, uso: UsoDeIA) -> None:
        with self._session_factory() as session:
            session.add(UsoIAModel(
                vendedor_id=uso.vendedor_id, analise_id=uso.analise_id, etapa=uso.etapa, provedor=uso.provedor,
                modelo=uso.modelo, versao_prompt=uso.versao_prompt, tokens_entrada=uso.tokens_entrada,
                tokens_saida=uso.tokens_saida, cache_lido=uso.cache_lido, cache_gravado=uso.cache_gravado,
                buscas_web=uso.buscas_web, custo_estimado_usd=uso.custo_estimado_usd, duracao_ms=uso.duracao_ms,
                criado_em=uso.criado_em,
            ))
            session.commit()

    def gasto_de_hoje_usd(self, agora: datetime) -> Decimal:
        with self._session_factory() as session:
            total = session.query(func.coalesce(func.sum(UsoIAModel.custo_estimado_usd), 0)).filter(
                UsoIAModel.criado_em >= inicio_do_dia(agora)
            ).scalar()
            return Decimal(str(total or 0))


class CacheDePesquisasSQL:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal):
        self._session_factory = session_factory

    def obter(self, chave: str, agora: datetime) -> dict[str, Any] | None:
        with self._session_factory() as session:
            linha = session.get(PesquisaMercadoModel, chave)
            if linha is None or _utc(linha.expira_em) <= agora:
                return None
            return {**(linha.conteudo or {}), "fontes": list(linha.fontes or [])}

    def salvar(self, chave: str, conteudo: dict[str, Any], fontes: list[str], agora: datetime,
               expira_em: datetime) -> None:
        with self._session_factory() as session:
            linha = session.get(PesquisaMercadoModel, chave) or PesquisaMercadoModel(chave=chave)
            linha.conteudo = {k: v for k, v in conteudo.items() if k != "fontes"}
            linha.fontes = list(fontes)
            linha.criado_em = agora
            linha.expira_em = expira_em
            session.merge(linha)
            session.commit()


class CacheDeCategoriasMLSQL:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal):
        self._session_factory = session_factory

    def obter(self, categoria_id: str, agora: datetime) -> list[dict[str, Any]] | None:
        with self._session_factory() as session:
            linha = session.get(CategoriaMLCacheModel, categoria_id)
            if linha is None or _utc(linha.expira_em) <= agora:
                return None
            return list(linha.atributos or [])

    def salvar(self, categoria_id: str, atributos: list[dict[str, Any]], expira_em: datetime) -> None:
        with self._session_factory() as session:
            linha = session.get(CategoriaMLCacheModel, categoria_id) or CategoriaMLCacheModel(categoria_id=categoria_id)
            linha.atributos = atributos
            linha.expira_em = expira_em
            session.merge(linha)
            session.commit()
