"""
Infraestrutura · IA · Cliente do Gemini (Google AI Studio), um por chave (GEMINI_API_KEY_GRATIS)

Mesmas regras do cliente da Anthropic: timeout, uma nova tentativa só em erro temporário
(429 fica de fora: na camada grátis ele quer dizer limite do dia, e a reserva é o Haiku),
chave recusada desliga por 10 minutos com aviso pelo nome da variável, e registro de uso.
Na camada grátis o custo é zero. O Google pode usar o que é enviado na camada grátis para
melhorar os produtos dele: por isso as fotos chegam aqui sem metadados e a tela avisa.
"""

import json
import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from backend.application.ia.modelos import ContextoDaChamada, FalhaDoProvedor, UsoDeIA
from backend.application.ia.portas import RegistroDeUso
from backend.infrastructure.ia.cliente_anthropic import agora_utc

log = logging.getLogger("quickclick.ia")

DESLIGADA_POR = timedelta(minutes=10)
ESPERA_S = 2.0
TEMPORARIOS = {500, 503, 504}


def esquema_para_gemini(esquema: dict[str, Any]) -> dict[str, Any]:
    """O mesmo JSON Schema, sem additionalProperties (o Gemini aceita só um subconjunto do padrão)."""
    if isinstance(esquema, dict):
        return {k: esquema_para_gemini(v) for k, v in esquema.items() if k != "additionalProperties"}
    if isinstance(esquema, list):
        return [esquema_para_gemini(v) for v in esquema]
    return esquema


class ClienteGemini:
    def __init__(self, nome_variavel: str, chave: str | None, registro: RegistroDeUso,
                 relogio: Callable[[], datetime] = agora_utc, dormir: Callable[[float], None] = time.sleep,
                 cliente: Any = None):
        self.nome_variavel = nome_variavel
        self._chave = chave
        self._registro = registro
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
            from google import genai

            self._cliente = genai.Client(api_key=self._chave)
        return self._cliente

    def gerar_json(self, *, modelo: str, partes: list[Any], sistema: str, esquema: dict[str, Any],
                   contexto: ContextoDaChamada, versao_prompt: str, timeout_s: float,
                   max_tokens: int = 8000) -> dict[str, Any]:
        if not self.disponivel():
            raise FalhaDoProvedor(self.nome_variavel, "chave ausente ou desligada")
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=sistema,
            response_mime_type="application/json",
            response_json_schema=esquema_para_gemini(esquema),
            max_output_tokens=max_tokens,
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
            http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),
        )
        for tentativa in (1, 2):
            inicio = time.monotonic()
            try:
                resposta = self._obter_cliente().models.generate_content(model=modelo, contents=partes, config=config)
                break
            except errors.APIError as erro:
                if erro.code in (401, 403) or (erro.code == 400 and "api key" in str(erro).lower()):
                    with self._trava:
                        self._desligada_ate = self._relogio() + DESLIGADA_POR
                    log.error("%s recusada (%s): chave inválida ou sem permissão. Desligada por 10 minutos.",
                              self.nome_variavel, erro.code)
                    raise FalhaDoProvedor(modelo, f"chave recusada ({erro.code})", chave_recusada=True) from erro
                if erro.code == 429:
                    raise FalhaDoProvedor(modelo, "limite da camada grátis (429)", temporaria=True) from erro
                if erro.code in TEMPORARIOS and tentativa == 1:
                    self._dormir(ESPERA_S)
                    continue
                raise FalhaDoProvedor(modelo, f"{erro.code}: {type(erro).__name__}") from erro
            except Exception as erro:  # rede e timeout
                if tentativa == 1:
                    self._dormir(ESPERA_S)
                    continue
                raise FalhaDoProvedor(modelo, f"temporário: {type(erro).__name__}", temporaria=True) from erro
        self._registrar(resposta, modelo, contexto, versao_prompt, int((time.monotonic() - inicio) * 1000))

        texto = (getattr(resposta, "text", None) or "").strip()
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError as erro:
            raise FalhaDoProvedor(modelo, "resposta fora do JSON esperado (ou cortada)") from erro
        if not isinstance(dados, dict):
            raise FalhaDoProvedor(modelo, "resposta fora do JSON esperado")
        return dados

    def _registrar(self, resposta: Any, modelo: str, contexto: ContextoDaChamada, versao_prompt: str,
                   duracao_ms: int) -> None:
        meta = getattr(resposta, "usage_metadata", None)
        entrada = int(getattr(meta, "prompt_token_count", 0) or 0)
        saida = int(getattr(meta, "candidates_token_count", 0) or 0) + int(getattr(meta, "thoughts_token_count", 0) or 0)
        lido = int(getattr(meta, "cached_content_token_count", 0) or 0)
        registro = UsoDeIA(
            vendedor_id=contexto.vendedor_id, analise_id=contexto.analise_id, etapa=contexto.etapa,
            provedor="gemini", modelo=modelo, versao_prompt=versao_prompt, tokens_entrada=entrada,
            tokens_saida=saida, cache_lido=lido, cache_gravado=0, buscas_web=0, custo_estimado_usd=Decimal("0"),
            duracao_ms=duracao_ms, criado_em=self._relogio(),
        )
        log.info("IA uso: etapa=%s modelo=%s entrada=%d saida=%d cache_lido=%d custo_usd=0 tempo_ms=%d",
                 registro.etapa, modelo, entrada, saida, lido, duracao_ms)
        try:
            self._registro.registrar(registro)
        except Exception as erro:
            log.warning("Não deu para gravar o uso da IA (%s).", type(erro).__name__)


def parte_de_imagem(jpeg: bytes) -> Any:
    from google.genai import types

    return types.Part.from_bytes(data=jpeg, mime_type="image/jpeg")
