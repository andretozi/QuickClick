"""
Domínio · Canais · Ficha do produto (o que sabemos dele, igual para todos os canais)

Junta a leitura da IA e a confirmação do vendedor sem inventar nada: o que o vendedor confirmou
entra como confirmado; o que só a IA leu entra com a origem e a confiança da leitura; atributo que
a IA não viu fica de fora. Cada canal depois traduz a ficha para os campos do próprio esquema.
"""

from dataclasses import dataclass, field

from backend.domain.ia.leitura import Atributo, Confianca, Confirmacao, CondicaoProduto, Leitura, OrigemAtributo

TAMANHOS_GTIN = (8, 12, 13, 14)  # EAN-8, UPC-A, EAN-13 e GTIN-14


@dataclass(frozen=True)
class ValorDaFicha:
    chave: str
    valor: str
    origem: OrigemAtributo  # do que a IA leu; DESCONHECIDO quando a IA não leu esse valor
    confianca: Confianca  # idem; BAIXA quando a IA não leu esse valor
    confirmado: bool


@dataclass(frozen=True)
class Identificacao:
    gtin: str | None = None
    sku: str | None = None


@dataclass(frozen=True)
class Embalagem:
    peso_g: int | None = None
    comprimento_cm: float | None = None
    largura_cm: float | None = None
    altura_cm: float | None = None


@dataclass(frozen=True)
class FichaDoProduto:
    produto: str = ""
    categoria: str = "outros"  # categoria nossa (CATEGORIAS de leitura.py)
    condicao: CondicaoProduto = CondicaoProduto.DESCONHECIDO
    valores: tuple[ValorDaFicha, ...] = ()
    identificacao: Identificacao = field(default_factory=Identificacao)
    embalagem: Embalagem = field(default_factory=Embalagem)


def _comparavel(valor: str) -> str:
    return " ".join(valor.split()).casefold()


def montar_ficha(leitura: Leitura, confirmacao: Confirmacao | None = None) -> FichaDoProduto:
    """Confirmados primeiro (na ordem da confirmação), depois o que só a IA leu (na ordem da leitura)."""
    lidos: dict[str, Atributo] = {}
    for atributo in leitura.atributos:
        if atributo.valor:
            lidos.setdefault(atributo.chave, atributo)

    valores: dict[str, ValorDaFicha] = {}
    for confirmado in confirmacao.atributos if confirmacao is not None else ():
        if confirmado.chave in valores:
            continue
        lido = lidos.get(confirmado.chave)
        # Vendedor mudou ou acrescentou o valor: não é mais o que a IA leu
        igual = lido is not None and _comparavel(lido.valor) == _comparavel(confirmado.valor)
        valores[confirmado.chave] = ValorDaFicha(
            confirmado.chave, confirmado.valor,
            lido.origem if igual else OrigemAtributo.DESCONHECIDO,
            lido.confianca if igual else Confianca.BAIXA,
            confirmado=True,
        )
    for chave, lido in lidos.items():
        valores.setdefault(chave, ValorDaFicha(chave, lido.valor, lido.origem, lido.confianca, confirmado=False))

    if confirmacao is not None:
        produto, categoria, condicao = confirmacao.produto, confirmacao.categoria, confirmacao.condicao
    else:
        produto, categoria, condicao = leitura.produto, leitura.categoria, leitura.condicao.valor
    return FichaDoProduto(produto=produto, categoria=categoria, condicao=condicao, valores=tuple(valores.values()))


def gtin_valido(codigo: str) -> bool:
    """GTIN de 8, 12, 13 ou 14 dígitos com o dígito verificador GS1 certo (espaços só nas pontas)."""
    if not isinstance(codigo, str):
        return False
    digitos = codigo.strip()
    if len(digitos) not in TAMANHOS_GTIN or not (digitos.isascii() and digitos.isdigit()) or set(digitos) == {"0"}:
        return False
    corpo = reversed(digitos[:-1])
    soma = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(corpo))
    return (10 - soma % 10) % 10 == int(digitos[-1])
