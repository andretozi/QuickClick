/**
 * Infraestrutura · Redução das fotos no navegador (canvas)
 *
 * Cada foto vira um JPEG de no máximo 800 px no lado maior, guardado como data URL.
 * Assim um anúncio com 6 fotos fica em algumas centenas de KB e cabe no localStorage.
 * Com o back, a foto original sobe para o armazenamento de arquivos e este passo some.
 */
const MAX_SIDE = 800;
const QUALITY = 0.8;

export class InvalidImageError extends Error {
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

/** File → data URL em JPEG, com no máximo 800 px no lado maior. */
export async function resizeImage(file) {
  if (!file?.type?.startsWith('image/')) throw new InvalidImageError();
  const url = URL.createObjectURL(file);
  try {
    const image = await loadImage(url);
    const scale = Math.min(1, MAX_SIDE / Math.max(image.naturalWidth, image.naturalHeight));
    const width = Math.max(1, Math.round(image.naturalWidth * scale));
    const height = Math.max(1, Math.round(image.naturalHeight * scale));
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext('2d');
    context.fillStyle = '#ffffff'; // fundo branco para PNG com transparência
    context.fillRect(0, 0, width, height);
    context.drawImage(image, 0, 0, width, height);
    return canvas.toDataURL('image/jpeg', QUALITY);
  } finally {
    URL.revokeObjectURL(url);
  }
}

/** Cor média do miolo de uma foto ({ r, g, b }), lida numa miniatura. Usada pela IA simulada. */
export async function averageColor(dataUrl) {
  const image = await loadImage(dataUrl);
  const canvas = document.createElement('canvas');
  canvas.width = 24;
  canvas.height = 24;
  const context = canvas.getContext('2d', { willReadFrequently: true });
  context.drawImage(image, 0, 0, 24, 24);
  const { data } = context.getImageData(4, 4, 16, 16); // o miolo, longe do fundo
  const all = { r: 0, g: 0, b: 0, n: 0 };
  const vivid = { r: 0, g: 0, b: 0, n: 0 }; // pixels com cor de verdade (o produto, não o fundo)
  for (let i = 0; i < data.length; i += 4) {
    const [r, g, b] = [data[i], data[i + 1], data[i + 2]];
    const bucket = Math.max(r, g, b) - Math.min(r, g, b) > 50 ? [all, vivid] : [all];
    bucket.forEach((sum) => {
      sum.r += r;
      sum.g += g;
      sum.b += b;
      sum.n += 1;
    });
  }
  const pick = vivid.n > all.n * 0.15 ? vivid : all;
  return { r: pick.r / pick.n, g: pick.g / pick.n, b: pick.b / pick.n };
}
