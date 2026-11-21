"""
Infraestrutura · Dados reais da QuickStore para a IA e publicação (com o token do vendedor)
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.application.ia.modelos import CategoriaSugerida, PrecoObservado
from backend.application.ia.portas import CacheDeCategoriasML
from backend.application.portas import FalhaNoMarketplace
from backend.domain.canais.esquema import EsquemaDoCanal
from backend.domain.ia.atributos_ml import AtributoML, esquema_do_ml
from backend.infrastructure.marketplaces.quickstore import GatewayQuickStore

log = logging.getLogger("quickclick.marketplaces")

VALIDADE_DOS_ATRIBUTOS = timedelta(hours=24)
PAUSA_DEPOIS_DE_403 = timedelta(hours=1)
CONDICAO_NA_QUICKSTORE = {"novo": "new", "usado": "used", "recondicionado": "used"}


def _agora() -> datetime:
    return datetime.now(UTC)


_TAGS_ATRIBUTO_RELEVANTES = (
    "required",
    "catalog_required",
    "read_only",
    "non_modifiable",
    "hidden",
    "allow_variations",
    "variation_attribute",
    "grid_template_required",
)


def _resumo_do_atributo(bruto: dict[str, Any]) -> dict[str, Any]:
    resumo: dict[str, Any] = {
        "id": bruto.get("id"),
        "name": bruto.get("name"),
        "tags": {k: v for k, v in (bruto.get("tags") or {}).items() if k in _TAGS_ATRIBUTO_RELEVANTES and v},
        "values": [
            {"id": v.get("id"), "name": v.get("name")}
            for v in (bruto.get("values") or [])[:200]
            if isinstance(v, dict)
        ],
    }
    if bruto.get("default_unit"):
        resumo["default_unit"] = bruto.get("default_unit")
    if bruto.get("value_type"):
        resumo["value_type"] = bruto.get("value_type")
    return resumo


class FonteQuickStore:
    def __init__(
        self,
        gateway: GatewayQuickStore,
        cache: CacheDeCategoriasML,
        relogio: Callable[[], datetime] = _agora,
    ):
        self._gateway = gateway
        self._cache = cache
        self._relogio = relogio
        self._busca_pausada_ate: datetime | None = None

    def descobrir_categoria(self, termos: list[str], access_token: str) -> CategoriaSugerida | None:
        candidatos = list(dict.fromkeys(t.strip() for t in (termos or []) if t and t.strip()))
        for termo in candidatos:
            try:
                achados = self._gateway.descobrir_dominio(termo, access_token)
            except FalhaNoMarketplace as erro:
                log.warning("QuickStore: categoria não descoberta (%s).", erro.status or "sem resposta")
                return None
            primeiro = next((a for a in achados if isinstance(a, dict) and a.get("category_id")), None)
            if primeiro is not None:
                return CategoriaSugerida(
                    str(primeiro["category_id"]),
                    str(primeiro.get("category_name") or ""),
                    str(primeiro.get("domain_name") or ""),
                )
        return None

    def _atributos(self, categoria_id: str, access_token: str) -> list[AtributoML] | None:
        agora = self._relogio()
        chave_cache = f"qs:{categoria_id}"
        guardados = self._cache.obter(chave_cache, agora)
        if guardados is None:
            try:
                brutos = self._gateway.atributos_da_categoria(categoria_id, access_token)
            except FalhaNoMarketplace as erro:
                log.warning("QuickStore: atributos da categoria não lidos (%s).", erro.status or "sem resposta")
                return None
            guardados = [_resumo_do_atributo(b) for b in brutos if isinstance(b, dict) and b.get("id")]
            self._cache.salvar(chave_cache, guardados, agora + VALIDADE_DOS_ATRIBUTOS)
        return [AtributoML.de_api(a) for a in guardados]

    def atributos_da_categoria(self, categoria_id: str, access_token: str) -> list[AtributoML]:
        return self._atributos(categoria_id, access_token) or []

    def esquema(self, categoria_id: str, access_token: str, categoria_nome: str = "") -> EsquemaDoCanal | None:
        atributos = self._atributos(categoria_id, access_token)
        return None if atributos is None else esquema_do_ml(categoria_id, categoria_nome, atributos)

    def buscar_parecidos(
        self,
        termos: list[str],
        categoria_id: str | None,
        condicao: str,
        access_token: str,
    ) -> list[PrecoObservado] | None:
        agora = self._relogio()
        if not termos or (self._busca_pausada_ate and agora < self._busca_pausada_ate):
            return None
        try:
            dados = self._gateway.buscar_itens(termos[0], categoria_id, CONDICAO_NA_QUICKSTORE.get(condicao), access_token)
        except FalhaNoMarketplace as erro:
            if erro.status in (401, 403):
                self._busca_pausada_ate = agora + PAUSA_DEPOIS_DE_403
                log.warning(
                    "QuickStore: a busca de itens está restrita para este app (%s). "
                    "Usando a reserva do preço por uma hora.",
                    erro.status,
                )
            else:
                log.warning("QuickStore: busca de itens falhou (%s).", erro.status or "sem resposta")
            return None
        observados = []
        for item in (dados or {}).get("results") or []:
            if not isinstance(item, dict) or item.get("currency_id", "BRL") != "BRL":
                continue
            try:
                preco = round(float(item.get("price") or 0) * 100)
            except (TypeError, ValueError):
                continue
            if preco > 0:
                frete = bool((item.get("shipping") or {}).get("free_shipping"))
                observados.append(PrecoObservado(preco, frete))
        return observados

    def tarifa(self, preco_centavos: int, categoria_id: str, access_token: str) -> int | None:
        try:
            dados = self._gateway.custo_de_venda(preco_centavos / 100, categoria_id, access_token)
        except FalhaNoMarketplace as erro:
            log.warning("QuickStore: tarifa não consultada (%s).", erro.status or "sem resposta")
            return None
        if isinstance(dados, list):
            dados = next(
                (d for d in dados if isinstance(d, dict) and d.get("listing_type_id") == "gold_special"),
                dados[0] if dados else None,
            )
        try:
            return round(float((dados or {}).get("sale_fee_amount")) * 100)
        except (TypeError, ValueError):
            return None
