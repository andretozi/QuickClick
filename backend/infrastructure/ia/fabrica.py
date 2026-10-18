"""
Infraestrutura · IA · Monta os provedores a partir da configuração

Interruptores (variáveis de ambiente; o App Service reinicia a aplicação quando elas mudam):
    IA_ATIVA (true)            false: nenhum provedor, todos os campos manuais abertos
    PESQUISA_WEB_ATIVA (true)  false: pesquisa e preço sem busca na web
    ADVISOR_ATIVO (false)      true: orientador (Opus) na pesquisa de mercado
    IA_CACHE_TTL (5m)          5m ou 1h
Modelos: MODELO_VISAO, MODELO_TEXTO, MODELO_RAPIDO, MODELO_GEMINI_TEXTO (padrões no catálogo).
Sem a chave, o provedor não nasce e o log diz qual variável falta.
"""

import logging

from backend.application.ia.escolha import ProvedoresDeIA
from backend.application.ia.portas import RegistroDeUso
from backend.infrastructure.configuracao import LeitorDeConfiguracao
from backend.infrastructure.ia.anthropic_ia import (
    AnthropicLeitor,
    AnthropicLigador,
    AnthropicPesquisador,
    AnthropicPrecificador,
    AnthropicPrecosNaWeb,
    AnthropicRedator,
)
from backend.infrastructure.ia.carregador_de_prompts import carregar_prompts
from backend.infrastructure.ia.cliente_anthropic import ClienteAnthropic
from backend.infrastructure.ia.cliente_gemini import ClienteGemini
from backend.infrastructure.ia.gemini_ia import GeminiLeitor, GeminiRedator

log = logging.getLogger("quickclick.ia")


def criar_provedores(leitor: LeitorDeConfiguracao, registro: RegistroDeUso) -> ProvedoresDeIA:
    if not leitor.booleano("IA_ATIVA", True):
        log.warning("IA desligada (IA_ATIVA=false): o criar anúncio fica só com os campos manuais.")
        return ProvedoresDeIA()
    carregar_prompts()  # uma vez, na partida

    ttl = leitor.texto("IA_CACHE_TTL")
    visao, texto, rapido, gemini = (leitor.texto(n) for n in
                                    ("MODELO_VISAO", "MODELO_TEXTO", "MODELO_RAPIDO", "MODELO_GEMINI_TEXTO"))
    com_web = leitor.booleano("PESQUISA_WEB_ATIVA", True)
    orientador = visao if leitor.booleano("ADVISOR_ATIVO", False) else None

    pago = ClienteAnthropic("ANTHROPIC_API_KEY_PAGO", leitor.texto("ANTHROPIC_API_KEY_PAGO"), registro, ttl)
    gratis = ClienteAnthropic("ANTHROPIC_API_KEY_GRATIS", leitor.texto("ANTHROPIC_API_KEY_GRATIS"), registro, ttl)
    gemini_gratis = ClienteGemini("GEMINI_API_KEY_GRATIS", leitor.texto("GEMINI_API_KEY_GRATIS"), registro)

    if not pago.disponivel():
        log.warning("IA paga desligada: falta ANTHROPIC_API_KEY_PAGO.")
    if not gemini_gratis.disponivel():
        log.warning("Gemini do plano Grátis desligado: falta GEMINI_API_KEY_GRATIS (a reserva é o Haiku).")
    if not gratis.disponivel():
        log.warning("Reserva do plano Grátis (Haiku) desligada: falta ANTHROPIC_API_KEY_GRATIS.")
    if not com_web:
        log.info("Busca na web desligada (PESQUISA_WEB_ATIVA=false).")

    return ProvedoresDeIA(
        leitor_visao_pago=AnthropicLeitor(pago, visao, effort_leitura="high", effort_releitura="medium"),
        leitor_rapido_pago=AnthropicLeitor(pago, rapido, effort_leitura="low", effort_releitura="low"),
        leitor_gemini_gratis=GeminiLeitor(gemini_gratis, gemini),
        leitor_rapido_gratis=AnthropicLeitor(gratis, rapido, effort_leitura="low", effort_releitura="low"),
        pesquisador_pago=AnthropicPesquisador(pago, texto, com_web=com_web, orientador=orientador, effort="medium"),
        pesquisador_rapido_pago=AnthropicPesquisador(pago, rapido, com_web=False, effort="low"),
        pesquisador_gratis=AnthropicPesquisador(gratis, rapido, com_web=False, effort="low"),
        precificador_pago=AnthropicPrecificador(pago, visao, effort="medium"),
        precos_na_web_pago=AnthropicPrecosNaWeb(pago, texto) if com_web else None,
        redator_pago=AnthropicRedator(pago, texto, effort="medium"),
        redator_rapido_pago=AnthropicRedator(pago, rapido, effort="low"),
        redator_gemini_gratis=GeminiRedator(gemini_gratis, gemini),
        redator_rapido_gratis=AnthropicRedator(gratis, rapido, effort="low"),
        ligador_pago=AnthropicLigador(pago, rapido),
        ligador_gratis=AnthropicLigador(gratis, rapido),
    )
