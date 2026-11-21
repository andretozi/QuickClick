"""
Domínio · IA · Ligar os atributos lidos aos atributos de uma categoria do Mercado Livre

Primeiro por regra (IDs conhecidos, nome e sinônimos); só as sobras vão para a IA rápida.
Obrigatórios da categoria que ficaram sem valor viram perguntas para o vendedor.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from backend.domain.canais.esquema import CampoDoCanal, EsquemaDoCanal, TipoDeCampo

CANAL_ML = "mercado-livre"  # id do catálogo (backend/domain/marketplace.py)

# chave nossa → IDs de atributo do Mercado Livre que costumam significar a mesma coisa
SINONIMOS_ML: dict[str, tuple[str, ...]] = {
    "marca": ("BRAND",),
    "fabricante": ("MANUFACTURER",),
    "modelo": ("MODEL", "LINE"),
    "cor": ("COLOR", "MAIN_COLOR"),
    "material": ("MATERIAL", "MAIN_MATERIAL"),
    "tamanho": ("SIZE",),
    "voltagem": ("VOLTAGE",),
    "quantidade": ("UNITS_PER_PACK", "UNITS_PER_PACKAGE", "PACKAGE_QUANTITY"),
    "genero": ("GENDER",),
    "capacidade": ("CAPACITY", "VOLUME_CAPACITY"),
    "potencia": ("POWER",),
    "estampa": ("PATTERN_NAME",),
}

MARCA_GENERICA_ML = "Genérica"
MODELO_PADRAO_ML = "Padrão"
MOTIVO_SEM_GTIN_ML = "O produto não tem código cadastrado"
TERMOS_DE_KIT = ("kit", "conjunto", "jogo", "pack")
IDS_QUANTIDADE_ML = ("UNITS_PER_PACK", "UNITS_PER_PACKAGE", "PACKAGE_QUANTITY")
# Obrigatórios que completar_para_publicacao preenche sozinho (o GTIN fica coberto pelo EMPTY_GTIN_REASON)
PREENCHIDOS_NA_PUBLICACAO_ML = frozenset({"BRAND", "MANUFACTURER", "MODEL", "SALE_FORMAT", "UNITS_PER_PACK",
                                          "IS_SET", "EMPTY_GTIN_REASON", "GTIN"})
# Atributos gerenciados/calculados pelo próprio Mercado Livre (read_only/non_modifiable).
# Mantemos essa lista como rede de segurança além das tags da API para proteger caches antigos de 24h.
IDS_SOMENTE_LEITURA_ML = frozenset({
    "FILTRABLE_SIZE",
    "SIZE_COVERAGE",
    "PACKAGE_HEIGHT",
    "PACKAGE_WIDTH",
    "PACKAGE_LENGTH",
    "PACKAGE_WEIGHT",
    "SELLER_PACKAGE_DATA_SOURCE",
    "IS_HIGHLIGHT_BRAND",
    "VALUE_ADDED_TAX",
    "IMPORT_DUTY",
    "HAZMAT_TRANSPORTABILITY",
    "DESCRIPTIVE_TAGS",
    "PRODUCT_CHEMICAL_FEATURES",
    "FOODS_AND_DRINKS",
    "MEDICINES",
    "BATTERIES_FEATURES",
    "SHIPMENT_PACKING",
    "ADDITIONAL_INFO_REQUIRED",
    "EXCLUDED_PLATFORMS",
    "IS_SUITABLE_FOR_SHIPMENT",
    "LIMITED_MARKETPLACE_VISIBILITY_REASONS",
    "HAS_COMPATIBILITIES",
    "CATALOG_TITLE",
    "SEARCH_ENHANCEMENT_FIELDS",
    "PRODUCT_FEATURES",
    "IS_NEW_OFFER",
    "SYI_PYMES_ID",
    "IS_FLAMMABLE",
})
# Sinônimos comuns para atributos de lista fechada do ML Brasil (ex.: GENDER não aceita "Unissex", só "Sem gênero")
ALIASES_VALORES_ML: dict[str, dict[str, str]] = {
    "GENDER": {
        "unissex": "sem genero",
        "unisex": "sem genero",
        "neutro": "sem genero",
        "neutra": "sem genero",
        "ambos": "sem genero",
        "todos": "sem genero",
        "sem genero": "sem genero",
        "genero neutro": "sem genero",
        "unissex infantil": "sem genero infantil",
        "infantil unissex": "sem genero infantil",
        "infantil": "sem genero infantil",
        "masculino": "masculino",
        "masculina": "masculino",
        "homem": "masculino",
        "homens": "masculino",
        "feminino": "feminino",
        "feminina": "feminino",
        "mulher": "feminino",
        "mulheres": "feminino",
        "menino": "meninos",
        "meninos": "meninos",
        "menina": "meninas",
        "meninas": "meninas",
    },
}
UNIDADES_CANONICAS = {"ml": "mL", "l": "L", "cc": "cc", "cm": "cm", "mm": "mm", "m": "m", "g": "g", "kg": "kg"}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).strip()


def _neutro(texto: str) -> str:
    """Flexão de gênero comum em cores e adjetivos ('branca' → 'branco', 'rosa clara' → 'rosa claro')."""
    palavras = _normalizar(texto).split()
    return " ".join(p[:-1] + "o" if len(p) > 3 and p.endswith("a") else p for p in palavras)


@dataclass(frozen=True)
class AtributoML:
    id: str
    nome: str
    obrigatorio: bool
    valores: tuple[tuple[str, str], ...] = ()  # (id do valor, nome do valor), quando a lista é fechada
    unidade_padrao: str = ""
    tipo_valor: str = ""  # value_type do ML (string, number, number_unit, list, boolean); vazio no cache antigo
    somente_leitura: bool = False
    oculto: bool = False
    permite_variacao: bool = False
    atributo_de_variacao: bool = False

    @staticmethod
    def de_api(bruto: dict[str, Any]) -> "AtributoML":
        tags = bruto.get("tags") or {}
        tags_dict = tags if isinstance(tags, dict) else {}
        attr_id = str(bruto.get("id"))
        obrigatorio = bool(tags_dict.get("required") or tags_dict.get("catalog_required"))
        somente_leitura = bool(
            tags_dict.get("read_only")
            or tags_dict.get("non_modifiable")
            or attr_id in IDS_SOMENTE_LEITURA_ML
        )
        oculto = bool(tags_dict.get("hidden"))
        permite_variacao = bool(tags_dict.get("allow_variations"))
        atributo_de_variacao = bool(tags_dict.get("variation_attribute"))
        valores = tuple(
            (str(v.get("id")), str(v.get("name")))
            for v in bruto.get("values") or []
            if isinstance(v, dict) and v.get("id") and v.get("name")
        )
        unidade = str(bruto.get("default_unit") or "").strip()
        return AtributoML(
            id=attr_id,
            nome=str(bruto.get("name") or ""),
            obrigatorio=obrigatorio,
            valores=valores,
            unidade_padrao=unidade,
            tipo_valor=str(bruto.get("value_type") or "").strip(),
            somente_leitura=somente_leitura,
            oculto=oculto,
            permite_variacao=permite_variacao,
            atributo_de_variacao=atributo_de_variacao,
        )


@dataclass(frozen=True)
class AtributoLigado:
    id: str
    valor: str
    valor_id: str | None = None
    chave: str = ""  # a chave nossa que deu origem à ligação

    def para_api(self) -> dict[str, str]:
        if self.valor_id:
            return {"id": self.id, "value_id": self.valor_id}
        return {"id": self.id, "value_name": self.valor}


def _valor_id(atributo: AtributoML, valor: str) -> str | None:
    alvo = _normalizar(valor)
    exato = next((vid for vid, nome in atributo.valores if _normalizar(nome) == alvo), None)
    if exato is not None:
        return exato
    alvo_neutro = _neutro(valor)
    por_neutro = next((vid for vid, nome in atributo.valores if _neutro(nome) == alvo_neutro), None)
    if por_neutro is not None:
        return por_neutro
    aliases = ALIASES_VALORES_ML.get(atributo.id)
    if aliases:
        canonico = aliases.get(alvo) or aliases.get(alvo_neutro)
        if canonico:
            return next((vid for vid, nome in atributo.valores if _normalizar(nome) == canonico), None)
    return None


def _formatar_valor(atributo: AtributoML, valor: str) -> str:
    """Normaliza quantidades inteiras ('1 unidade' → '1') e medidas com unidade ('250ml' → '250 mL')."""
    limpo = valor.strip()
    if atributo.id in IDS_QUANTIDADE_ML:
        numeros = re.findall(r"\d+", limpo)
        if numeros:
            return str(max(1, int(numeros[0])))
    casamento = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*([a-zA-Z]{1,4})?", limpo)
    if not casamento:
        return limpo
    numero = casamento.group(1).replace(",", ".")
    unidade_bruta = (casamento.group(2) or "").lower()
    if atributo.unidade_padrao:
        unidade = UNIDADES_CANONICAS.get(unidade_bruta, atributo.unidade_padrao)
        return f"{numero} {unidade}"
    if unidade_bruta in UNIDADES_CANONICAS and atributo.id in ("VOLUME_CAPACITY", "CAPACITY", "HEIGHT", "DIAMETER", "WEIGHT"):
        return f"{numero} {UNIDADES_CANONICAS[unidade_bruta]}"
    return limpo


def ligar_por_regra(confirmados: list[tuple[str, str]], da_categoria: list[AtributoML]
                    ) -> tuple[list[AtributoLigado], list[tuple[str, str]]]:
    """(ligados, sobras). Um atributo do Mercado Livre recebe no máximo um valor."""
    editaveis = [a for a in da_categoria if not a.somente_leitura]
    por_id = {a.id: a for a in editaveis}
    por_nome = {_normalizar(a.nome): a for a in editaveis if a.nome}
    ligados: dict[str, AtributoLigado] = {}
    sobras = []
    for chave, valor in confirmados:
        candidato = next((por_id[i] for i in SINONIMOS_ML.get(chave, ()) if i in por_id and i not in ligados), None)
        if candidato is None:
            chave_id = chave.strip().upper()
            if chave_id in por_id and chave_id not in ligados:
                candidato = por_id[chave_id]
        if candidato is None:
            candidato = por_nome.get(_normalizar(chave.replace("_", " ")))
            if candidato is not None and candidato.id in ligados:
                candidato = None
        if candidato is None:
            sobras.append((chave, valor))
            continue
        formatado = _formatar_valor(candidato, valor)
        ligados[candidato.id] = AtributoLigado(candidato.id, formatado, _valor_id(candidato, formatado), chave)
    return list(ligados.values()), sobras


def ligar_sugestoes_da_ia(sugestoes: list[dict[str, Any]], sobras: list[tuple[str, str]],
                          da_categoria: list[AtributoML], ja_ligados: list[AtributoLigado]) -> list[AtributoLigado]:
    """Aceita da IA só ligações para IDs que existem na categoria, ainda livres, com chave das sobras."""
    editaveis = [a for a in da_categoria if not a.somente_leitura]
    por_id = {a.id: a for a in editaveis}
    livres = {a.id for a in editaveis} - {l.id for l in ja_ligados}
    valores = dict(sobras)
    saida = []
    for sugestao in sugestoes if isinstance(sugestoes, list) else []:
        if not isinstance(sugestao, dict):
            continue
        chave, ml_id = str(sugestao.get("chave") or ""), str(sugestao.get("id_ml") or "")
        if chave in valores and ml_id in livres:
            formatado = _formatar_valor(por_id[ml_id], valores[chave])
            saida.append(AtributoLigado(ml_id, formatado, _valor_id(por_id[ml_id], formatado), chave))
            livres.discard(ml_id)
    return saida


def obrigatorios_faltando(da_categoria: list[AtributoML], ligados: list[AtributoLigado]) -> list[AtributoML]:
    preenchidos = {l.id for l in ligados}
    return [a for a in da_categoria if a.obrigatorio and not a.somente_leitura and not a.oculto and a.id not in preenchidos]


def chave_do_atributo_ml(atributo: AtributoML) -> str:
    """A chave nossa para um atributo do Mercado Livre: a nossa chave conhecida, ou o nome normalizado."""
    for chave, ids in SINONIMOS_ML.items():
        if atributo.id in ids:
            return chave
    return _normalizar(atributo.nome).replace(" ", "_") or atributo.id.lower()


def perguntas_dos_obrigatorios(faltando: list[AtributoML]) -> list[dict[str, str]]:
    """Obrigatórios da categoria que ficaram sem valor viram perguntas para o vendedor."""
    return [
        {"chave": chave_do_atributo_ml(a), "pergunta": f"{a.nome}: o Mercado Livre pede esse dado. Qual é?",
         "sugerir_foto": "etiqueta" if a.id in ("BRAND", "MODEL", "SIZE", "VOLTAGE") else "nenhuma"}
        for a in faltando
    ]


def mapa_de_chaves(ligados_por_chave: dict[str, str], faltando: list[AtributoML]) -> dict[str, str]:
    """chave nossa → id do Mercado Livre, juntando o que já foi ligado e os obrigatórios ainda sem valor."""
    mapa = dict(ligados_por_chave)
    for atributo in faltando:
        mapa.setdefault(chave_do_atributo_ml(atributo), atributo.id)
    return mapa


def ligar_confirmados(confirmados: list[tuple[str, str]], da_categoria: list[AtributoML],
                      mapa: dict[str, str]) -> list[AtributoLigado]:
    """Na confirmação: regra primeiro; o que sobrar usa o mapa guardado na leitura (sem chamar a IA de novo)."""
    ligados, sobras = ligar_por_regra(confirmados, da_categoria)
    por_id = {a.id: a for a in da_categoria if not a.somente_leitura}
    usados = {l.id for l in ligados}
    for chave, valor in sobras:
        ml_id = mapa.get(chave)
        if ml_id and ml_id in por_id and ml_id not in usados:
            formatado = _formatar_valor(por_id[ml_id], valor)
            ligados.append(AtributoLigado(ml_id, formatado, _valor_id(por_id[ml_id], formatado), chave))
            usados.add(ml_id)
    return ligados


def _unidades_do_kit(titulo: str, usados: dict[str, AtributoLigado]) -> int:
    for id_qtd in IDS_QUANTIDADE_ML:
        if id_qtd in usados:
            numeros = re.findall(r"\d+", usados[id_qtd].valor)
            if numeros:
                return max(1, int(numeros[0]))
    casamento = re.search(r"\b(?:kit|conjunto|jogo|pack)\s+(?:com\s+|de\s+)?(\d+)\b", _normalizar(titulo))
    if casamento:
        return max(1, int(casamento.group(1)))
    return 1


def _definir_ou_substituir(saida: list[AtributoLigado], usados: dict[str, AtributoLigado],
                           novo: AtributoLigado) -> None:
    if novo.id in usados:
        for idx, item in enumerate(saida):
            if item.id == novo.id:
                saida[idx] = novo
                break
    else:
        saida.append(novo)
    usados[novo.id] = novo


def _valor_canonico_por_id(atributo: AtributoML, valor_id: str) -> str:
    return next((nome for vid, nome in atributo.valores if vid == valor_id), "")


def _inferir_genero_do_titulo(atributo: AtributoML, titulo: str) -> AtributoLigado | None:
    aliases = ALIASES_VALORES_ML.get("GENDER", {})
    norm = _normalizar(titulo)
    if norm:
        palavras = norm.split()
        # Testa frases de 2 palavras antes de palavras isoladas (ex.: "unissex infantil" antes de "unissex")
        candidatos = [f"{palavras[i]} {palavras[i + 1]}" for i in range(len(palavras) - 1)] + palavras
        for termo in candidatos:
            canonico = aliases.get(termo)
            if canonico:
                vid = next((v for v, nome in atributo.valores if _normalizar(nome) == canonico), None)
                if vid is not None:
                    return AtributoLigado("GENDER", _valor_canonico_por_id(atributo, vid), vid)
    if atributo.obrigatorio:
        vid = _valor_id(atributo, "Sem gênero")
        if vid is not None:
            return AtributoLigado("GENDER", _valor_canonico_por_id(atributo, vid), vid)
    return None


def _extrair_tamanho_do_titulo(titulo: str) -> str | None:
    if not titulo:
        return None
    sem_acento = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode("ascii")
    achado = re.search(
        r"\b(?:tamanho|tam\.?|num(?:ero)?|n[o°º]\.?)\s*([0-9]{2}(?:[/\-][0-9]{2})?|PP|P|M|G|GG|XG|XXG|EG|U)\b",
        sem_acento,
        flags=re.IGNORECASE,
    )
    if not achado:
        return None
    bruto = achado.group(1).strip()
    return bruto.upper() if bruto.isalpha() else bruto


def completar_para_publicacao(ligados: list[AtributoLigado], da_categoria: list[AtributoML],
                              titulo: str = "") -> list[AtributoLigado]:
    """Preenche na hora de publicar o que o título já diz (valores fechados e medidas) e os atributos
    estruturais do Mercado Livre (marca, fabricante, modelo, formato de venda, unidades por kit e motivo
    de GTIN vazio) que elevam a pontuação de qualidade da ficha técnica."""
    por_id = {a.id: a for a in da_categoria}
    saida: list[AtributoLigado] = []
    for item in ligados:
        if item.id in IDS_SOMENTE_LEITURA_ML:
            continue
        atributo = por_id.get(item.id)
        if atributo is not None and atributo.somente_leitura:
            continue
        if atributo is not None and item.valor_id is None and atributo.valores:
            vid = _valor_id(atributo, item.valor)
            if vid is not None:
                saida.append(AtributoLigado(item.id, item.valor, vid, item.chave))
                continue
            if atributo.tipo_valor == "list":
                if atributo.id == "GENDER" and atributo.obrigatorio:
                    vid_padrao = _valor_id(atributo, "Sem gênero")
                    if vid_padrao is not None:
                        saida.append(
                            AtributoLigado(item.id, _valor_canonico_por_id(atributo, vid_padrao), vid_padrao, item.chave)
                        )
                continue
        saida.append(item)

    usados = {l.id: l for l in saida}
    palavras_titulo = set(_neutro(titulo).split())

    for atributo in da_categoria:
        if atributo.somente_leitura or atributo.oculto:
            continue
        if atributo.id in usados or not atributo.valores or not palavras_titulo:
            continue
        if atributo.id in ("SALE_FORMAT", "IS_SET", "EMPTY_GTIN_REASON", "SIZE_GRID_ID", "SIZE_GRID_ROW_ID"):
            continue
        for vid, nome in atributo.valores:
            termos = _neutro(nome).split()
            if termos and all(t in palavras_titulo for t in termos):
                ligado = AtributoLigado(atributo.id, nome, vid)
                saida.append(ligado)
                usados[atributo.id] = ligado
                break

    if "GENDER" in por_id and "GENDER" not in usados and not por_id["GENDER"].somente_leitura:
        genero_inferido = _inferir_genero_do_titulo(por_id["GENDER"], titulo)
        if genero_inferido is not None:
            saida.append(genero_inferido)
            usados["GENDER"] = genero_inferido

    if "SIZE" in por_id and "SIZE" not in usados and not por_id["SIZE"].somente_leitura:
        tamanho_titulo = _extrair_tamanho_do_titulo(titulo)
        if tamanho_titulo:
            ligado = AtributoLigado("SIZE", tamanho_titulo, _valor_id(por_id["SIZE"], tamanho_titulo))
            saida.append(ligado)
            usados["SIZE"] = ligado

    for id_cap in ("VOLUME_CAPACITY", "CAPACITY"):
        if id_cap in por_id and id_cap not in usados and titulo:
            achado = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(ml|l|cc)\b", titulo, flags=re.IGNORECASE)
            if achado:
                valor_cap = _formatar_valor(por_id[id_cap], f"{achado.group(1)}{achado.group(2)}")
                ligado = AtributoLigado(id_cap, valor_cap, _valor_id(por_id[id_cap], valor_cap))
                saida.append(ligado)
                usados[id_cap] = ligado

    marca = usados["BRAND"].valor if "BRAND" in usados else MARCA_GENERICA_ML
    if "BRAND" in por_id and "BRAND" not in usados:
        ligado = AtributoLigado("BRAND", MARCA_GENERICA_ML, _valor_id(por_id["BRAND"], MARCA_GENERICA_ML))
        saida.append(ligado)
        usados["BRAND"] = ligado

    if "MANUFACTURER" in por_id and por_id["MANUFACTURER"].obrigatorio and "MANUFACTURER" not in usados:
        ligado = AtributoLigado("MANUFACTURER", marca, _valor_id(por_id["MANUFACTURER"], marca))
        saida.append(ligado)
        usados["MANUFACTURER"] = ligado

    if "MODEL" in por_id and por_id["MODEL"].obrigatorio and "MODEL" not in usados:
        modelo = (titulo.split()[0] if titulo.strip() else "") or MODELO_PADRAO_ML
        ligado = AtributoLigado("MODEL", modelo, _valor_id(por_id["MODEL"], modelo))
        saida.append(ligado)
        usados["MODEL"] = ligado

    unidades = _unidades_do_kit(titulo, usados)
    # O Mercado Livre só aceita SALE_FORMAT="Kit" quando UNITS_PER_PACK >= 2; para 1 unidade exige "Unidade" e "1".
    eh_kit = unidades >= 2

    if "SALE_FORMAT" in por_id:
        formato = "Kit" if eh_kit else "Unidade"
        chave_fmt = usados["SALE_FORMAT"].chave if "SALE_FORMAT" in usados else ""
        _definir_ou_substituir(
            saida,
            usados,
            AtributoLigado("SALE_FORMAT", formato, _valor_id(por_id["SALE_FORMAT"], formato), chave_fmt),
        )

    for id_qtd in IDS_QUANTIDADE_ML:
        if id_qtd in por_id and (id_qtd == "UNITS_PER_PACK" or id_qtd in usados):
            valor_un = str(unidades)
            chave_qtd = usados[id_qtd].chave if id_qtd in usados else ""
            _definir_ou_substituir(
                saida,
                usados,
                AtributoLigado(id_qtd, valor_un, _valor_id(por_id[id_qtd], valor_un), chave_qtd),
            )

    if "IS_SET" in por_id and "IS_SET" not in usados:
        valor_set = "Sim" if eh_kit else "Não"
        ligado = AtributoLigado("IS_SET", valor_set, _valor_id(por_id["IS_SET"], valor_set))
        saida.append(ligado)
        usados["IS_SET"] = ligado

    if "EMPTY_GTIN_REASON" in por_id and "EMPTY_GTIN_REASON" not in usados and "GTIN" not in usados:
        vid = _valor_id(por_id["EMPTY_GTIN_REASON"], MOTIVO_SEM_GTIN_ML)
        if vid is not None or not por_id["EMPTY_GTIN_REASON"].valores:
            ligado = AtributoLigado("EMPTY_GTIN_REASON", MOTIVO_SEM_GTIN_ML, vid)
            saida.append(ligado)
            usados["EMPTY_GTIN_REASON"] = ligado

    return saida


TIPOS_DO_ML = {"boolean": TipoDeCampo.BOOLEANO, "number": TipoDeCampo.NUMERO, "number_unit": TipoDeCampo.NUMERO,
               "list": TipoDeCampo.LISTA, "string": TipoDeCampo.TEXTO}


def _tipo_do_campo(atributo: AtributoML) -> TipoDeCampo:
    if atributo.tipo_valor in TIPOS_DO_ML:
        return TIPOS_DO_ML[atributo.tipo_valor]
    # Cache antigo (sem value_type) ou tipo que não conhecemos: deduz pelos valores e pela unidade
    return TipoDeCampo.LISTA if atributo.valores else TipoDeCampo.NUMERO if atributo.unidade_padrao else TipoDeCampo.TEXTO


def esquema_do_ml(categoria_id: str, categoria_nome: str, atributos: list[AtributoML]) -> EsquemaDoCanal:
    """Os atributos de uma categoria do Mercado Livre no modelo genérico de campos, na mesma ordem. Os valores
    do ML ficam no campo em qualquer tipo (servem à conversão, como "Sim" e "Não" do booleano)."""
    campos = tuple(
        CampoDoCanal(
            canal=CANAL_ML, id=a.id, nome=a.nome, obrigatorio=a.obrigatorio, tipo=_tipo_do_campo(a),
            valores=a.valores, unidade=a.unidade_padrao, chave=chave_do_atributo_ml(a),
        )
        for a in atributos
        if not a.somente_leitura and not a.oculto
    )
    return EsquemaDoCanal(canal=CANAL_ML, categoria_id=categoria_id, categoria_nome=categoria_nome, campos=campos)
