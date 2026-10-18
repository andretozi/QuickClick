"""
Domínio · IA · Regra de escrita do título e da descrição

Português do Brasil, sem emojis, sem barra, sem travessão, sem meia risca e sem hífen como
pontuação. Hífen dentro de nome técnico (USB-C, Wi-Fi, NF-e) pode. No máximo uma lista de até
5 especificações "Rótulo: valor", uma por linha, sem marcador.

O validador acha os trechos errados (para a correção pela IA rápida); a limpeza determinística
é a última reserva, quando a correção também falha.
"""

import re
from dataclasses import dataclass

TITULO_MAX = 60
DESCRICAO_MAX = 2000
ESPECIFICACOES_MAX = 5

_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF\U00002300-\U000023FF"
    "\U0000FE0F\U0000200D\U000020E3\U0001F1E6-\U0001F1FF]"
)
_TRAVESSOES = re.compile("[‒–—―−]")  # figura, meia risca, travessão, barra horizontal, menos
_HIFEN_PONTUACAO = re.compile(r"(?<![0-9A-Za-zÀ-ÿ])-|-(?![0-9A-Za-zÀ-ÿ])")
_MARCADOR = re.compile(r"^\s*(?:[-*•·▪►✓✔○●]|\d{1,2}[.)])\s+")
_ESPECIFICACAO = re.compile(r"^[^:\n]{1,40}:\s+\S")


@dataclass(frozen=True)
class Problema:
    tipo: str  # emoji | barra | travessao | hifen | marcador | especificacoes | tamanho
    trecho: str


def _trecho(texto: str, inicio: int, fim: int) -> str:
    return texto[max(0, inicio - 20): fim + 20].strip()


def problemas_de_escrita(texto: str, limite: int | None = None) -> list[Problema]:
    problemas: list[Problema] = []
    for tipo, padrao in (("emoji", _EMOJI), ("travessao", _TRAVESSOES), ("hifen", _HIFEN_PONTUACAO)):
        for achado in padrao.finditer(texto):
            problemas.append(Problema(tipo, _trecho(texto, achado.start(), achado.end())))
    for indice in (i for i, c in enumerate(texto) if c == "/"):
        problemas.append(Problema("barra", _trecho(texto, indice, indice + 1)))
    linhas = texto.splitlines()
    for linha in linhas:
        if _MARCADOR.match(linha):
            problemas.append(Problema("marcador", linha.strip()[:60]))
    especificacoes = [linha for linha in linhas if _ESPECIFICACAO.match(linha.strip())]
    if len(especificacoes) > ESPECIFICACOES_MAX:
        problemas.append(Problema("especificacoes", f"{len(especificacoes)} linhas de especificação"))
    if limite is not None and len(texto) > limite:
        problemas.append(Problema("tamanho", f"{len(texto)} caracteres"))
    return problemas


def limpar_escrita(texto: str) -> str:
    """Conserta sem IA: tira emojis e marcadores, troca barra por "ou" e traço de pontuação por vírgula."""
    texto = _EMOJI.sub("", texto)
    linhas = [_MARCADOR.sub("", linha) for linha in texto.splitlines()]
    texto = "\n".join(linhas)
    texto = re.sub(r"\s*/\s*", " ou ", texto)
    texto = _TRAVESSOES.sub(",", texto)
    texto = _HIFEN_PONTUACAO.sub(",", texto)
    texto = re.sub(r"\s*,\s*,+", ",", texto)  # vírgulas repetidas
    texto = re.sub(r"(^|\n)\s*,\s*", r"\1", texto)  # vírgula no começo da linha
    texto = re.sub(r"\s+,", ",", texto)
    texto = re.sub(r",(?=\S)", ", ", texto)
    texto = re.sub(r"[ \t]{2,}", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    linhas = [linha.strip() for linha in texto.splitlines()]
    especificacoes = 0
    saida = []
    for linha in linhas:
        if _ESPECIFICACAO.match(linha):
            especificacoes += 1
            if especificacoes > ESPECIFICACOES_MAX:
                continue
        saida.append(linha)
    return "\n".join(saida).strip()


def cortar_titulo(titulo: str, limite: int = TITULO_MAX) -> str:
    """Título acima do limite é cortado na última palavra inteira."""
    titulo = re.sub(r"\s+", " ", titulo).strip()
    if len(titulo) <= limite:
        return titulo
    corte = titulo[: limite + 1]
    espaco = corte.rfind(" ")
    titulo = corte[:espaco] if espaco > 0 else titulo[:limite]
    return titulo.rstrip(" ,.;:")


def titulo_valido(titulo: str) -> str:
    """Título limpo pela regra de escrita e dentro de 60 caracteres."""
    return cortar_titulo(limpar_escrita(titulo).replace("\n", " "))
