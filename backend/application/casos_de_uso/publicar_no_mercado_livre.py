"""
Aplicação · Publicar e gerir anúncios no Mercado Livre, com o anúncio montado no back

O front manda o anúncio revisado (JSON) e as fotos escolhidas. O back monta o item do Mercado Livre:
categoria (a da análise, ou a descoberta pelo título), título, preço, moeda BRL, estoque, condição,
anúncio Clássico (gold_special) e atributos com os IDs da categoria; sobe as fotos pela API de
imagens, cria o item e grava a descrição em texto simples. Nada é publicado sem o clique do vendedor.
Também sincroniza, pausa, reativa, edita e exclui anúncios direto na conta do vendedor no Mercado Livre.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from backend.application.casos_de_uso.conectar_marketplace import ConectarMarketplace
from backend.application.ia.modelos import ArquivoDeFoto
from backend.application.ia.portas import FontePrecosMarketplace, PreparadorDeFotos, RepositorioDeAnalises
from backend.application.portas import FalhaNoMarketplace, PublicadorMercadoLivre
from backend.domain.erros import (
    AnuncioNaoEncontrado,
    FotoInvalida,
    MercadoLivreDesconectado,
    PublicacaoRecusada,
)
from backend.domain.ia.atributos_ml import completar_para_publicacao, ligar_confirmados
from backend.domain.ia.escrita import cortar_titulo
from backend.domain.ia.leitura import normalizar_chave

log = logging.getLogger("quickclick.marketplaces")

MERCADO_LIVRE = "mercado-livre"
ANUNCIO_CLASSICO = "gold_special"
CONDICAO_NO_ML = {"novo": "new", "new": "new", "usado": "used", "used": "used", "recondicionado": "used"}
STATUS_PARA_ML = {
    "pausado": "paused",
    "paused": "paused",
    "publicado": "active",
    "ativo": "active",
    "active": "active",
}
PRECO_MINIMO_CENTAVOS = 100
ESTOQUE_MAXIMO = 99_999
DESCRICAO_MAX_ML = 50_000
_FORMATO_ITEM_ID = re.compile(r"^MLB\d{5,20}$")


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
    fotos_mantidas: tuple[str, ...] = ()


def _validar_item_id(item_id: str) -> str:
    codigo = str(item_id or "").strip().upper().replace("-", "")
    if not _FORMATO_ITEM_ID.match(codigo):
        raise ValueError("Identificador do anúncio inválido.")
    return codigo


def _validar_url_foto_ml(url: Any) -> str | None:
    texto = str(url or "").strip()
    if not texto or len(texto) > 500:
        return None
    partes = urlparse(texto)
    host = (partes.hostname or "").lower()
    if partes.scheme != "https" or not (host == "mlstatic.com" or host.endswith(".mlstatic.com")):
        return None
    return texto


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
    if not 0 <= estoque <= ESTOQUE_MAXIMO:
        raise ValueError("O estoque informado é inválido.")
    atributos = []
    for item in dados.get("atributos") or []:
        if isinstance(item, dict):
            chave, valor = normalizar_chave(item.get("chave")), str(item.get("valor") or "").strip()[:120]
            if chave and valor:
                atributos.append((chave, valor))
    mantidas = tuple(
        url for url in (_validar_url_foto_ml(u) for u in (dados.get("fotos_mantidas") or [])[:6]) if url
    )
    return AnuncioParaPublicar(
        titulo=titulo,
        descricao=str(dados.get("descricao") or "").strip()[:DESCRICAO_MAX_ML],
        preco_centavos=preco,
        estoque=estoque,
        condicao=CONDICAO_NO_ML.get(str(dados.get("condicao") or "").lower(), "new"),
        atributos=tuple(atributos),
        analise_id=str(dados["analise_id"]) if dados.get("analise_id") else None,
        ml_categoria_id=str(dados["ml_categoria_id"]) if dados.get("ml_categoria_id") else None,
        fotos_mantidas=mantidas,
    )


def _causas(corpo: Any) -> list[str]:
    if not isinstance(corpo, dict):
        return []
    causas = [str(c.get("message") or c.get("code") or "") for c in (corpo.get("cause") or []) if isinstance(c, dict)]
    causas = [c for c in causas if c]
    return causas or ([str(corpo.get("message"))] if corpo.get("message") else [])


def _pede_family_name(corpo: Any) -> bool:
    """Categorias no modelo novo do Mercado Livre (User Products) pedem family_name em vez de title."""
    texto = str(corpo or "").lower()
    return "family_name" in texto or ("title" in texto and "invalid" in texto)


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

    def _conferir_dono(self, vendedor_id: int, item_id: str) -> tuple[str, dict[str, Any]]:
        codigo = _validar_item_id(item_id)
        credenciais = self._conectar.credenciais_ativas(vendedor_id, MERCADO_LIVRE)
        if credenciais is None or not credenciais.access_token:
            raise MercadoLivreDesconectado()
        try:
            atual = self._publicador.obter_anuncio(credenciais.access_token, codigo)
        except FalhaNoMarketplace as erro:
            if erro.status == 404:
                raise AnuncioNaoEncontrado() from erro
            raise PublicacaoRecusada(_causas(erro.corpo)) from erro
        dono_item = str(atual.get("seller_id") or "").strip()
        dono_conta = str(credenciais.conta_externa_id or "").strip()
        if dono_conta and dono_item and dono_item != dono_conta:
            raise AnuncioNaoEncontrado()
        return credenciais.access_token, atual

    def executar(self, vendedor_id: int, anuncio: dict[str, Any], fotos: list[ArquivoDeFoto]) -> dict[str, Any]:
        dados = anuncio_de_dict(anuncio)
        if dados.estoque < 1:
            raise ValueError("O estoque precisa ser de pelo menos 1 unidade.")
        if not fotos and not dados.fotos_mantidas:
            raise FotoInvalida("Escolha pelo menos uma foto para o anúncio.")
        token = self._conectar.token_ativo(vendedor_id, MERCADO_LIVRE)
        if not token:
            raise MercadoLivreDesconectado()
        preparadas = self._preparador.preparar(fotos) if fotos else []  # confere o conteúdo e tira os metadados

        ml = self._ml_da_analise(vendedor_id, dados.analise_id)
        categoria_id = dados.ml_categoria_id or ml.get("categoria_id")
        if not categoria_id:
            sugerida = self._fonte.descobrir_categoria([dados.titulo], token)
            if sugerida is None:
                raise PublicacaoRecusada(["Não consegui descobrir a categoria do Mercado Livre para esse título."])
            categoria_id = sugerida.categoria_id
        da_categoria = self._fonte.atributos_da_categoria(categoria_id, token)
        ligados = completar_para_publicacao(
            ligar_confirmados(list(dados.atributos), da_categoria, ml.get("mapa") or {}),
            da_categoria,
            dados.titulo,
        )

        try:
            imagens_novas = [
                {"id": self._publicador.subir_imagem(token, f.leitura_jpeg, f"foto{f.indice + 1}.jpg")}
                for f in preparadas
            ]
            imagens = ([{"source": url} for url in dados.fotos_mantidas] + imagens_novas)[:6]
            item = {
                "title": dados.titulo, "category_id": categoria_id, "price": dados.preco_centavos / 100,
                "currency_id": "BRL", "available_quantity": dados.estoque, "buying_mode": "buy_it_now",
                "condition": dados.condicao, "listing_type_id": ANUNCIO_CLASSICO,
                "pictures": imagens,
                "attributes": [ligado.para_api() for ligado in ligados],
            }
            try:
                criado = self._publicador.publicar_anuncio(token, item)
            except FalhaNoMarketplace as erro:
                if not _pede_family_name(erro.corpo):
                    raise
                log.info("Mercado Livre pediu family_name (User Products): publicando de novo com ele.")
                sem_titulo = {k: v for k, v in item.items() if k != "title"}
                criado = self._publicador.publicar_anuncio(token, {**sem_titulo, "family_name": dados.titulo})
        except FalhaNoMarketplace as erro:
            causas = _causas(erro.corpo)
            log.warning("Mercado Livre recusou a publicação (%s): %s", erro.status or "sem resposta",
                        "; ".join(causas) or "sem detalhes")
            raise PublicacaoRecusada(causas) from erro

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

    def obter(self, vendedor_id: int, item_id: str) -> dict[str, Any]:
        _, atual = self._conferir_dono(vendedor_id, item_id)
        return atual

    def alterar_status(self, vendedor_id: int, item_id: str, status: str) -> dict[str, Any]:
        destino = STATUS_PARA_ML.get(str(status or "").strip().lower())
        if not destino:
            raise ValueError("Status inválido para o anúncio.")
        token, atual = self._conferir_dono(vendedor_id, item_id)
        codigo = str(atual["id"])
        try:
            self._publicador.atualizar_anuncio(token, codigo, {"status": destino})
            return self._publicador.obter_anuncio(token, codigo)
        except FalhaNoMarketplace as erro:
            raise PublicacaoRecusada(_causas(erro.corpo)) from erro

    def atualizar(self, vendedor_id: int, item_id: str, anuncio: dict[str, Any],
                  fotos: list[ArquivoDeFoto] | None = None) -> dict[str, Any]:
        dados = anuncio_de_dict(anuncio)
        token, atual = self._conferir_dono(vendedor_id, item_id)
        codigo = str(atual["id"])
        preparadas = self._preparador.preparar(fotos) if fotos else []

        try:
            novas = [
                {"id": self._publicador.subir_imagem(token, f.leitura_jpeg, f"foto{f.indice + 1}.jpg")}
                for f in preparadas
            ]
        except FalhaNoMarketplace as erro:
            raise PublicacaoRecusada(_causas(erro.corpo)) from erro

        mantidas = [{"source": url} for url in dados.fotos_mantidas]
        imagens = (mantidas + novas)[:6]

        ml = self._ml_da_analise(vendedor_id, dados.analise_id)
        categoria_id = dados.ml_categoria_id or str(atual.get("category_id") or "") or ml.get("categoria_id")
        ligados = []
        if categoria_id and dados.atributos:
            da_categoria = self._fonte.atributos_da_categoria(categoria_id, token)
            ligados = completar_para_publicacao(
                ligar_confirmados(list(dados.atributos), da_categoria, ml.get("mapa") or {}),
                da_categoria,
                dados.titulo,
            )

        mudancas: dict[str, Any] = {
            "price": dados.preco_centavos / 100,
            "available_quantity": max(1, dados.estoque) if atual.get("status") == "active" else dados.estoque,
        }
        if imagens:
            mudancas["pictures"] = imagens
        if ligados:
            mudancas["attributes"] = [ligado.para_api() for ligado in ligados]
        if int(atual.get("sold_quantity") or 0) == 0:
            tags = [str(t) for t in (atual.get("tags") or [])]
            if "user_product_listing" in tags or atual.get("family_name"):
                mudancas["family_name"] = dados.titulo
            else:
                mudancas["title"] = dados.titulo

        try:
            try:
                self._publicador.atualizar_anuncio(token, codigo, mudancas)
            except FalhaNoMarketplace as erro:
                if _pede_family_name(erro.corpo) and "title" in mudancas:
                    sem_titulo = {k: v for k, v in mudancas.items() if k != "title"}
                    self._publicador.atualizar_anuncio(token, codigo, {**sem_titulo, "family_name": dados.titulo})
                else:
                    essencial = {"price": mudancas["price"], "available_quantity": mudancas["available_quantity"]}
                    if imagens:
                        essencial["pictures"] = imagens
                    self._publicador.atualizar_anuncio(token, codigo, essencial)
        except FalhaNoMarketplace as erro:
            raise PublicacaoRecusada(_causas(erro.corpo)) from erro

        avisos = []
        if dados.descricao:
            try:
                self._publicador.atualizar_descricao(token, codigo, dados.descricao)
            except FalhaNoMarketplace as erro:
                log.warning("Descrição não atualizada no Mercado Livre (%s).", erro.status or "sem resposta")
                avisos.append({"codigo": "descricao_nao_gravada",
                               "mensagem": "Os dados principais foram salvos, mas a descrição não pôde ser atualizada."})

        atualizado = self._publicador.obter_anuncio(token, codigo)
        return {**atualizado, "avisos": avisos}

    def excluir(self, vendedor_id: int, item_id: str) -> dict[str, Any]:
        token, atual = self._conferir_dono(vendedor_id, item_id)
        codigo = str(atual["id"])
        try:
            self._publicador.excluir_anuncio(token, codigo)
        except FalhaNoMarketplace as erro:
            raise PublicacaoRecusada(_causas(erro.corpo)) from erro
        return {"id": codigo, "excluido": True}
