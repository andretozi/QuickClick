"""
Domínio · IA · Ligar os atributos lidos aos atributos de uma categoria do Mercado Livre

Primeiro por regra (IDs conhecidos, nome e sinônimos); só as sobras vão para a IA rápida.
Obrigatórios da categoria que ficaram sem valor viram perguntas para o vendedor.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

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

    @staticmethod
    def de_api(bruto: dict[str, Any]) -> "AtributoML":
        tags = bruto.get("tags") or {}
        obrigatorio = bool(tags.get("required") or tags.get("catalog_required")) if isinstance(tags, dict) else False
        valores = tuple(
            (str(v.get("id")), str(v.get("name")))
            for v in bruto.get("values") or []
            if isinstance(v, dict) and v.get("id") and v.get("name")
        )
        unidade = str(bruto.get("default_unit") or "").strip()
        return AtributoML(id=str(bruto.get("id")), nome=str(bruto.get("name") or ""), obrigatorio=obrigatorio,
                          valores=valores, unidade_padrao=unidade)


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
    return next((vid for vid, nome in atributo.valores if _neutro(nome) == alvo_neutro), None)


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
    por_id = {a.id: a for a in da_categoria}
    por_nome = {_normalizar(a.nome): a for a in da_categoria if a.nome}
    ligados: dict[str, AtributoLigado] = {}
    sobras = []
    for chave, valor in confirmados:
        candidato = next((por_id[i] for i in SINONIMOS_ML.get(chave, ()) if i in por_id and i not in ligados), None)
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
    por_id = {a.id: a for a in da_categoria}
    livres = {a.id for a in da_categoria} - {l.id for l in ja_ligados}
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
    return [a for a in da_categoria if a.obrigatorio and a.id not in preenchidos]


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
    por_id = {a.id: a for a in da_categoria}
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


def completar_para_publicacao(ligados: list[AtributoLigado], da_categoria: list[AtributoML],
                              titulo: str = "") -> list[AtributoLigado]:
    """Preenche na hora de publicar o que o título já diz (valores fechados e medidas) e os atributos
    estruturais do Mercado Livre (marca, fabricante, modelo, formato de venda, unidades por kit e motivo
    de GTIN vazio) que elevam a pontuação de qualidade da ficha técnica."""
    saida = list(ligados)
    por_id = {a.id: a for a in da_categoria}
    usados = {l.id: l for l in saida}
    palavras_titulo = set(_neutro(titulo).split())

    for atributo in da_categoria:
        if atributo.id in usados or not atributo.valores or not palavras_titulo:
            continue
        if atributo.id in ("SALE_FORMAT", "IS_SET", "EMPTY_GTIN_REASON"):
            continue
        for vid, nome in atributo.valores:
            termos = _neutro(nome).split()
            if termos and all(t in palavras_titulo for t in termos):
                ligado = AtributoLigado(atributo.id, nome, vid)
                saida.append(ligado)
                usados[atributo.id] = ligado
                break

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
