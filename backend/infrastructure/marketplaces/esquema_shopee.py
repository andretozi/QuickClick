"""
Infraestrutura · Shopee · Fonte de esquema: os campos que a Shopee pede para uma categoria, no modelo genérico.

Endpoints e nomes de campo vindos da memória do plano multimarketplace: conferir na doc oficial da Shopee.
"""

import logging
from typing import Any

from backend.application.ia.modelos import CategoriaSugerida
from backend.application.portas import FalhaNoMarketplace
from backend.domain.canais.esquema import CampoDoCanal, EsquemaDoCanal, TipoDeCampo
from backend.domain.canais.exigencias import comparavel
from backend.domain.erros import ServicoIndisponivel
from backend.domain.ia.leitura import CHAVES_DA_EMBALAGEM
from backend.infrastructure.marketplaces.shopee import ClienteShopee

log = logging.getLogger(__name__)

CANAL_SHOPEE = "shopee"  # id do catálogo (backend/domain/marketplace.py)
CAMINHO_CATEGORIA = "/api/v2/product/category_recommend"  # conferir na doc oficial da Shopee
CAMINHO_ATRIBUTOS = "/api/v2/product/get_attribute_tree"  # conferir na doc oficial da Shopee
IDIOMA = "pt-BR"
VALIDACOES_NUMERICAS = frozenset({"INT_TYPE", "FLOAT_TYPE"})  # input_validation_type; conferir na doc oficial da Shopee

# chave nossa → nomes de atributo da Shopee (comparáveis: sem acento nem caixa) que significam a mesma coisa
SINONIMOS_SHOPEE: dict[str, tuple[str, ...]] = {
    "marca": ("marca", "brand"),
    "modelo": ("modelo", "model"),
    "cor": ("cor", "color", "colour"),
    "material": ("material",),
    "tamanho": ("tamanho", "size"),
    "voltagem": ("voltagem", "voltage"),
    "genero": ("genero", "gender"),
    "capacidade": ("capacidade", "capacity"),
    "potencia": ("potencia", "power"),
    "estampa": ("estampa", "pattern"),
}
_CHAVE_POR_NOME = {nome: chave for chave, nomes in SINONIMOS_SHOPEE.items() for nome in nomes}

# Campos do add_item que não vêm da árvore de atributos (id = nome do campo no add_item). A unidade é a
# nossa (CHAVES_DA_EMBALAGEM): o publicador converte o peso para kg. Nomes e obrigatórios: conferir na doc oficial da Shopee.
CAMPOS_FIXOS: tuple[CampoDoCanal, ...] = (
    CampoDoCanal(CANAL_SHOPEE, "brand", "Marca", True, TipoDeCampo.TEXTO, chave="marca"),
    CampoDoCanal(CANAL_SHOPEE, "weight", "Peso", True, TipoDeCampo.NUMERO,
                 unidade=CHAVES_DA_EMBALAGEM["peso_g"], chave="peso_g"),
    CampoDoCanal(CANAL_SHOPEE, "package_length", "Comprimento da embalagem", False, TipoDeCampo.NUMERO,
                 unidade=CHAVES_DA_EMBALAGEM["comprimento_cm"], chave="comprimento_cm"),
    CampoDoCanal(CANAL_SHOPEE, "package_width", "Largura da embalagem", False, TipoDeCampo.NUMERO,
                 unidade=CHAVES_DA_EMBALAGEM["largura_cm"], chave="largura_cm"),
    CampoDoCanal(CANAL_SHOPEE, "package_height", "Altura da embalagem", False, TipoDeCampo.NUMERO,
                 unidade=CHAVES_DA_EMBALAGEM["altura_cm"], chave="altura_cm"),
)
IDS_FIXOS = frozenset(c.id for c in CAMPOS_FIXOS)


def _campo(atributo: dict[str, Any]) -> CampoDoCanal | None:
    # get_attribute_tree aninha em attribute_info o que get_attributes trazia solto: conferir na doc oficial da Shopee
    info = atributo.get("attribute_info") or atributo
    nome = str(atributo.get("display_attribute_name") or atributo.get("name") or "").strip()
    if atributo.get("attribute_id") is None or not nome:
        return None
    valores = tuple(
        (str(v["value_id"]), str(v.get("display_value_name") or v.get("name") or "").strip())
        for v in atributo.get("attribute_value_list") or [] if isinstance(v, dict) and v.get("value_id") is not None
    )
    unidades = info.get("attribute_unit_list") or info.get("attribute_unit") or []
    if valores:
        tipo = TipoDeCampo.LISTA
    elif info.get("input_validation_type") in VALIDACOES_NUMERICAS:
        tipo = TipoDeCampo.NUMERO
    else:
        tipo = TipoDeCampo.TEXTO
    return CampoDoCanal(
        canal=CANAL_SHOPEE, id=str(atributo["attribute_id"]), nome=nome,
        obrigatorio=bool(atributo.get("is_mandatory", atributo.get("mandatory", False))), tipo=tipo,
        valores=valores, unidade=str(unidades[0]) if tipo is TipoDeCampo.NUMERO and unidades else "",
        chave=_CHAVE_POR_NOME.get(comparavel(nome), ""),
    )


def esquema_da_shopee(categoria_id: str, categoria_nome: str, atributos: list[Any]) -> EsquemaDoCanal:
    """Os atributos da categoria, na ordem da Shopee, seguidos dos campos fixos do add_item."""
    campos = tuple(c for a in atributos if isinstance(a, dict) and (c := _campo(a)) is not None)
    return EsquemaDoCanal(CANAL_SHOPEE, categoria_id, categoria_nome, campos + CAMPOS_FIXOS)


class FonteDeEsquemaShopee:
    """Implementa a porta FonteDeEsquema; o shop_id vem no construtor porque a porta não o tem."""

    def __init__(self, cliente: ClienteShopee, shop_id: str):
        self._cliente = cliente
        self._shop_id = shop_id

    def _ler(self, caminho: str, params: dict[str, Any], access_token: str) -> Any:
        try:
            return self._cliente.get(caminho, params, access_token=access_token, shop_id=self._shop_id).get("response")
        except (FalhaNoMarketplace, ServicoIndisponivel) as erro:
            log.warning("Shopee: %s não lido (%s).", caminho, getattr(erro, "status", 0) or "sem resposta")
            return None

    def descobrir_categoria(self, termos: list[str], access_token: str) -> CategoriaSugerida | None:
        nome = " ".join(t.strip() for t in termos if t.strip())
        if not nome:
            return None
        resposta = self._ler(CAMINHO_CATEGORIA, {"item_name": nome}, access_token)
        ids = resposta.get("category_id") if isinstance(resposta, dict) else None
        return CategoriaSugerida(str(ids[0]), "") if isinstance(ids, list) and ids else None

    def esquema(self, categoria_id: str, access_token: str, categoria_nome: str = "") -> EsquemaDoCanal | None:
        resposta = self._ler(CAMINHO_ATRIBUTOS, {"category_id_list": categoria_id, "language": IDIOMA}, access_token)
        lista = resposta.get("list") if isinstance(resposta, dict) else None
        da_categoria = next((c for c in lista or [] if isinstance(c, dict)
                             and str(c.get("category_id")) == str(categoria_id)), None)
        if da_categoria is None:
            return None
        return esquema_da_shopee(categoria_id, categoria_nome, da_categoria.get("attribute_tree") or [])
