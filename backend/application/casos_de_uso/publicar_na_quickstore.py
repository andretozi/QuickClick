"""
Aplicação · Publicar, gerir e sincronizar anúncios na QuickStore
"""

import logging
import re
from typing import Any

from backend.application.casos_de_uso.conectar_marketplace import ConectarMarketplace
from backend.application.casos_de_uso.publicar_comum import (
    ANUNCIO_CLASSICO,
    _causas,
    anuncio_de_dict,
    executar_alterar_status,
    executar_excluir,
    subir_imagens_no_canal,
    verificar_duplicidade_no_canal,
    vincular_publicacao_no_produto,
)
from backend.application.ia.modelos import ArquivoDeFoto, FotoPreparada
from backend.application.ia.portas import FontePrecosMarketplace, PreparadorDeFotos, RepositorioDeAnalises
from backend.application.portas import (
    FalhaNoMarketplace,
    PublicadorDeCanal,
    RepositorioDeMidia,
    RepositorioDeProdutos,
)
from backend.domain.erros import (
    AnuncioNaoEncontrado,
    FotoInvalida,
    PublicacaoRecusada,
    QuickStoreDesconectada,
)
from backend.domain.ia.atributos_ml import completar_para_publicacao, ligar_confirmados
from backend.domain.produto import Produto, Publicacao

log = logging.getLogger("quickclick.marketplaces")

QUICKSTORE = "quickstore"
CATEGORIA_PADRAO_QUICKSTORE = "MLB23332"
_FORMATO_ITEM_ID_QUICKSTORE = re.compile(r"^[A-Za-z0-9_-]{1,60}$")


def _erro_indica_url_ou_foto(erro: FalhaNoMarketplace) -> bool:
    texto = " ".join(_causas(erro.corpo, erro.mensagem)).lower()
    return any(termo in texto for termo in ("url", "http://", "https://", "picture", "foto", "imagem", "image"))


def _validar_item_id_quickstore(item_id: str) -> str:
    codigo = str(item_id or "").strip()
    if not _FORMATO_ITEM_ID_QUICKSTORE.match(codigo):
        raise ValueError("Identificador do anúncio inválido.")
    return codigo


def _erro_nao_encontrado_quickstore() -> AnuncioNaoEncontrado:
    return AnuncioNaoEncontrado(
        "Não encontramos esse anúncio na sua conta da QuickStore.",
        canal=QUICKSTORE,
    )


def _publicacao_do_canal(produto: Produto | None, canal: str) -> Publicacao | None:
    if produto is None:
        return None
    for pub in produto.publicacoes:
        if pub.canal == canal:
            return pub
    return None


def _dados_do_produto_mudaram(anterior: Produto, novo: Produto) -> bool:
    pub_antiga = _publicacao_do_canal(anterior, QUICKSTORE)
    pub_nova = _publicacao_do_canal(novo, QUICKSTORE)
    preco_qs_antigo = (
        pub_antiga.preco_centavos if pub_antiga and pub_antiga.preco_centavos is not None else anterior.preco_centavos
    )
    preco_qs_novo = (
        pub_nova.preco_centavos if pub_nova and pub_nova.preco_centavos is not None else novo.preco_centavos
    )
    return (
        anterior.titulo != novo.titulo
        or anterior.descricao != novo.descricao
        or anterior.preco_centavos != novo.preco_centavos
        or preco_qs_antigo != preco_qs_novo
        or anterior.estoque != novo.estoque
        or anterior.condicao != novo.condicao
        or anterior.fotos != novo.fotos
        or anterior.atributos != novo.atributos
    )


def _payload_para_publicador(produto: Produto, pub: Publicacao) -> dict[str, Any]:
    atributos = []
    for item in produto.atributos or []:
        if isinstance(item, dict):
            chave = str(item.get("nome") or item.get("chave") or item.get("id") or "").strip()
            valor = item.get("valor")
            if chave and valor is not None and str(valor).strip() != "":
                atributos.append({"chave": chave, "valor": str(valor).strip()})
    preco_canal = pub.preco_centavos if pub.preco_centavos is not None else produto.preco_centavos
    return {
        "titulo": produto.titulo,
        "descricao": produto.descricao,
        "preco_centavos": max(100, int(preco_canal or 0)),
        "estoque": int(produto.estoque or 0),
        "condicao": produto.condicao,
        "atributos": atributos,
        "analise_id": produto.analise_id,
        "ml_categoria_id": pub.categoria_id,
        "fotos_mantidas": list(produto.fotos or [])[:6],
    }


class PublicarNaQuickStore:
    def __init__(
        self,
        conectar: ConectarMarketplace,
        publicador: PublicadorDeCanal,
        fonte: FontePrecosMarketplace,
        analises: RepositorioDeAnalises,
        preparador: PreparadorDeFotos,
        *,
        produtos: RepositorioDeProdutos | None = None,
        midia: RepositorioDeMidia | None = None,
        url_base_publica: str = "",
    ):
        self._conectar = conectar
        self._publicador = publicador
        self._fonte = fonte
        self._analises = analises
        self._preparador = preparador
        self._produtos = produtos
        self._midia = midia
        self._url_base_publica = str(url_base_publica or "").strip().rstrip("/")

    def _subir_imagens(self, vendedor_id: int, token: str, preparadas: list[FotoPreparada]) -> list[dict[str, str]]:
        if self._midia is not None and self._url_base_publica.startswith(("https://", "http://")):
            imagens: list[dict[str, str]] = []
            for foto in preparadas:
                foto_id = self._midia.salvar(vendedor_id, foto.leitura_jpeg)
                imagens.append({"source": f"{self._url_base_publica}/api/quickstore/midia/{foto_id}.jpg"})
            return imagens
        return subir_imagens_no_canal(
            self._publicador,
            self._preparador,
            token,
            preparadas,
        )

    def _ml_da_analise(self, vendedor_id: int, analise_id: str | None) -> dict[str, Any]:
        if not analise_id:
            return {}
        analise = self._analises.obter(analise_id)
        if analise is None or analise["vendedor_id"] != vendedor_id:
            return {}
        return (analise.get("leitura") or {}).get("ml") or {}

    def _conferir_dono(self, vendedor_id: int, item_id: str) -> tuple[str, dict[str, Any]]:
        codigo = _validar_item_id_quickstore(item_id)
        credenciais = self._conectar.credenciais_ativas(vendedor_id, QUICKSTORE)
        if credenciais is None or not credenciais.access_token:
            raise QuickStoreDesconectada()
        try:
            atual = self._publicador.obter_anuncio(credenciais.access_token, codigo)
        except FalhaNoMarketplace as erro:
            if erro.status in (401, 403):
                raise QuickStoreDesconectada() from erro
            if erro.status == 404:
                raise _erro_nao_encontrado_quickstore() from erro
            raise PublicacaoRecusada(_causas(erro.corpo, erro.mensagem), canal=QUICKSTORE) from erro
        dono_item = str(atual.get("seller_id") or "").strip()
        dono_conta = str(credenciais.conta_externa_id or "").strip()
        if dono_conta and dono_item and dono_item != dono_conta:
            raise _erro_nao_encontrado_quickstore()
        return credenciais.access_token, atual

    def executar(self, vendedor_id: int, anuncio: dict[str, Any], fotos: list[ArquivoDeFoto]) -> dict[str, Any]:
        dados = anuncio_de_dict(anuncio, exigir_mlstatic=False)
        if dados.estoque < 1:
            raise ValueError("O estoque precisa ser de pelo menos 1 unidade.")
        if not fotos and not dados.fotos_mantidas:
            raise FotoInvalida("Escolha pelo menos uma foto para o anúncio.")
        token = self._conectar.token_ativo(vendedor_id, QUICKSTORE)
        if not token:
            raise QuickStoreDesconectada()

        verificar_duplicidade_no_canal(
            self._produtos,
            self._publicador,
            vendedor_id,
            dados.produto_id,
            QUICKSTORE,
            token,
        )

        preparadas = self._preparador.preparar(fotos) if fotos else []

        ml = self._ml_da_analise(vendedor_id, dados.analise_id)
        sugerida_qs = self._fonte.descobrir_categoria([dados.titulo], token)
        if sugerida_qs is not None:
            categoria_id = sugerida_qs.categoria_id
        else:
            categoria_id = dados.ml_categoria_id or ml.get("categoria_id") or CATEGORIA_PADRAO_QUICKSTORE

        da_categoria = self._fonte.atributos_da_categoria(categoria_id, token)
        ligados = completar_para_publicacao(
            ligar_confirmados(list(dados.atributos), da_categoria, ml.get("mapa") or {}),
            da_categoria,
            dados.titulo,
        )

        try:
            imagens_novas = self._subir_imagens(vendedor_id, token, preparadas)
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
                if (
                    erro.status in (400, 422)
                    and categoria_id != CATEGORIA_PADRAO_QUICKSTORE
                    and not _erro_indica_url_ou_foto(erro)
                ):
                    log.info(
                        "QuickStore recusou categoria %s (%s); tentando reenvio com categoria padrão %s.",
                        categoria_id,
                        erro.status,
                        CATEGORIA_PADRAO_QUICKSTORE,
                    )
                    categoria_id = CATEGORIA_PADRAO_QUICKSTORE
                    da_categoria_padrao = self._fonte.atributos_da_categoria(categoria_id, token)
                    ligados_padrao = completar_para_publicacao(
                        ligar_confirmados(list(dados.atributos), da_categoria_padrao, {}),
                        da_categoria_padrao,
                        dados.titulo,
                    )
                    item_fallback = {
                        **item,
                        "category_id": categoria_id,
                        "attributes": [ligado.para_api() for ligado in ligados_padrao],
                    }
                    criado = self._publicador.publicar_anuncio(token, item_fallback)
                else:
                    raise
        except FalhaNoMarketplace as erro:
            if erro.status in (401, 403):
                raise QuickStoreDesconectada() from erro
            causas = _causas(erro.corpo, erro.mensagem)
            log.warning(
                "%s recusou a publicação (%s): %s",
                QUICKSTORE,
                erro.status or "sem resposta",
                "; ".join(causas) or "sem detalhes",
            )
            raise PublicacaoRecusada(causas, canal=QUICKSTORE) from erro

        avisos = []
        item_id = str(criado.get("id") or "")
        if dados.descricao and item_id:
            try:
                self._publicador.gravar_descricao(token, item_id, dados.descricao)
            except FalhaNoMarketplace as erro:
                log.warning("Descrição não gravada em %s (%s).", QUICKSTORE, erro.status or "sem resposta")
                avisos.append(
                    {
                        "codigo": "descricao_nao_gravada",
                        "canal": QUICKSTORE,
                        "mensagem": "O anúncio foi criado, mas a descrição não entrou. Confira na QuickStore.",
                    }
                )
        vincular_publicacao_no_produto(
            self._produtos,
            vendedor_id,
            dados.produto_id,
            canal=QUICKSTORE,
            id_externo=item_id,
            status_externo=criado.get("status"),
            permalink=criado.get("permalink"),
            categoria_id=categoria_id,
        )
        return {
            "id": item_id,
            "permalink": criado.get("permalink"),
            "status": criado.get("status"),
            "categoria_id": categoria_id,
            "fotos": [
                img["source"]
                for img in imagens
                if isinstance(img, dict) and str(img.get("source") or "").startswith("https://")
            ],
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
            canal=QUICKSTORE,
            erro_desconectado=QuickStoreDesconectada,
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
            novas = self._subir_imagens(vendedor_id, token, preparadas)
        except FalhaNoMarketplace as erro:
            if erro.status in (401, 403):
                raise QuickStoreDesconectada() from erro
            raise PublicacaoRecusada(_causas(erro.corpo, erro.mensagem), canal=QUICKSTORE) from erro

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
            "available_quantity": dados.estoque,
            "title": dados.titulo,
            "condition": dados.condicao,
        }
        if imagens:
            mudancas["pictures"] = imagens
        if ligados:
            mudancas["attributes"] = [ligado.para_api() for ligado in ligados]

        try:
            try:
                self._publicador.atualizar_anuncio(token, codigo, mudancas)
            except FalhaNoMarketplace as erro:
                if erro.status in (401, 403):
                    raise
                essencial: dict[str, Any] = {
                    "price": mudancas["price"],
                    "available_quantity": mudancas["available_quantity"],
                    "title": dados.titulo,
                }
                if imagens:
                    essencial["pictures"] = imagens
                self._publicador.atualizar_anuncio(token, codigo, essencial)
        except FalhaNoMarketplace as erro:
            if erro.status in (401, 403):
                raise QuickStoreDesconectada() from erro
            raise PublicacaoRecusada(_causas(erro.corpo, erro.mensagem), canal=QUICKSTORE) from erro

        avisos = []
        try:
            self._publicador.atualizar_descricao(token, codigo, dados.descricao)
        except FalhaNoMarketplace as erro:
            log.warning("Descrição não atualizada em %s (%s).", QUICKSTORE, erro.status or "sem resposta")
            avisos.append(
                {
                    "codigo": "descricao_nao_gravada",
                    "canal": QUICKSTORE,
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
            canal=QUICKSTORE,
            erro_desconectado=QuickStoreDesconectada,
        )


class SincronizadorQuickStore:
    def __init__(self, publicar_na_quickstore: PublicarNaQuickStore):
        self._publicar_na_quickstore = publicar_na_quickstore

    def sincronizar_ao_salvar(self, vendedor_id: int, anterior: Produto | None, salvo: Produto) -> None:
        if anterior is None:
            return
        pub_antiga = _publicacao_do_canal(anterior, QUICKSTORE)
        pub_nova = _publicacao_do_canal(salvo, QUICKSTORE)
        id_antigo = str(pub_antiga.id_externo or "").strip() if pub_antiga else ""
        id_novo = str(pub_nova.id_externo or "").strip() if pub_nova else ""

        if id_antigo and (pub_nova is None or pub_nova.status == "nao_publicado" or not id_novo):
            try:
                self._publicar_na_quickstore.excluir(vendedor_id, id_antigo)
            except Exception as erro:
                log.debug("Não deu para encerrar item %s na QuickStore ao salvar produto: %s", id_antigo, erro)
            return

        if not id_novo or id_novo != id_antigo or pub_nova is None:
            return

        try:
            if _dados_do_produto_mudaram(anterior, salvo):
                self._publicar_na_quickstore.atualizar(
                    vendedor_id,
                    id_novo,
                    _payload_para_publicador(salvo, pub_nova),
                )
            if pub_antiga and pub_antiga.status != pub_nova.status and pub_nova.status in ("publicado", "pausado"):
                self._publicar_na_quickstore.alterar_status(vendedor_id, id_novo, pub_nova.status)
        except Exception as erro:
            log.debug("Não deu para sincronizar item %s na QuickStore ao salvar produto: %s", id_novo, erro)

    def sincronizar_ao_remover(self, vendedor_id: int, anterior: Produto) -> None:
        pub_qs = _publicacao_do_canal(anterior, QUICKSTORE)
        id_qs = str(pub_qs.id_externo or "").strip() if pub_qs else ""
        if id_qs:
            try:
                self._publicar_na_quickstore.excluir(vendedor_id, id_qs)
            except Exception as erro:
                log.debug("Não deu para excluir item %s na QuickStore ao remover produto: %s", id_qs, erro)
