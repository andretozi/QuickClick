"""
Infraestrutura · Shopee · Publicador: corpo do upload_image e do add_item a partir do Produto, sem rota ligada.

Nomes de endpoint e de campo vindos do plano multimarketplace: conferir na doc oficial da Shopee.
"""

import math
from typing import Any

from backend.application.portas import FalhaNoMarketplace
from backend.domain.canais.esquema import CampoDoCanal, EsquemaDoCanal, TipoDeCampo
from backend.domain.canais.exigencias import comparavel
from backend.domain.erros import CamposObrigatoriosFaltando
from backend.domain.ia.leitura import numero_positivo
from backend.domain.produto import Produto
from backend.infrastructure.marketplaces.esquema_shopee import IDS_FIXOS
from backend.infrastructure.marketplaces.shopee import ClienteShopee

CAMINHO_FOTO = "/api/v2/media_space/upload_image"  # chamada sem loja; conferir na doc oficial da Shopee
CAMINHO_ITEM = "/api/v2/product/add_item"  # conferir na doc oficial da Shopee
CONDICAO_NA_SHOPEE = {"novo": "NEW", "usado": "USED"}  # conferir na doc oficial da Shopee
MAIOR_NUMERO = 1_000_000_000  # acima disso (ou infinito) é erro de digitação, não medida


def _texto_do_numero(numero: float) -> str:
    """1500000 → "1500000" e 12.5 → "12.5" (o formato :g cortava em 6 algarismos)."""
    return str(int(numero)) if numero.is_integer() else str(numero)


def _valor(campo: CampoDoCanal, texto: str) -> Any:
    """O valor no formato da Shopee, ou None quando a resposta não serve ao campo."""
    if campo.tipo is TipoDeCampo.LISTA:
        alvo = comparavel(texto)
        return next(({"value_id": int(i), "original_value_name": n} for i, n in campo.valores
                     if comparavel(n) == alvo), None)
    if campo.tipo is TipoDeCampo.NUMERO:
        numero = numero_positivo(texto, campo.unidade)
        if numero is None or not math.isfinite(numero) or numero > MAIOR_NUMERO:
            return None
        if campo.id == "weight":
            # o nosso peso é em g; a Shopee pede kg (menos de 0,5 g vira 0 e conta como sem peso, como na ficha)
            return round(numero / 1000, 3) or None
        if campo.id in IDS_FIXOS:
            return math.ceil(numero)  # cm inteiros, para cima: embalagem menor que a real erra o frete
        return {"value_id": 0, "original_value_name": _texto_do_numero(numero), "value_unit": campo.unidade}
    return texto if campo.id in IDS_FIXOS else {"value_id": 0, "original_value_name": texto}


class PublicadorShopee:
    def __init__(self, cliente: ClienteShopee, shop_id: str):
        self._cliente = cliente
        self._shop_id = shop_id

    @staticmethod
    def corpo_upload_image(jpeg: bytes, nome: str = "foto.jpg") -> dict[str, Any]:
        """Os arquivos do multipart (campo "image"; conferir na doc oficial da Shopee)."""
        return {"image": (nome, jpeg, "image/jpeg")}

    @staticmethod
    def corpo_add_item(produto: Produto, respostas: dict[str, str], esquema: EsquemaDoCanal,
                       image_ids: list[str], logisticas: list[int]) -> dict[str, Any]:
        """respostas: valores confirmados por chave nossa; campo próprio do canal pelo id dele.
        Recusa com CamposObrigatoriosFaltando, listando tudo o que falta, antes de montar o corpo."""
        faltando = [nome for nome, falta in (
            ("Título", not produto.titulo.strip()), ("Preço", produto.preco_centavos <= 0),
            ("Condição", produto.condicao not in CONDICAO_NA_SHOPEE), ("Fotos", not image_ids),
            ("Forma de envio", not logisticas)) if falta]
        fixos: dict[str, Any] = {}
        atributos: list[dict[str, Any]] = []
        for campo in esquema.campos:
            texto = str(respostas.get(campo.chave or campo.id) or "").strip()
            valor = _valor(campo, texto) if texto else None
            if valor is None:
                if campo.obrigatorio:
                    faltando.append(campo.nome)
            elif campo.id in IDS_FIXOS:
                fixos[campo.id] = valor
            else:
                atributos.append({"attribute_id": int(campo.id), "attribute_value_list": [valor]})
        if faltando:
            raise CamposObrigatoriosFaltando("Shopee", faltando)

        # Nomes do add_item: conferir na doc oficial da Shopee (brand_id 0 = marca fora da lista da Shopee)
        corpo: dict[str, Any] = {
            "item_name": produto.titulo.strip(),
            "description": produto.descricao,
            "category_id": int(esquema.categoria_id),
            "original_price": produto.preco_centavos / 100,
            "seller_stock": [{"stock": produto.estoque}],
            "condition": CONDICAO_NA_SHOPEE[produto.condicao],
            "image": {"image_id_list": list(image_ids)},
            "logistic_info": [{"logistic_id": i, "enabled": True} for i in logisticas],
            "attribute_list": atributos,
        }
        if "brand" in fixos:
            corpo["brand"] = {"brand_id": 0, "original_brand_name": fixos["brand"]}
        if "weight" in fixos:
            corpo["weight"] = fixos["weight"]
        medidas = {i: fixos[i] for i in ("package_length", "package_width", "package_height") if i in fixos}
        if len(medidas) == 3:  # a Shopee pede as três juntas ou nenhuma (conferir na doc oficial da Shopee)
            corpo["dimension"] = medidas
        return corpo

    def subir_foto(self, jpeg: bytes, nome: str = "foto.jpg") -> str:
        resposta = self._cliente.post(CAMINHO_FOTO, files=self.corpo_upload_image(jpeg, nome))
        image_id = str(((resposta.get("response") or {}).get("image_info") or {}).get("image_id") or "")
        if not image_id:
            raise FalhaNoMarketplace("A Shopee não devolveu a foto enviada.")
        return image_id

    def publicar(self, access_token: str, produto: Produto, respostas: dict[str, str], esquema: EsquemaDoCanal,
                 fotos: list[bytes], logisticas: list[int]) -> dict[str, Any]:
        """Sobe as fotos e cria o item. Confere os obrigatórios antes da primeira chamada."""
        self.corpo_add_item(produto, respostas, esquema, ["conferencia"] * len(fotos), logisticas)
        image_ids = [self.subir_foto(foto) for foto in fotos]
        corpo = self.corpo_add_item(produto, respostas, esquema, image_ids, logisticas)
        return self._cliente.post(CAMINHO_ITEM, json=corpo, access_token=access_token, shop_id=self._shop_id)
