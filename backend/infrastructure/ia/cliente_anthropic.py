"""
Infraestrutura · IA · Cliente da Anthropic, um por chave (ANTHROPIC_API_KEY_PAGO ou _GRATIS)

    - timeout por chamada e uma nova tentativa só em erro temporário (429, 503, 529, rede), com espera curta;
    - 401 ou 403 (chave vencida, revogada ou sem permissão): não tenta de novo, desliga a chave por
      10 minutos, avisa no log com o NOME da variável (nunca o valor) e a análise usa a reserva;
    - recusa (stop_reason "refusal") e resposta cortada (max_tokens) também viram FalhaDoProvedor;
    - registra o uso de toda chamada (tokens, cache, buscas, custo estimado, tempo) e loga só isso; o custo do
      orientador (usage.iterations, no preço do modelo dele) entra no custo da chamada.
"""

import json
import logging
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import anthropic

from backend.application.ia.modelos import ContextoDaChamada, FalhaDoProvedor, UsoDeIA
from backend.application.ia.portas import RegistroDeUso
from backend.infrastructure.ia.precos import custo_anthropic

log = logging.getLogger("quickclick.ia")

DESLIGADA_POR = timedelta(minutes=10)
ESPERA_ANTES_DE_TENTAR_DE_NOVO_S = 2.0
ESPERA_MAXIMA_S = 5.0
_TEMPORARIOS = (anthropic.RateLimitError, anthropic.OverloadedError, anthropic.ServiceUnavailableError,
                anthropic.APIConnectionError, anthropic.APITimeoutError, anthropic.InternalServerError)


def agora_utc() -> datetime:
    return datetime.now(UTC)


class ClienteAnthropic:
    def __init__(self, nome_variavel: str, chave: str | None, registro: RegistroDeUso, ttl_cache: str = "5m",
                 relogio: Callable[[], datetime] = agora_utc, dormir: Callable[[float], None] = time.sleep,
                 cliente: Any = None):
        self.nome_variavel = nome_variavel
        self._chave = chave
        self._registro = registro
        self.ttl_cache = ttl_cache if ttl_cache in ("5m", "1h") else "5m"
        self._relogio = relogio
        self._dormir = dormir
        self._cliente = cliente
        self._desligada_ate: datetime | None = None
        self._trava = threading.Lock()

    def disponivel(self) -> bool:
        if not self._chave:
            return False
        with self._trava:
            return self._desligada_ate is None or self._relogio() >= self._desligada_ate

    def _obter_cliente(self):
        if self._cliente is None:
            self._cliente = anthropic.Anthropic(api_key=self._chave, max_retries=0)
        return self._cliente

    def _desligar(self, status: int) -> None:
        with self._trava:
            self._desligada_ate = self._relogio() + DESLIGADA_POR
        log.error("%s recusada (%s): chave expirada, revogada ou sem permissão. Desligada por 10 minutos; "
                  "troque no Claude Console e no App Service (ou rode python -m scripts.guardar_chave %s).",
                  self.nome_variavel, status, self.nome_variavel)

    def cache(self) -> dict[str, str]:
        return {"type": "ephemeral", "ttl": self.ttl_cache}

    def criar(self, *, contexto: ContextoDaChamada, versao_prompt: str, timeout_s: float,
              betas: list[str] | None = None, **parametros) -> Any:
        """messages.create com as regras do módulo. Devolve a Message (ou BetaMessage)."""
        if not self.disponivel():
            raise FalhaDoProvedor(self.nome_variavel, "chave ausente ou desligada")
        modelo = parametros["model"]
        cliente = self._obter_cliente()
        metodo = cliente.beta.messages.create if betas else cliente.messages.create
        extras = {"betas": betas} if betas else {}
        for tentativa in (1, 2):
            inicio = time.monotonic()
            try:
                resposta = metodo(timeout=timeout_s, **extras, **parametros)
                break
            except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as erro:
                self._desligar(erro.status_code)
                raise FalhaDoProvedor(modelo, f"chave recusada ({erro.status_code})", chave_recusada=True) from erro
            except _TEMPORARIOS as erro:
                if tentativa == 2:
                    raise FalhaDoProvedor(modelo, f"temporário: {type(erro).__name__}", temporaria=True) from erro
                self._dormir(self._espera(erro))
            except anthropic.APIStatusError as erro:
                raise FalhaDoProvedor(modelo, f"{erro.status_code}: {type(erro).__name__}") from erro
        duracao_ms = int((time.monotonic() - inicio) * 1000)
        self._registrar(resposta, contexto, versao_prompt, duracao_ms)

        if resposta.stop_reason == "refusal":
            raise FalhaDoProvedor(modelo, "recusou o pedido")
        if resposta.stop_reason == "max_tokens":
            raise FalhaDoProvedor(modelo, "resposta cortada (max_tokens)")
        return resposta

    def _espera(self, erro: Exception) -> float:
        resposta = getattr(erro, "response", None)
        try:
            pedida = float(resposta.headers.get("retry-after")) if resposta is not None else 0.0
        except (TypeError, ValueError):
            pedida = 0.0
        return min(max(pedida, ESPERA_ANTES_DE_TENTAR_DE_NOVO_S), ESPERA_MAXIMA_S)

    def _registrar(self, resposta: Any, contexto: ContextoDaChamada, versao_prompt: str, duracao_ms: int) -> None:
        uso = resposta.usage
        servidor = getattr(uso, "server_tool_use", None)
        buscas = int(getattr(servidor, "web_search_requests", 0) or 0) if servidor else 0
        entrada = int(uso.input_tokens or 0)
        saida = int(uso.output_tokens or 0)
        lido = int(uso.cache_read_input_tokens or 0)
        gravado = int(uso.cache_creation_input_tokens or 0)
        modelo = resposta.model
        orientador = _custo_do_orientador(uso, self.ttl_cache)
        registro = UsoDeIA(
            vendedor_id=contexto.vendedor_id, analise_id=contexto.analise_id, etapa=contexto.etapa,
            provedor="anthropic", modelo=modelo, versao_prompt=versao_prompt,
            tokens_entrada=entrada, tokens_saida=saida, cache_lido=lido, cache_gravado=gravado, buscas_web=buscas,
            custo_estimado_usd=custo_anthropic(modelo, entrada, saida, lido, gravado, buscas, self.ttl_cache) + orientador,
            duracao_ms=duracao_ms, criado_em=self._relogio(),
        )
        log.info("IA uso: etapa=%s modelo=%s entrada=%d saida=%d cache_lido=%d cache_gravado=%d buscas=%d "
                 "orientador_usd=%s custo_usd=%s tempo_ms=%d", registro.etapa, modelo, entrada, saida, lido, gravado,
                 buscas, orientador, registro.custo_estimado_usd, duracao_ms)
        try:
            self._registro.registrar(registro)
        except Exception as erro:  # registrar o uso nunca derruba a análise
            log.warning("Não deu para gravar o uso da IA (%s).", type(erro).__name__)


def _campo(objeto: Any, nome: str) -> Any:
    return objeto.get(nome) if isinstance(objeto, dict) else getattr(objeto, nome, None)


def _custo_do_orientador(uso: Any, ttl_cache: str) -> Decimal:
    """O orientador (advisor) roda como sub-inferência cobrada no preço do modelo dele: os tokens dele vêm só em
    usage.iterations (tipo advisor_message), fora dos totais de cima, que são só do executor."""
    total = Decimal("0")
    for iteracao in _campo(uso, "iterations") or []:
        if _campo(iteracao, "type") != "advisor_message":
            continue
        total += custo_anthropic(str(_campo(iteracao, "model") or ""), int(_campo(iteracao, "input_tokens") or 0),
                                 int(_campo(iteracao, "output_tokens") or 0),
                                 int(_campo(iteracao, "cache_read_input_tokens") or 0),
                                 int(_campo(iteracao, "cache_creation_input_tokens") or 0), 0, ttl_cache)
    return total


def texto_da_resposta(resposta: Any) -> str:
    return "".join(bloco.text for bloco in resposta.content if getattr(bloco, "type", "") == "text")


def json_da_resposta(resposta: Any, provedor: str) -> dict[str, Any]:
    """O JSON da saída estruturada (output_config.format garante o formato; mesmo assim, conferimos)."""
    texto = texto_da_resposta(resposta).strip()
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as erro:
        raise FalhaDoProvedor(provedor, "resposta fora do JSON esperado") from erro
    if not isinstance(dados, dict):
        raise FalhaDoProvedor(provedor, "resposta fora do JSON esperado")
    return dados


def entrada_da_ferramenta(resposta: Any, nome: str, provedor: str) -> dict[str, Any]:
    """A entrada da ferramenta strict que faz as vezes de saída estruturada (quando há busca na web)."""
    for bloco in resposta.content:
        if getattr(bloco, "type", "") == "tool_use" and getattr(bloco, "name", "") == nome:
            dados = bloco.input if isinstance(bloco.input, dict) else {}
            if dados:
                return dados
    # sem a chamada da ferramenta: tenta o JSON no texto (reserva, sem segunda chamada)
    return json_da_resposta(resposta, provedor)
