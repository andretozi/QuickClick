"""
Infraestrutura · IA · Preparar as fotos com o Pillow (sem IA, em memória)

    1. confere o conteúdo real (Pillow abre e verifica; a extensão não conta), até 10 MB e 40 megapixels,
       só JPEG, PNG, WEBP e HEIC (com o pillow-heif);
    2. corrige a orientação pelo EXIF e APAGA os metadados (EXIF e localização): a imagem é refeita
       só com os pixels, em RGB;
    3. mede a qualidade de graça: nitidez (variância das bordas), brilho médio e resolução;
    4. gera a versão de leitura (lado maior até 1568, garantindo pelo menos 1200 px de área útil após
       recorte de bordas brancas para o zoom do Mercado Livre, JPEG 90) e a de detalhe (até 2576).
Nada vai para disco, banco ou log.
"""

import io
import logging
import warnings

from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

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
LADO_MINIMO_ML = 1200  # Mercado Livre exige >= 500 px após cortar bordas brancas e recomenda 1200 px para zoom
LADO_UTIL_MINIMO_ML = 1000
LADO_AMPLIADO_ML = 1600

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


def _caixa_util_sem_borda_clara(imagem: Image.Image) -> tuple[int, int, int, int] | None:
    """Encontra a caixa do produto ignorando bordas brancas ou quase brancas e ruído de JPEG nas extremidades."""
    cinza = imagem.convert("L")
    if min(cinza.size) >= 64:
        cinza = cinza.filter(ImageFilter.MedianFilter(size=3))
    # Limiar 28 em imagem invertida equivale a considerar branco/fundo claro qualquer pixel com luminância >= 227
    mascara = ImageOps.invert(cinza).point(lambda p: 255 if p > 28 else 0)
    # Ignora 2% da borda externa na detecção para que artefatos de moldura de 1-2 px não impeçam o recorte
    if mascara.width > 50 and mascara.height > 50:
        borda_x = max(1, round(mascara.width * 0.02))
        borda_y = max(1, round(mascara.height * 0.02))
        interior = mascara.crop((borda_x, borda_y, mascara.width - borda_x, mascara.height - borda_y))
        caixa_int = interior.getbbox()
        if caixa_int is not None:
            return (
                caixa_int[0] + borda_x,
                caixa_int[1] + borda_y,
                caixa_int[2] + borda_x,
                caixa_int[3] + borda_y,
            )
    return mascara.getbbox()


def _garantir_minimo_mercado_livre(imagem: Image.Image) -> Image.Image:
    """Garante que a imagem e a área útil (sem bordas brancas) tenham pelo menos 1200 px no lado maior,
    evitando a recusa do Mercado Livre quando o produto tem fundo branco amplo (< 500 px após corte)."""
    caixa = _caixa_util_sem_borda_clara(imagem)
    if caixa is not None:
        x0, y0, x1, y1 = caixa
        largura_util, altura_util = x1 - x0, y1 - y0
        if largura_util >= 16 and altura_util >= 16 and min(largura_util, altura_util) < LADO_UTIL_MINIMO_ML:
            margem_x = max(12, round(largura_util * 0.08))
            margem_y = max(12, round(altura_util * 0.08))
            recorte = imagem.crop((
                max(0, x0 - margem_x),
                max(0, y0 - margem_y),
                min(imagem.width, x1 + margem_x),
                min(imagem.height, y1 + margem_y),
            ))
            escala = max(
                LADO_MINIMO_ML / max(1, max(recorte.width, recorte.height)),
                900 / max(1, min(recorte.width, recorte.height)),
            )
            nova_largura = max(900, round(recorte.width * escala))
            nova_altura = max(900, round(recorte.height * escala))
            return recorte.resize((nova_largura, nova_altura), Image.Resampling.LANCZOS)
    if max(imagem.size) < LADO_MINIMO_ML or min(imagem.size) < 800:
        escala = max(
            LADO_MINIMO_ML / max(1, max(imagem.size)),
            800 / max(1, min(imagem.size)),
        )
        return imagem.resize(
            (max(800, round(imagem.width * escala)), max(800, round(imagem.height * escala))),
            Image.Resampling.LANCZOS,
        )
    return imagem


def ampliar_para_mercado_livre(conteudo_jpeg: bytes) -> bytes:
    """Segunda passagem para fotos de produtos brancos em fundo branco recusadas pelo corte de bordas do ML:
    aproxima o centro, amplia para 1600 px e adiciona uma moldura neutra sutil que impede o corte excessivo."""
    with Image.open(io.BytesIO(conteudo_jpeg)) as aberta:
        aberta.load()
        rgb = aberta.convert("RGB")
    caixa = _caixa_util_sem_borda_clara(rgb)
    if caixa is not None and (caixa[2] - caixa[0]) >= 32 and (caixa[3] - caixa[1]) >= 32:
        x0, y0, x1, y1 = caixa
        margem_x = max(8, round((x1 - x0) * 0.06))
        margem_y = max(8, round((y1 - y0) * 0.06))
        recorte = rgb.crop((
            max(0, x0 - margem_x),
            max(0, y0 - margem_y),
            min(rgb.width, x1 + margem_x),
            min(rgb.height, y1 + margem_y),
        ))
    else:
        corte_x = round(rgb.width * 0.14)
        corte_y = round(rgb.height * 0.14)
        recorte = rgb.crop((corte_x, corte_y, max(corte_x + 1, rgb.width - corte_x), max(corte_y + 1, rgb.height - corte_y)))
    escala = max(
        LADO_AMPLIADO_ML / max(1, max(recorte.width, recorte.height)),
        1200 / max(1, min(recorte.width, recorte.height)),
    )
    ampliada = recorte.resize(
        (max(1200, round(recorte.width * escala)), max(1200, round(recorte.height * escala))),
        Image.Resampling.LANCZOS,
    )
    # Moldura neutra a 2% da borda garante que o detector de bordas brancas do Mercado Livre
    # preserve pelo menos ~96% de 1600 px (> 1500 px), mesmo em produtos totalmente brancos (ex.: caneca branca).
    desenho = ImageDraw.Draw(ampliada)
    mx = max(10, round(ampliada.width * 0.02))
    my = max(10, round(ampliada.height * 0.02))
    desenho.rectangle(
        [mx, my, ampliada.width - 1 - mx, ampliada.height - 1 - my],
        outline=(185, 185, 190),
        width=2,
    )
    return _jpeg(ampliada, QUALIDADE_JPEG_LEITURA)


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
        leitura_pronta = _garantir_minimo_mercado_livre(_redimensionada(limpa, LADO_MAIOR_LEITURA))
        return FotoPreparada(
            indice=indice,
            leitura_jpeg=_jpeg(leitura_pronta, QUALIDADE_JPEG_LEITURA),
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

    def ampliar_para_publicacao(self, conteudo_jpeg: bytes) -> bytes:
        return ampliar_para_mercado_livre(conteudo_jpeg)
