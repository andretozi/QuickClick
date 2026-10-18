"""
Infraestrutura · IA · Preparar as fotos com o Pillow (sem IA, em memória)

    1. confere o conteúdo real (Pillow abre e verifica; a extensão não conta), até 10 MB e 40 megapixels,
       só JPEG, PNG, WEBP e HEIC (com o pillow-heif);
    2. corrige a orientação pelo EXIF e APAGA os metadados (EXIF e localização): a imagem é refeita
       só com os pixels, em RGB;
    3. mede a qualidade de graça: nitidez (variância das bordas), brilho médio e resolução;
    4. gera a versão de leitura (lado maior 1568, JPEG 90) e a de detalhe (até 2576) para recortar etiqueta.
Nada vai para disco, banco ou log.
"""

import io
import logging
import warnings

from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

from backend.application.ia.modelos import ArquivoDeFoto, FotoPreparada
from backend.domain.erros import FotoInvalida
from backend.domain.ia.fotos import (
    FORMATOS_ACEITOS,
    LADO_MAIOR_LEITURA,
    LADO_MAIOR_RECORTE_ETIQUETA,
    MAX_BYTES_POR_FOTO,
    MAX_FOTOS_POR_ANALISE,
    MAX_PIXELS,
    QUALIDADE_JPEG_LEITURA,
    MedidaDaFoto,
    caixa_em_pixels,
    tamanho_para_lado_maior,
)

log = logging.getLogger("quickclick.ia")

Image.MAX_IMAGE_PIXELS = MAX_PIXELS  # acima disso o Pillow recusa (bomba de descompressão)
LADO_DA_MEDIDA = 512

try:  # HEIC do iPhone, se a biblioteca abrir
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:  # sem pillow-heif, HEIC é recusado como formato não aceito
    pass


def _jpeg(imagem: Image.Image, qualidade: int) -> bytes:
    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", quality=qualidade, optimize=True)  # sem exif=: sai sem metadados
    return saida.getvalue()


def _redimensionada(imagem: Image.Image, lado_maior: int) -> Image.Image:
    tamanho = tamanho_para_lado_maior(imagem.width, imagem.height, lado_maior)
    if tamanho == imagem.size:
        return imagem
    return imagem.resize(tamanho, Image.Resampling.LANCZOS)


def _em_rgb_com_fundo_branco(imagem: Image.Image) -> Image.Image:
    """PNG ou WEBP com transparência ganha fundo branco (convert("RGB") deixaria o fundo preto)."""
    if imagem.mode in ("RGBA", "LA") or (imagem.mode == "P" and "transparency" in imagem.info):
        rgba = imagem.convert("RGBA")
        fundo = Image.new("RGB", rgba.size, (255, 255, 255))
        fundo.paste(rgba, mask=rgba.getchannel("A"))
        return fundo
    return imagem.convert("RGB")


def _percentil_do_histograma(histograma: list[int], fracao_do_topo: float) -> int:
    alvo, acumulado = sum(histograma) * fracao_do_topo, 0
    for valor in range(len(histograma) - 1, -1, -1):
        acumulado += histograma[valor]
        if acumulado >= alvo:
            return valor
    return 0


def medir(imagem: Image.Image) -> MedidaDaFoto:
    """Brilho médio, variância das bordas e força das bordas mais fortes, num tamanho fixo (lado 512)."""
    cinza = _redimensionada(imagem, LADO_DA_MEDIDA).convert("L")
    brilho = ImageStat.Stat(cinza).mean[0]
    bordas = cinza.filter(ImageFilter.FIND_EDGES)
    if bordas.width > 2 and bordas.height > 2:  # o filtro cria uma moldura forte de 1 px: fica de fora
        bordas = bordas.crop((1, 1, bordas.width - 1, bordas.height - 1))
    return MedidaDaFoto(largura=imagem.width, altura=imagem.height, brilho_medio=brilho,
                        nitidez=ImageStat.Stat(bordas).var[0],
                        borda_forte=_percentil_do_histograma(bordas.histogram(), 0.001))


class PillowPreparador:
    def preparar(self, arquivos: list[ArquivoDeFoto], primeiro_indice: int = 0) -> list[FotoPreparada]:
        if not arquivos:
            raise FotoInvalida("Manda pelo menos uma foto do produto.")
        if len(arquivos) > MAX_FOTOS_POR_ANALISE:
            raise FotoInvalida(f"Manda até {MAX_FOTOS_POR_ANALISE} fotos por análise.")
        return [self._preparar_uma(arquivo, primeiro_indice + i) for i, arquivo in enumerate(arquivos)]

    def _preparar_uma(self, arquivo: ArquivoDeFoto, indice: int) -> FotoPreparada:
        if len(arquivo.conteudo) > MAX_BYTES_POR_FOTO:
            raise FotoInvalida("Uma das fotos passou de 10 MB. Manda uma versão menor.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(arquivo.conteudo)) as conferida:
                    formato = (conferida.format or "").upper()
                    conferida.verify()  # confere a estrutura do arquivo
                with Image.open(io.BytesIO(arquivo.conteudo)) as aberta:
                    aberta.load()
                    girada = ImageOps.exif_transpose(aberta)
                    rgb = _em_rgb_com_fundo_branco(girada)
        except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning,
                OSError, ValueError, SyntaxError) as erro:
            log.info("Foto recusada (%s).", type(erro).__name__)
            raise FotoInvalida() from erro
        if formato not in FORMATOS_ACEITOS:
            raise FotoInvalida()
        # Refeita só com os pixels: EXIF, GPS, XMP e perfis ficam para trás
        limpa = Image.new("RGB", rgb.size)
        limpa.paste(rgb)
        return FotoPreparada(
            indice=indice,
            leitura_jpeg=_jpeg(_redimensionada(limpa, LADO_MAIOR_LEITURA), QUALIDADE_JPEG_LEITURA),
            detalhe_jpeg=_jpeg(_redimensionada(limpa, LADO_MAIOR_RECORTE_ETIQUETA), 92),
            largura=limpa.width,
            altura=limpa.height,
            medida=medir(limpa),
        )

    def recortar(self, foto: FotoPreparada, caixa: tuple[int, int, int, int]) -> bytes:
        with Image.open(io.BytesIO(foto.detalhe_jpeg)) as detalhe:
            detalhe.load()
            recorte = detalhe.crop(caixa_em_pixels(caixa, detalhe.width, detalhe.height))
            if max(recorte.size) < 400:  # etiqueta pequena: amplia um pouco para a leitura
                escala = 400 / max(recorte.size)
                recorte = recorte.resize((max(1, round(recorte.width * escala)), max(1, round(recorte.height * escala))),
                                         Image.Resampling.LANCZOS)
            return _jpeg(recorte.convert("RGB"), 92)
