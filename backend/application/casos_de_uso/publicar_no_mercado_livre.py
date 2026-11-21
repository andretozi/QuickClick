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
import unicodedata
from typing import Any
from urllib.parse import urlparse

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
from backend.application.portas import (
    FalhaNoMarketplace,
    PublicadorMercadoLivre,
    RepositorioDeMidia,
    RepositorioDeProdutos,
)
from backend.domain.erros import (
    AnuncioNaoEncontrado,
    FotoInvalida,
    MercadoLivreDesconectado,
    PublicacaoRecusada,
)
from backend.domain.ia.atributos_ml import (
    MARCA_GENERICA_ML,
    AtributoLigado,
    AtributoML,
    completar_para_publicacao,
    ligar_confirmados,
)

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
_MIDIA_LOCAL_RE = re.compile(r"/api/quickstore/midia/([0-9a-f]{32})\.jpg$", re.IGNORECASE)
_SUFIXO_PAIS_TAMANHO = re.compile(r"\b(?:br|us|eu|uk|arg|col|mx|cm)\b", re.IGNORECASE)
_IDS_COMBINACAO_PADRAO = frozenset({"COLOR", "SIZE"})
_IDS_ATRIB_VARIACAO_PADRAO = frozenset({"SIZE_GRID_ROW_ID", "MAIN_COLOR", "GTIN", "EMPTY_GTIN_REASON"})


def _validar_item_id(item_id: str) -> str:
    codigo = str(item_id or "").strip().upper().replace("-", "")
    if not _FORMATO_ITEM_ID.match(codigo):
        raise ValueError("Identificador do anúncio inválido.")
    return codigo


def _pede_family_name(corpo: Any) -> bool:
    """Categorias no modelo novo do Mercado Livre (User Products) pedem family_name em vez de title."""
    texto = str(corpo or "").lower()
    return "family_name" in texto or ("title" in texto and "invalid" in texto)


def _pede_variacoes(corpo: Any) -> bool:
    """Detecta recusa do Mercado Livre exigindo o envio de cor/tamanho dentro do array variations."""
    texto = str(corpo or "").lower()
    return any(
        termo in texto
        for termo in (
            "attribute_combinations",
            "allow_variations",
            "variation_attribute",
            "item.variations",
            "in variations",
            "en variaciones",
            "variations are required",
            "variaciones son requeridas",
        )
    )


def _erro_tamanho_imagem_ml(corpo: Any) -> bool:
    """Detecta recusa do Mercado Livre por resolução mínima (< 500 px após recorte de bordas brancas)."""
    texto = str(corpo or "").lower()
    return any(termo in texto for termo in ("500", "píxeles", "pixeles", "bordes", "tamaño", "tamano"))


def _normalizar_tamanho(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def _casamento_tamanho(alvo: str, candidato: str) -> int:
    a = _normalizar_tamanho(alvo)
    c = _normalizar_tamanho(candidato)
    if not a or not c:
        return 0
    a_limpo = re.sub(r"\s+", " ", _SUFIXO_PAIS_TAMANHO.sub("", a)).strip()
    c_limpo = re.sub(r"\s+", " ", _SUFIXO_PAIS_TAMANHO.sub("", c)).strip()
    if a == c or (a_limpo and c_limpo and a_limpo == c_limpo):
        return 2
    partes_c = [p.strip() for p in re.split(r"[/\-]", c_limpo or c) if p.strip()]
    partes_a = [p.strip() for p in re.split(r"[/\-]", a_limpo or a) if p.strip()]
    if any(pa in partes_c for pa in partes_a):
        return 1
    return 0


def _escolher_linha_guia(
    rows: list[dict[str, Any]],
    tamanho_alvo: str,
) -> tuple[str, str | None, str | None, int] | None:
    """Seleciona a linha da guia de tamanhos que melhor corresponde ao tamanho do produto."""
    melhor: tuple[str, str | None, str | None, int] | None = None
    primeira_valida: tuple[str, str | None, str | None, int] | None = None

    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = str(row.get("id") or "").strip()
        if not row_id:
            continue
        row_size_name: str | None = None
        row_size_id: str | None = None
        melhor_nota_linha = 0

        for attr in row.get("attributes") or []:
            if not isinstance(attr, dict):
                continue
            attr_id = str(attr.get("id") or "").strip().upper()
            valores = [v for v in (attr.get("values") or []) if isinstance(v, dict)]
            if attr_id == "SIZE" and valores and row_size_name is None:
                row_size_name = str(valores[0].get("name") or "").strip() or None
                row_size_id = str(valores[0].get("id") or "").strip() or None
            if not tamanho_alvo:
                continue
            if attr_id == "SIZE" or attr_id.endswith("_SIZE"):
                for val in valores:
                    nota = _casamento_tamanho(tamanho_alvo, str(val.get("name") or ""))
                    if nota > melhor_nota_linha:
                        melhor_nota_linha = nota

        candidato = (row_id, row_size_name, row_size_id, melhor_nota_linha)
        if primeira_valida is None:
            primeira_valida = candidato
        if melhor_nota_linha == 2:
            return candidato
        if melhor_nota_linha > 0 and (melhor is None or melhor_nota_linha > melhor[3]):
            melhor = candidato

    if melhor is not None:
        return melhor
    return primeira_valida if not tamanho_alvo else None


def _substituir_ou_adicionar_atributo(ligados: list[AtributoLigado], novo: AtributoLigado) -> list[AtributoLigado]:
    saida = list(ligados)
    for idx, item in enumerate(saida):
        if item.id == novo.id:
            saida[idx] = novo
            return saida
    saida.append(novo)
    return saida


def _montar_item_com_variacao(
    item: dict[str, Any],
    ligados: list[AtributoLigado],
    da_categoria: list[AtributoML],
) -> dict[str, Any] | None:
    ids_combinacao = {a.id for a in da_categoria if a.permite_variacao} or set(_IDS_COMBINACAO_PADRAO)
    ids_atrib_variacao = {
        a.id for a in da_categoria if a.atributo_de_variacao and not a.permite_variacao
    } | set(_IDS_ATRIB_VARIACAO_PADRAO)
    ids_atrib_variacao -= ids_combinacao

    combinacoes = [l for l in ligados if l.id in ids_combinacao]
    if not combinacoes:
        return None
    atrib_variacao = [l for l in ligados if l.id in ids_atrib_variacao]
    atrib_raiz = [l for l in ligados if l.id not in ids_combinacao and l.id not in ids_atrib_variacao]

    picture_ids = [
        str(p.get("id") or p.get("source"))
        for p in (item.get("pictures") or [])
        if isinstance(p, dict) and (p.get("id") or p.get("source"))
    ]
    variacao: dict[str, Any] = {
        "price": item["price"],
        "available_quantity": item["available_quantity"],
        "attribute_combinations": [l.para_api() for l in combinacoes],
        "picture_ids": picture_ids,
    }
    if atrib_variacao:
        variacao["attributes"] = [l.para_api() for l in atrib_variacao]

    base = {k: v for k, v in item.items() if k not in ("price", "available_quantity")}
    base["attributes"] = [l.para_api() for l in atrib_raiz]
    base["variations"] = [variacao]
    return base


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
        midia: RepositorioDeMidia | None = None,
    ):
        self._conectar = conectar
        self._publicador = publicador
        self._fonte = fonte
        self._analises = analises
        self._preparador = preparador
        self._produtos = produtos
        self._midia = midia

    def _subir_imagens(self, token: str, preparadas: list[FotoPreparada]) -> list[dict[str, str]]:
        return subir_imagens_no_canal(
            self._publicador,
            self._preparador,
            token,
            preparadas,
            deve_ampliar=_erro_tamanho_imagem_ml,
        )

    def _resolver_fotos_mantidas(self, token: str, urls: tuple[str, ...]) -> list[dict[str, str]]:
        """Reaproveita URLs externas (mlstatic) e sobe fotos locais do /api/quickstore/midia direto ao ML."""
        resolvidas: list[dict[str, str]] = []
        for idx, url in enumerate(urls):
            if self._midia is not None:
                casamento = _MIDIA_LOCAL_RE.search(urlparse(url).path or "")
                if casamento:
                    salva = self._midia.obter(casamento.group(1).lower())
                    if salva is not None:
                        conteudo, _ = salva
                        foto_local = FotoPreparada(indice=idx, leitura_jpeg=conteudo, detalhe_jpeg=conteudo)
                        resolvidas.extend(self._subir_imagens(token, [foto_local]))
                        continue
            resolvidas.append({"source": url})
        return resolvidas

    def _resolver_guia_de_tamanho(
        self,
        token: str,
        categoria_id: str,
        ligados: list[AtributoLigado],
        da_categoria: list[AtributoML],
        *,
        seller_id: str | None = None,
    ) -> list[AtributoLigado]:
        """Quando a categoria exige guia de tamanhos (SIZE_GRID_ID), busca no ML e vincula a linha do tamanho."""
        por_id = {a.id: a for a in da_categoria}
        usados = {l.id: l for l in ligados}
        if "SIZE_GRID_ID" not in por_id or "SIZE_GRID_ID" in usados:
            return ligados

        obter_categoria = getattr(self._publicador, "obter_categoria", None)
        buscar_guias = getattr(self._publicador, "buscar_guias_de_tamanho", None)
        obter_guia = getattr(self._publicador, "obter_guia_de_tamanho", None)
        if not callable(obter_categoria) or not callable(buscar_guias):
            return ligados

        try:
            categoria = obter_categoria(categoria_id, token)
        except FalhaNoMarketplace as erro:
            if erro.status in (401, 403):
                raise
            log.info("Mercado Livre: não foi possível ler catalog_domain de %s (%s).", categoria_id, erro.status)
            return ligados

        catalog_domain = str(((categoria or {}).get("settings") or {}).get("catalog_domain") or "").strip()
        if "-" not in catalog_domain:
            return ligados
        site_id, domain_id = catalog_domain.split("-", 1)
        if not site_id or not domain_id:
            return ligados

        atributos_base: list[dict[str, Any]] = []
        if "GENDER" in usados:
            atributos_base.append(usados["GENDER"].para_api())
        atributos_com_marca = list(atributos_base)
        if "BRAND" in usados and usados["BRAND"].valor and usados["BRAND"].valor != MARCA_GENERICA_ML:
            atributos_com_marca.append(usados["BRAND"].para_api())

        consultas: list[tuple[str | None, list[dict[str, Any]], str | None]] = []
        if seller_id:
            consultas.append(("SPECIFIC", atributos_com_marca, seller_id))
            if atributos_com_marca != atributos_base:
                consultas.append(("SPECIFIC", atributos_base, seller_id))
        if atributos_com_marca != atributos_base:
            consultas.append(("BRAND", atributos_com_marca, None))
        consultas.append(("STANDARD", atributos_base, None))
        consultas.append((None, atributos_base, seller_id))

        tamanho_alvo = usados["SIZE"].valor if "SIZE" in usados else ""
        melhor_global: tuple[str, str, str | None, str | None, int] | None = None

        vistos: set[tuple[str | None, str, str | None]] = set()
        for tipo, attrs, sid in consultas:
            chave_consulta = (tipo, str(attrs), sid)
            if chave_consulta in vistos:
                continue
            vistos.add(chave_consulta)
            try:
                charts = buscar_guias(token, domain_id, site_id, attrs, seller_id=sid, tipo=tipo)
            except FalhaNoMarketplace as erro:
                if erro.status in (401, 403):
                    raise
                log.info("Mercado Livre: busca de guia de tamanhos (%s) falhou (%s).", tipo or "geral", erro.status)
                continue

            for chart in charts:
                chart_id = str(chart.get("id") or "").strip()
                if not chart_id:
                    continue
                rows = chart.get("rows") or []
                if not rows and callable(obter_guia):
                    try:
                        detalhe = obter_guia(token, chart_id)
                        rows = (detalhe or {}).get("rows") or []
                    except FalhaNoMarketplace as erro:
                        if erro.status in (401, 403):
                            raise
                        rows = []
                if not isinstance(rows, list) or not rows:
                    continue
                escolhida = _escolher_linha_guia(rows, tamanho_alvo)
                if escolhida is None:
                    continue
                row_id, row_size_name, row_size_id, nota = escolhida
                if nota == 2:
                    melhor_global = (chart_id, row_id, row_size_name, row_size_id, nota)
                    break
                if melhor_global is None or nota > melhor_global[4]:
                    melhor_global = (chart_id, row_id, row_size_name, row_size_id, nota)
            if melhor_global is not None and melhor_global[4] == 2:
                break

        if melhor_global is None:
            return ligados

        chart_id, row_id, row_size_name, row_size_id, _ = melhor_global
        atualizados = _substituir_ou_adicionar_atributo(ligados, AtributoLigado("SIZE_GRID_ID", chart_id))
        if "SIZE_GRID_ROW_ID" in por_id:
            atualizados = _substituir_ou_adicionar_atributo(atualizados, AtributoLigado("SIZE_GRID_ROW_ID", row_id))
        if row_size_name and "SIZE" in por_id:
            atualizados = _substituir_ou_adicionar_atributo(
                atualizados,
                AtributoLigado("SIZE", row_size_name, row_size_id),
            )
        return atualizados

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
        credenciais = self._conectar.credenciais_ativas(vendedor_id, MERCADO_LIVRE)
        if credenciais is None or not credenciais.access_token:
            raise MercadoLivreDesconectado()
        token = credenciais.access_token
        seller_id = str(credenciais.conta_externa_id or "").strip() or None

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
            ligados = self._resolver_guia_de_tamanho(
                token,
                categoria_id,
                ligados,
                da_categoria,
                seller_id=seller_id,
            )
            imagens_mantidas = self._resolver_fotos_mantidas(token, dados.fotos_mantidas)
            imagens_novas = self._subir_imagens(token, preparadas)
            imagens = (imagens_mantidas + imagens_novas)[:6]
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
                elif _pede_variacoes(erro.corpo):
                    com_variacao = _montar_item_com_variacao(item, ligados, da_categoria)
                    if com_variacao is None:
                        raise
                    log.info("Marketplace pediu variations (cor/tamanho): publicando de novo com variação.")
                    criado = self._publicador.publicar_anuncio(token, com_variacao)
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
            mantidas = self._resolver_fotos_mantidas(token, dados.fotos_mantidas)
            novas = self._subir_imagens(token, preparadas)
        except FalhaNoMarketplace as erro:
            if erro.status in (401, 403):
                raise MercadoLivreDesconectado() from erro
            raise PublicacaoRecusada(_causas(erro.corpo, erro.mensagem), canal=MERCADO_LIVRE) from erro

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
