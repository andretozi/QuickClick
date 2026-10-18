"""
Domínio · IA · Estados da análise

    recebida → preparando_fotos → [tratando_fotos → verificando_fotos] → lendo_produto
    → aguardando_confirmacao → pesquisando_mercado → precificando → escrevendo → pronta

tratando_fotos e verificando_fotos são da versão final (TRATAMENTO_FOTO_ATIVO): no MVP o
orquestrador passa por elas sem gravar. Qualquer estado em processamento pode virar falhou
(erro do provedor sem reserva) ou interrompida (o servidor reiniciou no meio).
"""

from datetime import datetime, timedelta
from enum import StrEnum


class StatusAnalise(StrEnum):
    RECEBIDA = "recebida"
    PREPARANDO_FOTOS = "preparando_fotos"
    TRATANDO_FOTOS = "tratando_fotos"  # versão final
    VERIFICANDO_FOTOS = "verificando_fotos"  # versão final
    LENDO_PRODUTO = "lendo_produto"
    AGUARDANDO_CONFIRMACAO = "aguardando_confirmacao"
    PESQUISANDO_MERCADO = "pesquisando_mercado"
    PRECIFICANDO = "precificando"
    ESCREVENDO = "escrevendo"
    PRONTA = "pronta"
    FALHOU = "falhou"
    INTERROMPIDA = "interrompida"


class Nivel(StrEnum):
    GRATIS = "gratis"
    PAGO = "pago"


# Ordem das etapas que trabalham (sem os estados de parada)
ETAPAS: tuple[StatusAnalise, ...] = (
    StatusAnalise.RECEBIDA,
    StatusAnalise.PREPARANDO_FOTOS,
    StatusAnalise.TRATANDO_FOTOS,
    StatusAnalise.VERIFICANDO_FOTOS,
    StatusAnalise.LENDO_PRODUTO,
    StatusAnalise.AGUARDANDO_CONFIRMACAO,
    StatusAnalise.PESQUISANDO_MERCADO,
    StatusAnalise.PRECIFICANDO,
    StatusAnalise.ESCREVENDO,
    StatusAnalise.PRONTA,
)

FINAIS = frozenset({StatusAnalise.PRONTA, StatusAnalise.FALHOU, StatusAnalise.INTERROMPIDA})

# Estados em que o processo trabalha em segundo plano (contam para "uma análise por vez")
EM_PROCESSAMENTO = frozenset({
    StatusAnalise.RECEBIDA,
    StatusAnalise.PREPARANDO_FOTOS,
    StatusAnalise.TRATANDO_FOTOS,
    StatusAnalise.VERIFICANDO_FOTOS,
    StatusAnalise.LENDO_PRODUTO,
    StatusAnalise.PESQUISANDO_MERCADO,
    StatusAnalise.PRECIFICANDO,
    StatusAnalise.ESCREVENDO,
})

# Até aqui as fotos ainda são necessárias (a leitura não terminou)
ANTES_DA_LEITURA = frozenset({
    StatusAnalise.RECEBIDA,
    StatusAnalise.PREPARANDO_FOTOS,
    StatusAnalise.TRATANDO_FOTOS,
    StatusAnalise.VERIFICANDO_FOTOS,
    StatusAnalise.LENDO_PRODUTO,
})

TEMPO_PARA_CONSIDERAR_PARADA = timedelta(minutes=10)


def posicao(status: StatusAnalise) -> int:
    return ETAPAS.index(status) if status in ETAPAS else -1


def esta_em_processamento(status: StatusAnalise) -> bool:
    return status in EM_PROCESSAMENTO


def pode_confirmar(status: StatusAnalise) -> bool:
    return status is StatusAnalise.AGUARDANDO_CONFIRMACAO


def pode_receber_foto_extra(status: StatusAnalise) -> bool:
    return status is StatusAnalise.AGUARDANDO_CONFIRMACAO


def pode_retomar(status: StatusAnalise) -> bool:
    return status in (StatusAnalise.FALHOU, StatusAnalise.INTERROMPIDA)


def retomada_precisa_de_fotos(etapa_atual: StatusAnalise | None, tem_leitura: bool) -> bool:
    """Parou antes de a leitura terminar: o front reenvia as fotos que ainda tem no rascunho."""
    if tem_leitura:
        return False
    return etapa_atual is None or etapa_atual in ANTES_DA_LEITURA


def etapa_de_retomada(etapa_atual: StatusAnalise | None, tem_leitura: bool,
                      tem_confirmacao: bool) -> StatusAnalise:
    """De onde a análise continua depois de falhar ou ser interrompida."""
    if not tem_leitura:
        return StatusAnalise.PREPARANDO_FOTOS
    if not tem_confirmacao:
        return StatusAnalise.AGUARDANDO_CONFIRMACAO
    if etapa_atual in (StatusAnalise.PRECIFICANDO, StatusAnalise.ESCREVENDO):
        return etapa_atual
    return StatusAnalise.PESQUISANDO_MERCADO


def esta_parada(status: StatusAnalise, atualizado_em: datetime, agora: datetime) -> bool:
    """Em processamento e sem notícia há mais de 10 minutos: o servidor reiniciou no meio."""
    return status in EM_PROCESSAMENTO and agora - atualizado_em > TEMPO_PARA_CONSIDERAR_PARADA
