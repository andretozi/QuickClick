/**
 * Infraestrutura · "IA" que sugere o anúncio e o preço (SIMULADA)
 *
 * Nada aqui é inteligência artificial de verdade e nenhuma foto sai do navegador.
 * - suggestListing: espera um pouco (como uma chamada de rede), lê a cor média da capa
 *   e escolhe, sempre do mesmo jeito para a mesma foto, um modelo de anúncio de exemplo.
 * - suggestPriceRange: monta uma faixa de preço a partir da categoria e da condição.
 *
 * Com o back, vira POST /api/ia/anuncio (a foto vai para um modelo de visão) e
 * GET /api/precos/faixa (preços de itens parecidos nos marketplaces).
 */
import { averageColor } from '../media/imageResizer.js';
import { simulateLatency } from '../storage/localStore.js';

/** Modelos de exemplo, por categoria. {cor} vira o nome da cor lida na foto. */
const TEMPLATES = [
  {
    category: 'calcados',
    title: 'Tênis casual {cor}, confortável e leve',
    description:
      'Tênis casual na cor {cor}, com palmilha macia e solado antiderrapante. Ótimo para o dia a dia. Pouco usado, sem marcas de desgaste. Envio rápido e bem embalado.'
  },
  {
    category: 'moda',
    title: 'Camiseta de algodão {cor}, caimento solto',
    description:
      'Camiseta de algodão na cor {cor}, tecido macio e caimento solto. Lavada com cuidado, sem manchas nem furos. Veste bem e combina com tudo.'
  },
  {
    category: 'casa',
    title: 'Luminária de mesa {cor} com braço articulado',
    description:
      'Luminária de mesa na cor {cor}, com braço articulado e cúpula de metal. Ideal para escrivaninha e leitura. Funcionando perfeitamente.'
  },
  {
    category: 'eletronicos',
    title: 'Fone de ouvido sem fio {cor} com estojo',
    description:
      'Fone sem fio na cor {cor}, com estojo de carga e boa bateria. Som limpo e graves na medida. Acompanha cabo. Testado e funcionando.'
  },
  {
    category: 'acessorios',
    title: 'Bolsa transversal {cor} com alça regulável',
    description:
      'Bolsa transversal na cor {cor}, com alça regulável, bolso interno e fecho de zíper. Material resistente e fácil de limpar.'
  },
  {
    category: 'cozinha',
    title: 'Jogo de potes {cor} com tampa, 5 peças',
    description:
      'Jogo com 5 potes na cor {cor}, com tampas que vedam bem. Vai ao micro ondas e à lava louças. Perfeito para organizar a cozinha.'
  },
  {
    category: 'livros',
    title: 'Livro de capa {cor} em ótimo estado',
    description: 'Livro com capa na cor {cor}, páginas limpas e sem anotações. Lido uma vez e guardado com cuidado.'
  }
];

/** Nomes de cor do jeito que se escreve num anúncio. */
const COLORS = [
  { name: 'preto', rgb: [30, 30, 30] },
  { name: 'branco', rgb: [235, 235, 235] },
  { name: 'cinza', rgb: [128, 128, 128] },
  { name: 'azul', rgb: [40, 80, 170] },
  { name: 'vermelho', rgb: [190, 40, 40] },
  { name: 'verde', rgb: [50, 140, 80] },
  { name: 'amarelo', rgb: [230, 200, 50] },
  { name: 'laranja', rgb: [235, 130, 40] },
  { name: 'rosa', rgb: [230, 140, 170] },
  { name: 'marrom', rgb: [120, 80, 50] },
  { name: 'bege', rgb: [215, 195, 160] },
  { name: 'roxo', rgb: [120, 70, 160] }
];

/** A cor da lista mais perto da média lida na foto. */
function colorName({ r, g, b }) {
  let best = COLORS[0];
  let bestDistance = Infinity;
  COLORS.forEach((color) => {
    const [cr, cg, cb] = color.rgb;
    const distance = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2;
    if (distance < bestDistance) {
      best = color;
      bestDistance = distance;
    }
  });
  return best.name;
}

/** Número estável a partir de um texto (o mesmo texto dá sempre o mesmo número). */
function hash(text) {
  let value = 2166136261;
  for (let i = 0; i < text.length; i += 97) {
    value ^= text.charCodeAt(i);
    value = Math.imul(value, 16777619);
  }
  return value >>> 0;
}

/** Preço base por categoria, em centavos (simulado). */
const BASE_PRICE = {
  moda: 7990,
  calcados: 18990,
  acessorios: 14990,
  casa: 12990,
  cozinha: 8990,
  eletronicos: 21990,
  livros: 3990,
  esporte: 15990,
  beleza: 6990,
  brinquedos: 9990,
  outros: 9990
};

/** Arredonda para um preço de vitrine: R$ 189,90 em vez de R$ 187,33. */
const showcasePrice = (cents) => Math.max(990, Math.round(cents / 1000) * 1000 - 10);

/**
 * Sugere título, descrição, categoria e condição a partir da capa. SIMULADO.
 * @param {{ photo: string }} input  data URL da foto de capa
 */
export async function suggestListing({ photo }) {
  const [color] = await Promise.all([averageColor(photo).then(colorName), simulateLatency(2100)]);
  const template = TEMPLATES[hash(photo) % TEMPLATES.length];
  const fill = (text) => text.replaceAll('{cor}', color);
  return {
    title: fill(template.title).slice(0, 60),
    description: fill(template.description),
    category: template.category,
    condition: 'used'
  };
}

/**
 * Faixa de preço de itens parecidos. SIMULADA a partir da categoria e da condição.
 * @returns {Promise<{ minCents: number, suggestedCents: number, maxCents: number }>}
 */
export async function suggestPriceRange({ category, condition, title = '' }) {
  await simulateLatency(700);
  const base = BASE_PRICE[category] ?? BASE_PRICE.outros;
  const conditionFactor = condition === 'new' ? 1.25 : 0.85;
  const wobble = 0.9 + (hash(`${category}:${title}`) % 21) / 100; // entre 0,90 e 1,10
  const suggested = base * conditionFactor * wobble;
  return {
    minCents: showcasePrice(suggested * 0.72),
    suggestedCents: showcasePrice(suggested),
    maxCents: showcasePrice(suggested * 1.38)
  };
}
