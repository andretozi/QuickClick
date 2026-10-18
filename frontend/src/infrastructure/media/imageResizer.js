/**
 * Infraestrutura · Fotos no navegador (canvas)
 *
 * De cada arquivo escolhido saem duas versões, as duas desenhadas a partir do original:
 * - a de guardar: JPEG de até 1200 px no lado maior (tamanho recomendado pelo Mercado Livre
 *   para ativar o zoom), em data URL, que fica no rascunho e no anúncio;
 * - a de leitura: JPEG de até 3000 px, qualidade 0,9, em Blob, que vai para a análise da IA
 *   e para a publicação no Mercado Livre.
 * O back também apaga os metadados (EXIF e localização) e ajusta bordas brancas antes de mandar.
 */
const STORED_SIDE = 1200;
const STORED_QUALITY = 0.84;
const READING_SIDE = 3000; // o back reduz para 1568 (IA/ML) e 2576 (etiqueta)
const READING_QUALITY = 0.9;

class InvalidImageError extends Error {
  constructor() {
    super('imagem_invalida');
    this.name = 'InvalidImageError';
    this.code = 'imagem_invalida';
  }
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new InvalidImageError());
    image.src = src;
  });
}

/** Desenha a imagem com o lado maior limitado, em fundo branco (PNG com transparência). */
function drawScaled(image, maxSide) {
  const scale = Math.min(1, maxSide / Math.max(image.naturalWidth, image.naturalHeight));
  const width = Math.max(1, Math.round(image.naturalWidth * scale));
  const height = Math.max(1, Math.round(image.naturalHeight * scale));
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d');
  context.fillStyle = '#ffffff';
  context.fillRect(0, 0, width, height);
  context.drawImage(image, 0, 0, width, height);
  return canvas;
}

function canvasToBlob(canvas, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new InvalidImageError())), 'image/jpeg', quality);
  });
}

async function withImage(file, work) {
  if (!file?.type?.startsWith('image/')) throw new InvalidImageError();
  const url = URL.createObjectURL(file);
  try {
    return await work(await loadImage(url));
  } finally {
    URL.revokeObjectURL(url);
  }
}

/** File → data URL em JPEG, com no máximo 1200 px no lado maior (a versão de guardar). */
export async function resizeImage(file) {
  return withImage(file, (image) => drawScaled(image, STORED_SIDE).toDataURL('image/jpeg', STORED_QUALITY));
}

/** File → as duas versões de uma vez: { stored: data URL de 1200 px, reading: Blob de até 3000 px }. */
export async function preparePhotoVersions(file) {
  return withImage(file, async (image) => ({
    stored: drawScaled(image, STORED_SIDE).toDataURL('image/jpeg', STORED_QUALITY),
    reading: await canvasToBlob(drawScaled(image, READING_SIDE), READING_QUALITY)
  }));
}

/** Só a versão de leitura (foto extra da etiqueta, do verso ou de um detalhe). */
export async function readingPhoto(file) {
  return withImage(file, (image) => canvasToBlob(drawScaled(image, READING_SIDE), READING_QUALITY));
}

/** Data URL guardada → Blob, para mandar ao back quando a versão de leitura já não está na memória. */
export function dataUrlToBlob(dataUrl) {
  const [header, base64 = ''] = String(dataUrl).split(',');
  const type = /data:([^;]+)/.exec(header)?.[1] ?? 'image/jpeg';
  const bytes = atob(base64);
  const buffer = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i += 1) buffer[i] = bytes.charCodeAt(i);
  return new Blob([buffer], { type });
}
