"""
Aplicação · Publicar no Mercado Livre, com o anúncio montado no back

O front manda o anúncio revisado (JSON) e as fotos escolhidas. O back monta o item do Mercado Livre:
categoria (a da análise, ou a descoberta pelo título), título, preço, moeda BRL, estoque, condição,
anúncio Clássico (gold_special) e atributos com os IDs da categoria; sobe as fotos pela API de
imagens, cria o item e grava a descrição em texto simples. Nada é publicado sem o clique do vendedor.
"""

import logging
from dataclasses import dataclass
from typing import Any

from backend.application.casos_de_uso.conectar_marketplace import ConectarMarketplace
from backend.application.ia.modelos import ArquivoDeFoto
from backend.application.ia.portas import FontePrecosMarketplace, PreparadorDeFotos, RepositorioDeAnalises
from backend.application.portas import FalhaNoMarketplace, PublicadorMercadoLivre
from backend.domain.erros import FotoInvalida, MercadoLivreDesconectado, PublicacaoRecusada
from backend.domain.ia.atributos_ml import ligar_confirmados
from backend.domain.ia.escrita import cortar_titulo
from backend.domain.ia.leitura import normalizar_chave

log = logging.getLogger("quickclick.marketplaces")

MERCADO_LIVRE = "mercado-livre"
ANUNCIO_CLASSICO = "gold_special"
CONDICAO_NO_ML = {"novo": "new", "new": "new", "usado": "used", "used": "used", "recondicionado": "used"}
PRECO_MINIMO_CENTAVOS = 100
ESTOQUE_MAXIMO = 99_999
DESCRICAO_MAX_ML = 50_000


@dataclass(frozen=True)
class AnuncioParaPublicar:
    titulo: str
    descricao: str
    preco_centavos: int
    estoque: int
    condicao: str  # new | used
    atributos: tuple[tuple[str, str], ...]
    analise_id: str | None = None
    ml_categoria_id: str | None = None


def anuncio_de_dict(dados: dict[str, Any]) -> AnuncioParaPublicar:
    if not isinstance(dados, dict):
        raise ValueError("Anúncio inválido.")
    titulo = cortar_titulo(str(dados.get("titulo") or ""))
    if not titulo:
        raise ValueError("O anúncio precisa de um título.")
    try:
        preco = int(dados.get("preco_centavos"))
        estoque = int(dados.get("estoque") or 1)
    except (TypeError, ValueError) as erro:
        raise ValueError("Preço ou estoque inválido.") from erro
    if preco < PRECO_MINIMO_CENTAVOS:
        raise ValueError("O preço precisa ser de pelo menos R$ 1,00.")
    if not 1 <= estoque <= ESTOQUE_MAXIMO:
        raise ValueError("O estoque precisa ser de pelo menos 1 unidade.")
    atributos = []
    for item in dados.get("atributos") or []:
        if isinstance(item, dict):
            chave, valor = normalizar_chave(item.get("chave")), str(item.get("valor") or "").strip()[:120]
            if chave and valor:
                atributos.append((chave, valor))
    return AnuncioParaPublicar(
        titulo=titulo,
        descricao=str(dados.get("descricao") or "").strip()[:DESCRICAO_MAX_ML],
        preco_centavos=preco,
        estoque=estoque,
        condicao=CONDICAO_NO_ML.get(str(dados.get("condicao") or "").lower(), "new"),
        atributos=tuple(atributos),
        analise_id=str(dados["analise_id"]) if dados.get("analise_id") else None,
        ml_categoria_id=str(dados["ml_categoria_id"]) if dados.get("ml_categoria_id") else None,
    )


def _causas(corpo: Any) -> list[str]:
    if not isinstance(corpo, dict):
        return []
    causas = [str(c.get("message") or c.get("code") or "") for c in corpo.get("cause") or [] if isinstance(c, dict)]
    causas = [c for c in causas if c]
    return causas or ([str(corpo.get("message"))] if corpo.get("message") else [])


def _pede_family_name(corpo: Any) -> bool:
    """Categorias no modelo novo do Mercado Livre (User Products) pedem family_name em vez de title."""
    return "family_name" in str(corpo or "")


class PublicarNoMercadoLivre:
    def __init__(self, conectar: ConectarMarketplace, publicador: PublicadorMercadoLivre,
                 fonte: FontePrecosMarketplace, analises: RepositorioDeAnalises, preparador: PreparadorDeFotos):
        self._conectar = conectar
        self._publicador = publicador
        self._fonte = fonte
        self._analises = analises
        self._preparador = preparador

    def _ml_da_analise(self, vendedor_id: int, analise_id: str | None) -> dict[str, Any]:
        if not analise_id:
            return {}
        analise = self._analises.obter(analise_id)
        if analise is None or analise["vendedor_id"] != vendedor_id:
            return {}
        return (analise.get("leitura") or {}).get("ml") or {}

    def executar(self, vendedor_id: int, anuncio: dict[str, Any], fotos: list[ArquivoDeFoto]) -> dict[str, Any]:
        dados = anuncio_de_dict(anuncio)
        if not fotos:
            raise FotoInvalida("Escolha pelo menos uma foto para o anúncio.")
        token = self._conectar.token_ativo(vendedor_id, MERCADO_LIVRE)
        if not token:
            raise MercadoLivreDesconectado()
        preparadas = self._preparador.preparar(fotos)  # confere o conteúdo e tira os metadados

        ml = self._ml_da_analise(vendedor_id, dados.analise_id)
        categoria_id = dados.ml_categoria_id or ml.get("categoria_id")
        if not categoria_id:
            sugerida = self._fonte.descobrir_categoria([dados.titulo], token)
            if sugerida is None:
                raise PublicacaoRecusada(["Não consegui descobrir a categoria do Mercado Livre para esse título."])
            categoria_id = sugerida.categoria_id
        da_categoria = self._fonte.atributos_da_categoria(categoria_id, token)
        ligados = ligar_confirmados(list(dados.atributos), da_categoria, ml.get("mapa") or {})

        try:
            imagens = [self._publicador.subir_imagem(token, f.leitura_jpeg, f"foto{f.indice + 1}.jpg") for f in preparadas]
            item = {
                "title": dados.titulo, "category_id": categoria_id, "price": dados.preco_centavos / 100,
                "currency_id": "BRL", "available_quantity": dados.estoque, "buying_mode": "buy_it_now",
                "condition": dados.condicao, "listing_type_id": ANUNCIO_CLASSICO,
                "pictures": [{"id": imagem} for imagem in imagens],
                "attributes": [ligado.para_api() for ligado in ligados],
            }
            try:
                criado = self._publicador.publicar_anuncio(token, item)
            except FalhaNoMarketplace as erro:
                if not _pede_family_name(erro.corpo):
                    raise
                log.info("Mercado Livre pediu family_name (User Products): publicando de novo com ele.")
                criado = self._publicador.publicar_anuncio(token, {**item, "family_name": dados.titulo})
        except FalhaNoMarketplace as erro:
            log.warning("Mercado Livre recusou a publicação (%s).", erro.status or "sem resposta")
            raise PublicacaoRecusada(_causas(erro.corpo)) from erro

        avisos = []
        item_id = str(criado.get("id") or "")
        if dados.descricao and item_id:
            try:
                self._publicador.gravar_descricao(token, item_id, dados.descricao)
            except FalhaNoMarketplace as erro:
                log.warning("Descrição não gravada no Mercado Livre (%s).", erro.status or "sem resposta")
                avisos.append({"codigo": "descricao_nao_gravada",
                               "mensagem": "O anúncio foi criado, mas a descrição não entrou. Confira no Mercado Livre."})
        return {"id": item_id, "permalink": criado.get("permalink"), "status": criado.get("status"),
                "categoria_id": categoria_id, "avisos": avisos}
