"""
Domínio · IA · Limites e qualidade das fotos

O servidor não guarda fotos no MVP: elas chegam na requisição, são conferidas e usadas em
memória, e somem quando a leitura termina. A qualidade é medida de graça (Python) e só
avisa: foto escura, tremida ou pequena nunca bloqueia a análise.
"""

from dataclasses import dataclass
from enum import StrEnum

MAX_FOTOS_POR_ANALISE = 6
MAX_BYTES_POR_FOTO = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000  # 40 megapixels (Image.MAX_IMAGE_PIXELS)
FORMATOS_ACEITOS = frozenset({"JPEG", "PNG", "WEBP", "HEIF"})

LADO_MAIOR_LEITURA = 1568  # versão de leitura, JPEG qualidade 90
QUALIDADE_JPEG_LEITURA = 90
LADO_MAIOR_RECORTE_ETIQUETA = 2576  # resolução total só no recorte da etiqueta
MAX_FOTOS_NA_LEITURA = 4

LADO_MENOR_MINIMO = 500  # abaixo disso: "pequena"
BRILHO_MINIMO = 55  # média de 0 a 255; abaixo disso: "escura"
NITIDEZ_MINIMA = 40.0  # variância das bordas (lado maior 512, sem a moldura do filtro)
BORDA_FORTE_MINIMA = 60  # percentil 99,9 das bordas: foto nítida com fundo liso ainda tem contorno forte


class QualidadeFoto(StrEnum):
    OK = "ok"
    ESCURA = "escura"
    TREMIDA = "tremida"
    PEQUENA = "pequena"


@dataclass(frozen=True)
class MedidaDaFoto:
    largura: int
    altura: int
    brilho_medio: float
    nitidez: float
    borda_forte: int = 255

    @property
    def qualidade(self) -> QualidadeFoto:
        return classificar_qualidade(self.largura, self.altura, self.brilho_medio, self.nitidez, self.borda_forte)


def classificar_qualidade(largura: int, altura: int, brilho_medio: float, nitidez: float,
                          borda_forte: int = 255) -> QualidadeFoto:
    """Um aviso por foto, do problema mais grave para o mais leve. Tremida: bordas fracas no geral
    e nenhum contorno forte (um produto nítido no fundo branco tem pouca borda, mas forte)."""
    if min(largura, altura) < LADO_MENOR_MINIMO:
        return QualidadeFoto.PEQUENA
    if brilho_medio < BRILHO_MINIMO:
        return QualidadeFoto.ESCURA
    if nitidez < NITIDEZ_MINIMA and borda_forte < BORDA_FORTE_MINIMA:
        return QualidadeFoto.TREMIDA
    return QualidadeFoto.OK


def tamanho_para_lado_maior(largura: int, altura: int, lado_maior: int) -> tuple[int, int]:
    """Novo tamanho com o lado maior limitado (nunca aumenta a foto)."""
    maior = max(largura, altura)
    if maior <= lado_maior:
        return largura, altura
    escala = lado_maior / maior
    return max(1, round(largura * escala)), max(1, round(altura * escala))


def caixa_em_pixels(caixa: tuple[int, int, int, int], largura: int, altura: int) -> tuple[int, int, int, int]:
    """Caixa normalizada de 0 a 1000 para pixels, com uma folga de 4% para não cortar a borda da etiqueta."""
    x0, y0, x1, y1 = caixa
    folga_x, folga_y = (x1 - x0) * 0.04, (y1 - y0) * 0.04
    return (
        max(0, int((x0 - folga_x) * largura / 1000)),
        max(0, int((y0 - folga_y) * altura / 1000)),
        min(largura, int((x1 + folga_x) * largura / 1000 + 0.999)),
        min(altura, int((y1 + folga_y) * altura / 1000 + 0.999)),
    )
