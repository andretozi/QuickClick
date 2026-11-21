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
    vincular_publicacao_no_produto,
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
    _valor_id,
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
_DOMINIOS_CALCADOS_ML = frozenset({
    "SANDALS_AND_CLOGS",
    "SNEAKERS",
    "BOOTS_AND_BOOTIES",
    "LOAFERS_AND_OXFORDS",
    "FOOTBALL_SHOES",
    "SLIPPERS",
    "FLATS",
    "HIGH_HEELS",
    "ESPADRILLES",
    "MOCCASINS",
})
_IDS_GENERO_INFANTIL_ML = frozenset({"339667", "339668", "19159491"})


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
    normalizado = re.sub(r"\s+", " ", sem_acento.lower()).strip()
    return re.sub(r"\b(\d+)[.,]0+\b", r"\1", normalizado)


def _casamento_tamanho(alvo: str, candidato: str) -> int:
    a = _normalizar_tamanho(alvo)
    c = _normalizar_tamanho(candidato)
    if not a or not c:
        return 0
    a_limpo = re.sub(r"\s+", " ", _SUFIXO_PAIS_TAMANHO.sub("", a)).strip()
    c_limpo = re.sub(r"\s+", " ", _SUFIXO_PAIS_TAMANHO.sub("", c)).strip()
    if a == c or (a_limpo and c_limpo and a_limpo == c_limpo):
        return 2
    partes_c = [p.strip() for p in re.split(r"[/\-]|\s+a\s+", c_limpo or c) if p.strip()]
    partes_a = [p.strip() for p in re.split(r"[/\-]|\s+a\s+", a_limpo or a) if p.strip()]
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
        fallback_size_name: str | None = None
        melhor_nota_linha = 0

        for attr in row.get("attributes") or []:
            if not isinstance(attr, dict):
                continue
            attr_id = str(attr.get("id") or "").strip().upper()
            valores = [v for v in (attr.get("values") or []) if isinstance(v, dict)]
            if attr_id == "SIZE" and valores and row_size_name is None:
                row_size_name = str(valores[0].get("name") or "").strip() or None
                row_size_id = str(valores[0].get("id") or "").strip() or None
            elif attr_id.endswith("_SIZE") and valores:
                nome_val = str(valores[0].get("name") or "").strip() or None
                if nome_val and (fallback_size_name is None or attr_id == "BR_SIZE"):
                    fallback_size_name = nome_val
            if not tamanho_alvo:
                continue
            if attr_id == "SIZE" or attr_id.endswith("_SIZE"):
                for val in valores:
                    nota = _casamento_tamanho(tamanho_alvo, str(val.get("name") or ""))
                    if nota > melhor_nota_linha:
                        melhor_nota_linha = nota

        candidato = (row_id, row_size_name or fallback_size_name, row_size_id, melhor_nota_linha)
        if primeira_valida is None:
            primeira_valida = candidato
        if melhor_nota_linha == 2:
            return candidato
        if melhor_nota_linha > 0 and (melhor is None or melhor_nota_linha > melhor[3]):
            melhor = candidato

    if melhor is not None:
        return melhor
    return primeira_valida if not tamanho_alvo else None


def _atributo_para_busca_guia(
    ligado: AtributoLigado,
    atributo_cat: AtributoML | None,
) -> dict[str, Any] | None:
    """Serializa um atributo no contrato de POST /catalog/charts/search ({id, values: [{id, name}]})."""
    nome_canonico: str | None = None
    if ligado.valor_id and atributo_cat is not None:
        for opcao in atributo_cat.valores or ():
            if isinstance(opcao, tuple) and len(opcao) >= 2:
                opc_id, opc_nome = str(opcao[0]), str(opcao[1])
            else:
                opc_id = str(getattr(opcao, "id", "") or "")
                opc_nome = str(getattr(opcao, "nome", "") or "")
            if opc_id == ligado.valor_id and opc_nome:
                nome_canonico = opc_nome
                break
    valor: dict[str, str] = {}
    if ligado.valor_id:
        valor["id"] = ligado.valor_id
    nome = (nome_canonico or ligado.valor or "").strip()
    if nome:
        valor["name"] = nome
    if not valor:
        return None
    return {"id": ligado.id, "values": [valor]}


def _extrair_colunas_especificacao_guia(spec: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Extrai os atributos/colunas da especificação de grade (technical_specs?section=grids)."""
    colunas: dict[str, dict[str, Any]] = {}

    def _visitar(lista: Any) -> None:
        if not isinstance(lista, list):
            return
        for item in lista:
            if not isinstance(item, dict):
                continue
            attrs = item.get("attributes")
            if isinstance(attrs, list):
                for attr in attrs:
                    if isinstance(attr, dict) and attr.get("id"):
                        colunas[str(attr["id"]).strip().upper()] = attr
            _visitar(item.get("components"))

    if isinstance(spec, dict):
        entrada = spec.get("input") or spec
        if isinstance(entrada, dict):
            _visitar(entrada.get("groups"))
            _visitar(entrada.get("components"))
    return colunas


def _eh_genero_infantil_ml(usados: dict[str, AtributoLigado]) -> bool:
    genero = usados.get("GENDER")
    if genero is None:
        return False
    if genero.valor_id and genero.valor_id in _IDS_GENERO_INFANTIL_ML:
        return True
    norm = _normalizar_tamanho(genero.valor)
    return any(termo in norm for termo in ("menin", "infantil", "bebe", "crianca"))


def _extrair_numero_tamanho_br(tamanho_alvo: str, *, infantil: bool = False) -> int | None:
    if not tamanho_alvo:
        return None
    limpo = _SUFIXO_PAIS_TAMANHO.sub("", _normalizar_tamanho(tamanho_alvo))
    numeros = [int(n) for n in re.findall(r"\b(\d{2})\b", limpo)]
    if not numeros:
        return None
    minimo, maximo = (15, 36) if infantil else (30, 51)
    for num in reversed(numeros):
        if minimo <= num <= maximo:
            return num
    for num in reversed(numeros):
        if 15 <= num <= 51:
            return num
    return None


def _comprimento_pe_cm(numero_br: int) -> str:
    """Converte tamanho BR em comprimento aproximado do pé em cm (dentro da faixa oficial 5.0–40.0 cm do ML)."""
    cm = round(max(10.0, min(35.0, 11.0 + (numero_br - 16) * 0.65)), 1)
    return f"{cm:.1f} cm"


def _linha_calcado_mlb(numero_br: int) -> list[dict[str, Any]]:
    return [
        {"id": "BR_SIZE", "values": [{"name": f"{numero_br} BR"}]},
        {"id": "FOOT_LENGTH", "values": [{"name": _comprimento_pe_cm(numero_br)}]},
    ]


def _montar_payload_guia_especifica(
    *,
    site_id: str,
    domain_id: str,
    atributos_base: list[dict[str, Any]],
    tamanho_alvo: str,
    usados: dict[str, AtributoLigado],
    por_id: dict[str, AtributoML],
    colunas_spec: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    eh_calcado = (
        "BR_SIZE" in colunas_spec
        or "FOOT_LENGTH" in colunas_spec
        or "FOOTWEAR_TYPE" in por_id
        or domain_id.upper() in _DOMINIOS_CALCADOS_ML
    )
    genero_nome = ""
    if atributos_base:
        vals = atributos_base[0].get("values") or []
        if vals and isinstance(vals[0], dict):
            genero_nome = str(vals[0].get("name") or "").strip()
    nome_guia = re.sub(r"\s+", " ", f"Guia {domain_id[:24]} {genero_nome[:18]}").strip()[:60] or "Guia Padrao"

    if eh_calcado:
        infantil = _eh_genero_infantil_ml(usados)
        numero_alvo = _extrair_numero_tamanho_br(tamanho_alvo, infantil=infantil)
        if numero_alvo is not None and numero_alvo < 32 and not infantil:
            infantil = True
        faixa_base = list(range(20, 35)) if infantil else list(range(34, 45))
        if numero_alvo is not None and numero_alvo not in faixa_base:
            faixa_base = sorted({*faixa_base, numero_alvo})
        rows = [{"attributes": _linha_calcado_mlb(n)} for n in faixa_base]
        return {
            "names": {site_id: nome_guia},
            "domain_id": domain_id,
            "site_id": site_id,
            "type": "SPECIFIC",
            "main_attribute": {"attributes": [{"site_id": site_id, "id": "BR_SIZE"}]},
            "attributes": atributos_base,
            "rows": rows,
        }

    if "SIZE" in colunas_spec or "SIZE" in por_id:
        alvo_limpo = (tamanho_alvo or "").strip() or "M"
        tamanhos = ["P", "M", "G", "GG"]
        if all(_casamento_tamanho(alvo_limpo, t) == 0 for t in tamanhos):
            tamanhos.append(alvo_limpo)
        filtrable_spec = colunas_spec.get("FILTRABLE_SIZE") or {}
        filtrable_vals = [
            v for v in (filtrable_spec.get("values") or []) if isinstance(v, dict) and (v.get("id") or v.get("name"))
        ]
        rows_vestuario: list[dict[str, Any]] = []
        for tam in tamanhos:
            attrs_linha: list[dict[str, Any]] = [{"id": "SIZE", "values": [{"name": tam}]}]
            if filtrable_vals:
                escolhido = next(
                    (v for v in filtrable_vals if _casamento_tamanho(tam, str(v.get("name") or "")) > 0),
                    filtrable_vals[0],
                )
                val_f: dict[str, str] = {}
                if escolhido.get("id"):
                    val_f["id"] = str(escolhido["id"])
                if escolhido.get("name"):
                    val_f["name"] = str(escolhido["name"])
                if val_f:
                    attrs_linha.append({"id": "FILTRABLE_SIZE", "values": [val_f]})
            for col_id in colunas_spec:
                if col_id.endswith("_FROM") and col_id not in ("FOOT_LENGTH_FROM",):
                    attrs_linha.append({"id": col_id, "values": [{"name": "90 cm"}]})
            rows_vestuario.append({"attributes": attrs_linha})
        return {
            "names": {site_id: nome_guia},
            "domain_id": domain_id,
            "site_id": site_id,
            "type": "SPECIFIC",
            "main_attribute": {"attributes": [{"site_id": site_id, "id": "SIZE"}]},
            "attributes": atributos_base,
            "rows": rows_vestuario,
        }

    return None


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

    def _criar_ou_estender_guia_especifica(
        self,
        *,
        token: str,
        catalog_domain: str,
        site_id: str,
        domain_id: str,
        atributos_base: list[dict[str, Any]],
        tamanho_alvo: str,
        usados: dict[str, AtributoLigado],
        por_id: dict[str, AtributoML],
        guia_especifica_sem_linha: dict[str, Any] | None,
    ) -> tuple[str, str, str | None, str | None, int] | None:
        """Adiciona uma linha à guia SPECIFIC do vendedor ou cria uma nova guia SPECIFIC no ML."""
        obter_guia = getattr(self._publicador, "obter_guia_de_tamanho", None)
        adicionar_linha = getattr(self._publicador, "adicionar_linha_guia_de_tamanho", None)
        criar_guia = getattr(self._publicador, "criar_guia_de_tamanho", None)
        obter_spec = getattr(self._publicador, "obter_especificacao_guia", None)

        colunas_spec: dict[str, dict[str, Any]] = {}
        if callable(obter_spec):
            try:
                spec = obter_spec(token, catalog_domain, atributos_base)
                colunas_spec = _extrair_colunas_especificacao_guia(spec)
            except FalhaNoMarketplace as erro:
                if erro.status in (401, 403):
                    raise

        eh_calcado = (
            "BR_SIZE" in colunas_spec
            or "FOOT_LENGTH" in colunas_spec
            or "FOOTWEAR_TYPE" in por_id
            or domain_id.upper() in _DOMINIOS_CALCADOS_ML
        )

        if guia_especifica_sem_linha is not None and tamanho_alvo and callable(adicionar_linha):
            chart_id_existente = str(guia_especifica_sem_linha.get("id") or "").strip()
            numero_br = _extrair_numero_tamanho_br(tamanho_alvo, infantil=_eh_genero_infantil_ml(usados))
            if chart_id_existente and eh_calcado and numero_br is not None:
                try:
                    resp_linha = adicionar_linha(token, chart_id_existente, _linha_calcado_mlb(numero_br))
                    rows_novas = (resp_linha or {}).get("rows") or []
                    if not rows_novas and isinstance(resp_linha, dict) and resp_linha.get("id"):
                        rows_novas = [resp_linha]
                    if not rows_novas and callable(obter_guia):
                        detalhe = obter_guia(token, chart_id_existente)
                        rows_novas = (detalhe or {}).get("rows") or []
                    if isinstance(rows_novas, list) and rows_novas:
                        escolhida = _escolher_linha_guia(rows_novas, tamanho_alvo)
                        if escolhida is not None:
                            row_id, row_size_name, row_size_id, nota = escolhida
                            return (chart_id_existente, row_id, row_size_name, row_size_id, nota)
                except FalhaNoMarketplace as erro:
                    if erro.status in (401, 403):
                        raise
                    detalhe_erro = "; ".join(_causas(erro.corpo, erro.mensagem)) or erro.mensagem
                    log.warning(
                        "Mercado Livre: falha ao adicionar linha '%s' na guia %s (%s): %s",
                        tamanho_alvo,
                        chart_id_existente,
                        erro.status,
                        detalhe_erro,
                    )

        if not callable(criar_guia):
            return None

        payload = _montar_payload_guia_especifica(
            site_id=site_id,
            domain_id=domain_id,
            atributos_base=atributos_base,
            tamanho_alvo=tamanho_alvo,
            usados=usados,
            por_id=por_id,
            colunas_spec=colunas_spec,
        )
        if payload is None:
            return None

        try:
            criada = criar_guia(token, payload)
        except FalhaNoMarketplace as erro:
            if erro.status in (401, 403):
                raise
            detalhe_erro = "; ".join(_causas(erro.corpo, erro.mensagem)) or erro.mensagem
            log.warning(
                "Mercado Livre: falha ao criar guia de tamanhos SPECIFIC para %s-%s (%s): %s | corpo=%s",
                site_id,
                domain_id,
                erro.status,
                detalhe_erro,
                erro.corpo,
            )
            return None

        chart_id = str((criada or {}).get("id") or "").strip()
        if not chart_id:
            return None
        rows = (criada or {}).get("rows") or []
        if not rows and callable(obter_guia):
            try:
                detalhe = obter_guia(token, chart_id)
                rows = (detalhe or {}).get("rows") or []
            except FalhaNoMarketplace as erro:
                if erro.status in (401, 403):
                    raise
                rows = []
        if not isinstance(rows, list) or not rows:
            return None
        escolhida = _escolher_linha_guia(rows, tamanho_alvo) or _escolher_linha_guia(rows, "")
        if escolhida is None:
            return None
        row_id, row_size_name, row_size_id, nota = escolhida
        log.info(
            "Mercado Livre: guia de tamanhos SPECIFIC %s criada automaticamente para %s-%s (linha %s).",
            chart_id,
            site_id,
            domain_id,
            row_id,
        )
        return (chart_id, row_id, row_size_name, row_size_id, nota)

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

        if not seller_id:
            obter_perfil = getattr(self._publicador, "obter_perfil_usuario", None)
            if callable(obter_perfil):
                try:
                    perfil = obter_perfil(token)
                    seller_id = str((perfil or {}).get("id") or "").strip() or None
                except FalhaNoMarketplace as erro:
                    if erro.status in (401, 403):
                        raise

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
            attr_genero = _atributo_para_busca_guia(usados["GENDER"], por_id.get("GENDER"))
            if attr_genero is not None:
                atributos_base.append(attr_genero)
        atributos_com_marca = list(atributos_base)
        if "BRAND" in usados and usados["BRAND"].valor and usados["BRAND"].valor != MARCA_GENERICA_ML:
            attr_marca = _atributo_para_busca_guia(usados["BRAND"], por_id.get("BRAND"))
            if attr_marca is not None:
                atributos_com_marca.append(attr_marca)

        consultas: list[tuple[str | None, list[dict[str, Any]], str | None]] = []
        if seller_id:
            consultas.append(("SPECIFIC", atributos_com_marca, seller_id))
            if atributos_com_marca != atributos_base:
                consultas.append(("SPECIFIC", atributos_base, seller_id))
        if atributos_com_marca != atributos_base:
            consultas.append(("BRAND", atributos_com_marca, seller_id))
        consultas.append(("STANDARD", atributos_base, seller_id))

        tamanho_alvo = usados["SIZE"].valor if "SIZE" in usados else ""
        melhor_global: tuple[str, str, str | None, str | None, int] | None = None
        encontrou_guia = False
        guia_especifica_sem_linha: dict[str, Any] | None = None

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
                detalhe_erro = "; ".join(_causas(erro.corpo, erro.mensagem)) or erro.mensagem
                log.info(
                    "Mercado Livre: busca de guia de tamanhos (%s) falhou (%s): %s",
                    tipo or "geral",
                    erro.status,
                    detalhe_erro,
                )
                continue

            if not charts:
                log.info(
                    "Mercado Livre: busca de guia de tamanhos (%s) retornou 0 guias para %s-%s.",
                    tipo or "geral",
                    site_id,
                    domain_id,
                )
                continue

            for chart in charts:
                chart_id = str(chart.get("id") or "").strip()
                if not chart_id:
                    continue
                encontrou_guia = True
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
                    if tipo == "SPECIFIC" and guia_especifica_sem_linha is None:
                        guia_especifica_sem_linha = chart
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
            if encontrou_guia and tamanho_alvo:
                log.info(
                    "Mercado Livre: nenhuma linha de guia de tamanhos de %s casou com '%s'.",
                    domain_id,
                    tamanho_alvo,
                )
            melhor_global = self._criar_ou_estender_guia_especifica(
                token=token,
                catalog_domain=catalog_domain,
                site_id=site_id,
                domain_id=domain_id,
                atributos_base=atributos_base,
                tamanho_alvo=tamanho_alvo,
                usados=usados,
                por_id=por_id,
                guia_especifica_sem_linha=guia_especifica_sem_linha,
            )
            if melhor_global is None:
                return ligados

        chart_id, row_id, row_size_name, row_size_id, _ = melhor_global
        atualizados = _substituir_ou_adicionar_atributo(ligados, AtributoLigado("SIZE_GRID_ID", chart_id))
        if "SIZE_GRID_ROW_ID" in por_id:
            atualizados = _substituir_ou_adicionar_atributo(atualizados, AtributoLigado("SIZE_GRID_ROW_ID", row_id))
        if row_size_name and "SIZE" in por_id:
            valor_id_size = row_size_id or _valor_id(por_id["SIZE"], row_size_name)
            atualizados = _substituir_ou_adicionar_atributo(
                atualizados,
                AtributoLigado("SIZE", row_size_name, valor_id_size),
            )
        log.info("Mercado Livre: guia de tamanhos %s (linha %s) vinculada para %s.", chart_id, row_id, domain_id)
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
        vincular_publicacao_no_produto(
            self._produtos,
            vendedor_id,
            dados.produto_id,
            canal=MERCADO_LIVRE,
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
