"""
Domínio · IA · Leitura do produto (o que a IA viu nas fotos) e a confirmação do vendedor

A IA devolve um JSON com esquema fechado; aqui ele é conferido e as regras de não inventar
valem mesmo se a IA errar:
    marca só com logo ou etiqueta (origem foto ou etiqueta); tamanho e voltagem só com etiqueta;
    "deducao" nunca sai com confiança alta; sem valor, a origem é "desconhecido" e vira pergunta;
    produto não reconhecido não carrega atributos; caixas fora de 0 a 1000 são descartadas.
"""

import re
from dataclasses import asdict, dataclass, field, replace
from enum import StrEnum
from typing import Any


class OrigemAtributo(StrEnum):
    FOTO = "foto"
    ETIQUETA = "etiqueta"
    DEDUCAO = "deducao"
    DESCONHECIDO = "desconhecido"


class Confianca(StrEnum):
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


class CondicaoProduto(StrEnum):
    NOVO = "novo"
    USADO = "usado"
    RECONDICIONADO = "recondicionado"
    DESCONHECIDO = "desconhecido"


class SugestaoDeFoto(StrEnum):
    ETIQUETA = "etiqueta"
    VERSO = "verso"
    DETALHE = "detalhe"
    NENHUMA = "nenhuma"


class Cartao(StrEnum):
    """Como o atributo aparece no passo Confirmar."""

    VIU = "a_ia_viu"  # preenchido, selo "A IA viu"
    CONFERE = "confere"  # preenchido em destaque, "Confere?" com sim e não
    PERGUNTA = "pergunta"  # campo vazio com a pergunta e o botão de mandar foto


# As mesmas categorias do front (frontend/src/domain/content/listingContent.js)
CATEGORIAS: tuple[str, ...] = (
    "moda", "calcados", "acessorios", "casa", "cozinha", "eletronicos",
    "livros", "esporte", "beleza", "brinquedos", "outros",
)
CHAVES_COMUNS: tuple[str, ...] = (
    "marca", "modelo", "cor", "material", "textura", "tamanho", "voltagem", "quantidade",
    "dimensoes", "capacidade", "genero", "estampa", "acabamento", "potencia", "compatibilidade",
)
CHAVES_SO_COM_ETIQUETA = frozenset({"tamanho", "voltagem"})
CHAVES_SO_COM_LOGO_OU_ETIQUETA = frozenset({"marca"})

MAX_PRODUTO = 80
MAX_TERMOS_BUSCA = 4
MAX_ATRIBUTOS = 20
MAX_PALAVRAS_EVIDENCIA = 12
MAX_SINAIS = 4
MAX_DEFEITOS = 5
MAX_TEXTO_LEGIVEL = 8
MAX_PERGUNTAS = 8
MAX_VALOR = 120
MAX_TEXTO_CURTO = 160


def _texto(valor: Any, limite: int = MAX_TEXTO_CURTO) -> str:
    if not isinstance(valor, str):
        return ""
    return re.sub(r"\s+", " ", valor).strip()[:limite].strip()


def _enum(tipo, valor: Any, padrao):
    try:
        return tipo(str(valor).strip().lower())
    except ValueError:
        return padrao


def _lista_de_textos(valores: Any, maximo: int, limite: int = MAX_TEXTO_CURTO) -> list[str]:
    if not isinstance(valores, (list, tuple)):
        return []
    vistos, saida = set(), []
    for valor in valores:
        texto = _texto(valor, limite)
        if texto and texto.lower() not in vistos:
            vistos.add(texto.lower())
            saida.append(texto)
        if len(saida) == maximo:
            break
    return saida


def normalizar_chave(chave: Any) -> str:
    texto = _texto(chave, 40).lower()
    texto = re.sub(r"[^a-z0-9à-ú]+", "_", texto).strip("_")
    return texto


@dataclass(frozen=True)
class Atributo:
    chave: str
    valor: str
    origem: OrigemAtributo
    evidencia: str
    confianca: Confianca

    @property
    def cartao(self) -> Cartao:
        if not self.valor or self.origem is OrigemAtributo.DESCONHECIDO or self.confianca is Confianca.BAIXA:
            return Cartao.PERGUNTA
        if self.origem in (OrigemAtributo.FOTO, OrigemAtributo.ETIQUETA) and self.confianca is Confianca.ALTA:
            return Cartao.VIU
        return Cartao.CONFERE


@dataclass(frozen=True)
class Pergunta:
    chave: str
    pergunta: str
    sugerir_foto: SugestaoDeFoto


@dataclass(frozen=True)
class EtiquetaIlegivel:
    foto: int
    caixa: tuple[int, int, int, int]


@dataclass(frozen=True)
class Condicao:
    valor: CondicaoProduto = CondicaoProduto.DESCONHECIDO
    sinais: tuple[str, ...] = ()
    confianca: Confianca = Confianca.BAIXA


@dataclass(frozen=True)
class Leitura:
    reconhecido: bool
    motivo_nao_reconhecido: str = ""
    produto: str = ""
    categoria: str = "outros"
    termos_busca: tuple[str, ...] = ()
    atributos: tuple[Atributo, ...] = ()
    condicao: Condicao = field(default_factory=Condicao)
    defeitos_visiveis: tuple[str, ...] = ()
    texto_legivel: tuple[str, ...] = ()
    etiqueta_ilegivel: tuple[EtiquetaIlegivel, ...] = ()
    perguntas: tuple[Pergunta, ...] = ()

    def atributo(self, chave: str) -> Atributo | None:
        return next((a for a in self.atributos if a.chave == chave), None)

    def para_dict(self) -> dict[str, Any]:
        dados = asdict(self)
        for atributo, original in zip(dados["atributos"], self.atributos, strict=True):
            atributo["cartao"] = original.cartao.value
        return dados


# Artigo e nome com acento das chaves comuns, para a pergunta padrão soar natural
NOMES_DE_ATRIBUTO: dict[str, tuple[str, str]] = {
    "marca": ("a", "marca"), "modelo": ("o", "modelo"), "cor": ("a", "cor"), "material": ("o", "material"),
    "textura": ("a", "textura"), "tamanho": ("o", "tamanho"), "voltagem": ("a", "voltagem"),
    "quantidade": ("a", "quantidade"), "dimensoes": ("as", "dimensões"), "capacidade": ("a", "capacidade"),
    "genero": ("o", "gênero"), "estampa": ("a", "estampa"), "acabamento": ("o", "acabamento"),
    "potencia": ("a", "potência"), "compatibilidade": ("a", "compatibilidade"),
}


def pergunta_padrao(chave: str) -> str:
    artigo, nome = NOMES_DE_ATRIBUTO.get(chave, ("", chave.replace("_", " ")))
    if not artigo:
        return f"Qual é o valor de {nome} do produto?"
    if artigo.endswith("s"):
        return f"Quais são {artigo} {nome} do produto?"
    return f"Qual é {artigo} {nome} do produto?"


def _sugestao_padrao(chave: str) -> SugestaoDeFoto:
    if chave in CHAVES_SO_COM_ETIQUETA or chave in CHAVES_SO_COM_LOGO_OU_ETIQUETA or chave == "modelo":
        return SugestaoDeFoto.ETIQUETA
    return SugestaoDeFoto.DETALHE


def _atributo(bruto: dict[str, Any]) -> Atributo | None:
    chave = normalizar_chave(bruto.get("chave"))
    if not chave:
        return None
    valor = _texto(bruto.get("valor"), MAX_VALOR)
    origem = _enum(OrigemAtributo, bruto.get("origem"), OrigemAtributo.DESCONHECIDO)
    confianca = _enum(Confianca, bruto.get("confianca"), Confianca.BAIXA)
    evidencia = " ".join(_texto(bruto.get("evidencia")).split()[:MAX_PALAVRAS_EVIDENCIA])

    # Nunca inventar: marca só com logo ou etiqueta; tamanho e voltagem só com etiqueta
    if chave in CHAVES_SO_COM_LOGO_OU_ETIQUETA and origem not in (OrigemAtributo.FOTO, OrigemAtributo.ETIQUETA):
        valor = ""
    if chave in CHAVES_SO_COM_ETIQUETA and origem is not OrigemAtributo.ETIQUETA:
        valor = ""
    if origem is OrigemAtributo.DEDUCAO and confianca is Confianca.ALTA:
        confianca = Confianca.MEDIA
    if not valor or origem is OrigemAtributo.DESCONHECIDO:
        valor, origem, confianca = "", OrigemAtributo.DESCONHECIDO, Confianca.BAIXA
    return Atributo(chave, valor, origem, evidencia, confianca)


def _caixa(bruto: Any) -> tuple[int, int, int, int] | None:
    if not isinstance(bruto, (list, tuple)) or len(bruto) != 4:
        return None
    try:
        x0, y0, x1, y1 = (int(round(float(v))) for v in bruto)
    except (TypeError, ValueError):
        return None
    if not all(0 <= v <= 1000 for v in (x0, y0, x1, y1)) or x0 >= x1 or y0 >= y1:
        return None
    return x0, y0, x1, y1


def _perguntas(brutas: Any, atributos: tuple[Atributo, ...]) -> tuple[Pergunta, ...]:
    perguntas: dict[str, Pergunta] = {}
    for bruta in brutas if isinstance(brutas, (list, tuple)) else []:
        if not isinstance(bruta, dict):
            continue
        chave = normalizar_chave(bruta.get("chave"))
        texto = _texto(bruta.get("pergunta"))
        if chave and texto and chave not in perguntas:
            perguntas[chave] = Pergunta(chave, texto, _enum(SugestaoDeFoto, bruta.get("sugerir_foto"),
                                                            SugestaoDeFoto.NENHUMA))
    # Todo atributo sem valor vira pergunta; atributo já respondido pela foto não precisa de pergunta
    for atributo in atributos:
        if atributo.cartao is Cartao.PERGUNTA and atributo.chave not in perguntas:
            perguntas[atributo.chave] = Pergunta(atributo.chave, pergunta_padrao(atributo.chave),
                                                 _sugestao_padrao(atributo.chave))
    com_valor = {a.chave for a in atributos if a.cartao is not Cartao.PERGUNTA}
    return tuple(p for chave, p in perguntas.items() if chave not in com_valor)[:MAX_PERGUNTAS]


def normalizar_leitura(bruto: dict[str, Any], quantidade_fotos: int) -> Leitura:
    """Do JSON da IA (ou do banco) para uma Leitura que segue as regras."""
    if not isinstance(bruto, dict):
        bruto = {}
    reconhecido = bool(bruto.get("reconhecido"))

    atributos: dict[str, Atributo] = {}
    for item in bruto.get("atributos") or []:
        if isinstance(item, dict) and (atributo := _atributo(item)) and atributo.chave not in atributos:
            atributos[atributo.chave] = atributo
        if len(atributos) == MAX_ATRIBUTOS:
            break

    condicao_bruta = bruto.get("condicao") if isinstance(bruto.get("condicao"), dict) else {}
    condicao = Condicao(
        valor=_enum(CondicaoProduto, condicao_bruta.get("valor"), CondicaoProduto.DESCONHECIDO),
        sinais=tuple(_lista_de_textos(condicao_bruta.get("sinais"), MAX_SINAIS)),
        confianca=_enum(Confianca, condicao_bruta.get("confianca"), Confianca.BAIXA),
    )

    etiquetas = []
    for item in bruto.get("etiqueta_ilegivel") or []:
        if not isinstance(item, dict):
            continue
        try:
            foto = int(item.get("foto"))
        except (TypeError, ValueError):
            continue
        caixa = _caixa(item.get("caixa"))
        if caixa is not None and 0 <= foto < quantidade_fotos:
            etiquetas.append(EtiquetaIlegivel(foto, caixa))

    categoria = _texto(bruto.get("categoria"), 20).lower()
    leitura = Leitura(
        reconhecido=reconhecido,
        motivo_nao_reconhecido="" if reconhecido else _texto(bruto.get("motivo_nao_reconhecido")),
        produto=_texto(bruto.get("produto"), MAX_PRODUTO),
        categoria=categoria if categoria in CATEGORIAS else "outros",
        termos_busca=tuple(_lista_de_textos(bruto.get("termos_busca"), MAX_TERMOS_BUSCA, 60)),
        atributos=tuple(atributos.values()),
        condicao=condicao,
        defeitos_visiveis=tuple(_lista_de_textos(bruto.get("defeitos_visiveis"), MAX_DEFEITOS)),
        texto_legivel=tuple(_lista_de_textos(bruto.get("texto_legivel"), MAX_TEXTO_LEGIVEL, 80)),
        etiqueta_ilegivel=tuple(etiquetas),
    )
    if not reconhecido:
        # Produto não reconhecido: sem chutar atributos (os campos manuais abrem na tela)
        leitura = replace(leitura, atributos=(), etiqueta_ilegivel=(), termos_busca=())
    return replace(leitura, perguntas=_perguntas(bruto.get("perguntas"), leitura.atributos))


def juntar_leitura_parcial(leitura: Leitura, bruto: dict[str, Any], origem: OrigemAtributo) -> Leitura:
    """Junta a releitura de uma etiqueta ou de uma foto extra: valor novo com evidência ganha do vazio
    e da dedução; valor que a IA já viu com confiança alta só muda se a nova leitura também for alta."""
    parcial = normalizar_leitura({"reconhecido": True, **bruto}, quantidade_fotos=0)
    atributos = {a.chave: a for a in leitura.atributos}
    for novo in parcial.atributos:
        if novo.cartao is Cartao.PERGUNTA:
            continue
        novo = replace(novo, origem=origem if novo.origem is not OrigemAtributo.DEDUCAO else novo.origem)
        atual = atributos.get(novo.chave)
        if atual is None or atual.cartao is not Cartao.VIU or novo.confianca is Confianca.ALTA:
            atributos[novo.chave] = novo
    texto = list(leitura.texto_legivel)
    for item in parcial.texto_legivel:
        if item.lower() not in {t.lower() for t in texto}:
            texto.append(item)
    defeitos = list(leitura.defeitos_visiveis)
    for item in parcial.defeitos_visiveis:
        if item.lower() not in {d.lower() for d in defeitos} and len(defeitos) < MAX_DEFEITOS:
            defeitos.append(item)
    juntos = tuple(atributos.values())[:MAX_ATRIBUTOS]
    perguntas = [{"chave": p.chave, "pergunta": p.pergunta, "sugerir_foto": p.sugerir_foto.value}
                 for p in leitura.perguntas]
    return replace(
        leitura,
        reconhecido=leitura.reconhecido or parcial.reconhecido,
        atributos=juntos,
        texto_legivel=tuple(texto[: MAX_TEXTO_LEGIVEL * 2]),
        defeitos_visiveis=tuple(defeitos),
        etiqueta_ilegivel=(),
        perguntas=_perguntas(perguntas, juntos),
    )


@dataclass(frozen=True)
class AtributoConfirmado:
    chave: str
    valor: str


@dataclass(frozen=True)
class Confirmacao:
    """O que o vendedor confirmou: só isso entra como fato na descrição."""

    produto: str
    categoria: str
    condicao: CondicaoProduto
    atributos: tuple[AtributoConfirmado, ...]
    defeitos: tuple[str, ...]

    def para_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalizar_confirmacao(bruto: dict[str, Any], leitura: Leitura | None) -> Confirmacao:
    """Do corpo do pedido (ou do banco) para uma Confirmacao limpa."""
    if not isinstance(bruto, dict):
        bruto = {}
    atributos: dict[str, AtributoConfirmado] = {}
    for item in bruto.get("atributos") or []:
        if not isinstance(item, dict):
            continue
        chave = normalizar_chave(item.get("chave"))
        valor = _texto(item.get("valor"), MAX_VALOR)
        if chave and valor and chave not in atributos:
            atributos[chave] = AtributoConfirmado(chave, valor)
        if len(atributos) == MAX_ATRIBUTOS * 2:
            break
    categoria = _texto(bruto.get("categoria"), 20).lower()
    if categoria not in CATEGORIAS:
        categoria = leitura.categoria if leitura else "outros"
    condicao = _enum(CondicaoProduto, bruto.get("condicao"),
                     leitura.condicao.valor if leitura else CondicaoProduto.DESCONHECIDO)
    return Confirmacao(
        produto=_texto(bruto.get("produto"), MAX_PRODUTO) or (leitura.produto if leitura else ""),
        categoria=categoria,
        condicao=condicao,
        atributos=tuple(atributos.values()),
        defeitos=tuple(_lista_de_textos(bruto.get("defeitos"), MAX_DEFEITOS)),
    )
