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
from typing import Any

from backend.application.casos_de_uso.conectar_marketplace import ConectarMarketplace
from backend.application.casos_de_uso.publicar_comum import (
    ANUNCIO_CLASSICO,
    CONDICAO_PARA_CANAL as CONDICAO_NO_ML,
    DESCRICAO_MAX as DESCRICAO_MAX_ML,
    ESTOQUE_MAXIMO,
    PRECO_MINIMO_CENTAVOS,
    STATUS_PARA_CANAL as STATUS_PARA_ML,
    AnuncioParaPublicar,
    _causas,
    _resumir_fallback_erro,
    _validar_url_foto as _validar_url_foto_ml,
    anuncio_de_dict,
    executar_alterar_status,
    executar_excluir,
    subir_imagens_no_canal,
    verificar_duplicidade_no_canal,
)
from backend.application.ia.modelos import ArquivoDeFoto, FotoPreparada
from backend.application.ia.portas import FontePrecosMarketplace, PreparadorDeFotos, RepositorioDeAnalises
from backend.application.portas import FalhaNoMarketplace, PublicadorMercadoLivre, RepositorioDeProdutos
from backend.domain.erros import (
    AnuncioNaoEncontrado,
    FotoInvalida,
    MercadoLivreDesconectado,
    PublicacaoRecusada,
)
from backend.domain.ia.atributos_ml import completar_para_publicacao, ligar_confirmados

__all__ = [
    "ANUNCIO_CLASSICO",
    "CONDICAO_NO_ML",
    "DESCRICAO_MAX_ML",
    "ESTOQUE_MAXIMO",
    "MERCADO_LIVRE",
    "PRECO_MINIMO_CENTAVOS",
    "STATUS_PARA_ML",
    "AnuncioParaPublicar",
    "PublicarNoMercadoLivre",
    "_causas",
    "_resumir_fallback_erro",
    "_validar_url_foto_ml",
    "anuncio_de_dict",
]

log = logging.getLogger("quickclick.marketplaces")

MERCADO_LIVRE = "mercado-livre"
_FORMATO_ITEM_ID = re.compile(r"^MLB\d{5,20}$")


def _validar_item_id(item_id: str) -> str:
    codigo = str(item_id or "").strip().upper().replace("-", "")
    if not _FORMATO_ITEM_ID.match(codigo):
        raise ValueError("Identificador do anúncio inválido.")
    return codigo


def _pede_family_name(corpo: Any) -> bool:
    """Categorias no modelo novo do Mercado Livre (User Products) pedem family_name em vez de title."""
    texto = str(corpo or "").lower()
    return "family_name" in texto or ("title" in texto and "invalid" in texto)


def _erro_tamanho_imagem_ml(corpo: Any) -> bool:
    """Detecta recusa do Mercado Livre por resolução mínima (< 500 px após recorte de bordas brancas)."""
    texto = str(corpo or "").lower()
    return any(termo in texto for termo in ("500", "píxeles", "pixeles", "bordes", "tamaño", "tamano"))


class PublicarNoMercadoLivre:
    def __init__(
        self,
        conectar: ConectarMarketplace,
        publicador: PublicadorMercadoLivre,
        fonte: FontePrecosMarketplace,
        analises: RepositorioDeAnalises,
        preparador: PreparadorDeFotos,
        *,
        produtos: RepositorioDeProdutos | None = None,
    ):
        self._conectar = conectar
        self._publicador = publicador
        self._fonte = fonte
        self._analises = analises
        self._preparador = preparador
        self._produtos = produtos

    def _subir_imagens(self, token: str, preparadas: list[FotoPreparada]) -> list[dict[str, str]]:
        return subir_imagens_no_canal(
            self._publicador,
            self._preparador,
            token,
            preparadas,
            deve_ampliar=_erro_tamanho_imagem_ml,
        )

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
            if erro.status in (401, 403):
                raise MercadoLivreDesconectado() from erro
            if erro.status == 404:
                raise AnuncioNaoEncontrado(canal=MERCADO_LIVRE) from erro
            raise PublicacaoRecusada(_causas(erro.corpo, erro.mensagem), canal=MERCADO_LIVRE) from erro
        dono_item = str(atual.get("seller_id") or "").strip()
        dono_conta = str(credenciais.conta_externa_id or "").strip()
        if dono_conta and dono_item and dono_item != dono_conta:
            raise AnuncioNaoEncontrado(canal=MERCADO_LIVRE)
        return credenciais.access_token, atual

    def executar(self, vendedor_id: int, anuncio: dict[str, Any], fotos: list[ArquivoDeFoto]) -> dict[str, Any]:
        dados = anuncio_de_dict(anuncio, exigir_mlstatic=False)
        if dados.estoque < 1:
            raise ValueError("O estoque precisa ser de pelo menos 1 unidade.")
        if not fotos and not dados.fotos_mantidas:
            raise FotoInvalida("Escolha pelo menos uma foto para o anúncio.")
        token = self._conectar.token_ativo(vendedor_id, MERCADO_LIVRE)
        if not token:
            raise MercadoLivreDesconectado()

        verificar_duplicidade_no_canal(
            self._produtos,
            self._publicador,
            vendedor_id,
            dados.produto_id,
            MERCADO_LIVRE,
            token,
        )

        preparadas = self._preparador.preparar(fotos) if fotos else []

        ml = self._ml_da_analise(vendedor_id, dados.analise_id)
        categoria_id = dados.ml_categoria_id or ml.get("categoria_id")
        if not categoria_id:
            sugerida = self._fonte.descobrir_categoria([dados.titulo], token)
            if sugerida is None:
                raise PublicacaoRecusada(
                    ["Não consegui descobrir a categoria do Mercado Livre para esse título."],
                    canal=MERCADO_LIVRE,
                )
            categoria_id = sugerida.categoria_id
        da_categoria = self._fonte.atributos_da_categoria(categoria_id, token)
        ligados = completar_para_publicacao(
            ligar_confirmados(list(dados.atributos), da_categoria, ml.get("mapa") or {}),
            da_categoria,
            dados.titulo,
        )

        try:
            imagens_novas = self._subir_imagens(token, preparadas)
            imagens = ([{"source": url} for url in dados.fotos_mantidas] + imagens_novas)[:6]
            item = {
                "title": dados.titulo,
                "category_id": categoria_id,
                "price": dados.preco_centavos / 100,
                "currency_id": "BRL",
                "available_quantity": dados.estoque,
                "buying_mode": "buy_it_now",
                "condition": dados.condicao,
                "listing_type_id": ANUNCIO_CLASSICO,
                "pictures": imagens,
                "attributes": [ligado.para_api() for ligado in ligados],
            }
            try:
                criado = self._publicador.publicar_anuncio(token, item)
            except FalhaNoMarketplace as erro:
                if erro.status in (401, 403):
                    raise
                if _pede_family_name(erro.corpo):
                    log.info("Marketplace pediu family_name (User Products): publicando de novo com ele.")
                    sem_titulo = {k: v for k, v in item.items() if k != "title"}
                    criado = self._publicador.publicar_anuncio(token, {**sem_titulo, "family_name": dados.titulo})
                else:
                    raise
        except FalhaNoMarketplace as erro:
            if erro.status in (401, 403):
                raise MercadoLivreDesconectado() from erro
            causas = _causas(erro.corpo, erro.mensagem)
            log.warning(
                "%s recusou a publicação (%s): %s",
                MERCADO_LIVRE,
                erro.status or "sem resposta",
                "; ".join(causas) or "sem detalhes",
            )
            raise PublicacaoRecusada(causas, canal=MERCADO_LIVRE) from erro

        avisos = []
        item_id = str(criado.get("id") or "")
        if dados.descricao and item_id:
            try:
                self._publicador.gravar_descricao(token, item_id, dados.descricao)
            except FalhaNoMarketplace as erro:
                log.warning("Descrição não gravada em %s (%s).", MERCADO_LIVRE, erro.status or "sem resposta")
                avisos.append(
                    {
                        "codigo": "descricao_nao_gravada",
                        "canal": MERCADO_LIVRE,
                        "mensagem": "O anúncio foi criado, mas a descrição não entrou. Confira no Mercado Livre.",
                    }
                )
        return {
            "id": item_id,
            "permalink": criado.get("permalink"),
            "status": criado.get("status"),
            "categoria_id": categoria_id,
            "avisos": avisos,
        }

    def obter(self, vendedor_id: int, item_id: str) -> dict[str, Any]:
        _, atual = self._conferir_dono(vendedor_id, item_id)
        return atual

    def alterar_status(self, vendedor_id: int, item_id: str, status: str) -> dict[str, Any]:
        token, atual = self._conferir_dono(vendedor_id, item_id)
        return executar_alterar_status(
            self._publicador,
            token,
            str(atual["id"]),
            status,
            canal=MERCADO_LIVRE,
            erro_desconectado=MercadoLivreDesconectado,
        )

    def atualizar(
        self,
        vendedor_id: int,
        item_id: str,
        anuncio: dict[str, Any],
        fotos: list[ArquivoDeFoto] | None = None,
    ) -> dict[str, Any]:
        dados = anuncio_de_dict(anuncio, exigir_mlstatic=False)
        token, atual = self._conferir_dono(vendedor_id, item_id)
        codigo = str(atual["id"])
        preparadas = self._preparador.preparar(fotos) if fotos else []

        try:
            novas = self._subir_imagens(token, preparadas)
        except FalhaNoMarketplace as erro:
            if erro.status in (401, 403):
                raise MercadoLivreDesconectado() from erro
            raise PublicacaoRecusada(_causas(erro.corpo, erro.mensagem), canal=MERCADO_LIVRE) from erro

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

        zerando_ml_ativo = dados.estoque == 0 and str(atual.get("status") or "").strip().lower() == "active"
        mudancas: dict[str, Any] = {
            "price": dados.preco_centavos / 100,
            "available_quantity": (
                dados.estoque
                if zerando_ml_ativo
                else (max(1, dados.estoque) if atual.get("status") == "active" else dados.estoque)
            ),
        }
        if zerando_ml_ativo:
            mudancas["status"] = "paused"
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
                if erro.status in (401, 403):
                    raise
                if _pede_family_name(erro.corpo) and "title" in mudancas:
                    sem_titulo = {k: v for k, v in mudancas.items() if k != "title"}
                    self._publicador.atualizar_anuncio(token, codigo, {**sem_titulo, "family_name": dados.titulo})
                else:
                    essencial: dict[str, Any] = {
                        "price": mudancas["price"],
                        "available_quantity": 1 if zerando_ml_ativo else mudancas["available_quantity"],
                    }
                    if zerando_ml_ativo:
                        essencial["status"] = "paused"
                    if imagens:
                        essencial["pictures"] = imagens
                    self._publicador.atualizar_anuncio(token, codigo, essencial)
        except FalhaNoMarketplace as erro:
            if erro.status in (401, 403):
                raise MercadoLivreDesconectado() from erro
            raise PublicacaoRecusada(_causas(erro.corpo, erro.mensagem), canal=MERCADO_LIVRE) from erro

        avisos = []
        if dados.descricao:
            try:
                self._publicador.atualizar_descricao(token, codigo, dados.descricao)
            except FalhaNoMarketplace as erro:
                log.warning("Descrição não atualizada em %s (%s).", MERCADO_LIVRE, erro.status or "sem resposta")
                avisos.append(
                    {
                        "codigo": "descricao_nao_gravada",
                        "canal": MERCADO_LIVRE,
                        "mensagem": "Os dados principais foram salvos, mas a descrição não pôde ser atualizada.",
                    }
                )

        atualizado = self._publicador.obter_anuncio(token, codigo)
        return {**atualizado, "avisos": avisos}

    def excluir(self, vendedor_id: int, item_id: str) -> dict[str, Any]:
        token, atual = self._conferir_dono(vendedor_id, item_id)
        return executar_excluir(
            self._publicador,
            token,
            str(atual["id"]),
            canal=MERCADO_LIVRE,
            erro_desconectado=MercadoLivreDesconectado,
        )
