/**
 * Infraestrutura · Repositório de anúncios (localStorage + sincronização com o Mercado Livre)
 *
 * Faz o papel da API local de anúncios e sincroniza os dados vindos do Mercado Livre.
 * Os anúncios de cada conta ficam na chave dela ("quickclick:v1:usuario:<id>:anuncios"):
 * uma conta nunca enxerga os de outra.
 */
import { USER_KEYS, newId, nowIso, readJson, simulateLatency, userKey, writeJson } from './localStore.js';

class ListingNotFoundError extends Error {
  constructor() {
    super('anuncio_nao_encontrado');
    this.name = 'ListingNotFoundError';
    this.code = 'anuncio_nao_encontrado';
  }
}

const STATUS_TO_FRONT = { publicado: 'published', pausado: 'paused', nao_publicado: 'unpublished' };
const STATUS_TO_STORE = { published: 'publicado', paused: 'pausado', unpublished: 'nao_publicado' };
const CONDITION_TO_FRONT = { novo: 'new', usado: 'used' };
const CONDITION_TO_STORE = { new: 'novo', used: 'usado' };

const mapChannels = (channels, table) =>
  Object.fromEntries(Object.entries(channels ?? {}).map(([slug, status]) => [slug, table[status] ?? status]));

const normalizeTitle = (text) =>
  String(text ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();

function mlStatusToStore(status) {
  if (status === 'active') return 'publicado';
  if (status === 'paused' || status === 'under_review') return 'pausado';
  return 'nao_publicado';
}

function inferCategoryFromTitle(title) {
  const normalized = normalizeTitle(title);
  if (/\b(caneca|xicara|copo|prato|panela|talher|tigela|garrafa|pote)\b/.test(normalized)) return 'cozinha';
  if (/\b(tenis|sapato|bota|sandalia|chinelo|sapatilha)\b/.test(normalized)) return 'calcados';
  if (/\b(camisa|camiseta|calca|vestido|jaqueta|blusa|moletom|shorts|saia)\b/.test(normalized)) return 'moda';
  if (/\b(bolsa|mochila|carteira|cinto|oculos|relogio|colar|anel)\b/.test(normalized)) return 'acessorios';
  if (/\b(celular|notebook|fone|teclado|mouse|monitor|camera|console|carregador)\b/.test(normalized)) return 'eletronicos';
  if (/\b(livro|revista|hq|manga)\b/.test(normalized)) return 'livros';
  if (/\b(luminaria|almofada|tapete|quadro|vaso|cortina|decoracao)\b/.test(normalized)) return 'casa';
  return 'outros';
}

/** JSON guardado → anúncio do front. */
const toListing = (anuncio) => ({
  id: anuncio.id,
  mlItemId: anuncio.ml_item_id ?? null,
  permalink: anuncio.permalink ?? null,
  mlCategoryId: anuncio.ml_categoria_id ?? null,
  health: anuncio.saude_ml ?? null,
  soldQuantity: Number(anuncio.vendidos ?? 0),
  title: anuncio.titulo,
  description: anuncio.descricao ?? '',
  category: anuncio.categoria || inferCategoryFromTitle(anuncio.titulo),
  condition: CONDITION_TO_FRONT[anuncio.condicao] ?? 'new',
  priceCents: anuncio.preco_centavos,
  suggestedPriceCents: anuncio.preco_sugerido_centavos ?? null,
  stock: anuncio.estoque,
  photos: anuncio.fotos ?? [],
  coverIndex: anuncio.capa ?? 0,
  attributes: (anuncio.atributos ?? []).map(({ id, nome, valor }) => ({ id: id ?? null, name: nome, value: valor })),
  channels: mapChannels(anuncio.canais, STATUS_TO_FRONT),
  createdAt: anuncio.criado_em,
  updatedAt: anuncio.atualizado_em
});

/** Campos do front (só os presentes) → campos guardados. */
function toStoreFields(data) {
  const fields = {};
  if (data.mlItemId !== undefined) fields.ml_item_id = data.mlItemId;
  if (data.permalink !== undefined) fields.permalink = data.permalink;
  if (data.mlCategoryId !== undefined) fields.ml_categoria_id = data.mlCategoryId;
  if (data.health !== undefined) fields.saude_ml = data.health;
  if (data.soldQuantity !== undefined) fields.vendidos = Number(data.soldQuantity);
  if (data.title !== undefined) fields.titulo = data.title.trim();
  if (data.description !== undefined) fields.descricao = data.description.trim();
  if (data.category !== undefined) fields.categoria = data.category;
  if (data.condition !== undefined) fields.condicao = CONDITION_TO_STORE[data.condition] ?? 'novo';
  if (data.priceCents !== undefined) fields.preco_centavos = data.priceCents;
  if (data.suggestedPriceCents !== undefined) fields.preco_sugerido_centavos = data.suggestedPriceCents;
  if (data.stock !== undefined) fields.estoque = Number(data.stock);
  if (data.photos !== undefined) fields.fotos = data.photos;
  if (data.coverIndex !== undefined) fields.capa = data.coverIndex;
  if (data.attributes !== undefined) {
    fields.atributos = data.attributes.map(({ id, name, key, value }) => ({
      id: id ?? null,
      nome: name ?? key ?? '',
      valor: value
    }));
  }
  if (data.channels !== undefined) fields.canais = mapChannels(data.channels, STATUS_TO_STORE);
  return fields;
}

function applyMlItemToStoreRecord(existing, mlItem) {
  const now = nowIso();
  const pictures = Array.isArray(mlItem.pictures) && mlItem.pictures.length
    ? mlItem.pictures
    : mlItem.thumbnail
      ? [mlItem.thumbnail]
      : existing?.fotos ?? [];
  const attributes = Array.isArray(mlItem.attributes) && mlItem.attributes.length
    ? mlItem.attributes.map((a) => ({ id: a.id ?? null, nome: a.name ?? a.id ?? '', valor: a.value ?? '' }))
    : existing?.atributos ?? [];
  const title = String(mlItem.title || existing?.titulo || '').trim();
  const description = mlItem.description !== undefined && mlItem.description !== ''
    ? String(mlItem.description)
    : existing?.descricao ?? '';
  const priceCents = mlItem.price !== undefined && mlItem.price !== null
    ? Math.round(Number(mlItem.price) * 100)
    : existing?.preco_centavos ?? 0;
  const stock = mlItem.available_quantity !== undefined && mlItem.available_quantity !== null
    ? Number(mlItem.available_quantity)
    : existing?.estoque ?? 0;

  return {
    id: existing?.id ?? newId('a'),
    ml_item_id: mlItem.id ?? existing?.ml_item_id ?? null,
    permalink: mlItem.permalink ?? existing?.permalink ?? null,
    ml_categoria_id: mlItem.category_id ?? existing?.ml_categoria_id ?? null,
    saude_ml: mlItem.health ?? existing?.saude_ml ?? null,
    vendidos: Number(mlItem.sold_quantity ?? existing?.vendidos ?? 0),
    titulo: title,
    descricao: description,
    categoria: existing?.categoria || inferCategoryFromTitle(title),
    condicao: mlItem.condition === 'used' ? 'usado' : 'novo',
    preco_centavos: priceCents,
    preco_sugerido_centavos: existing?.preco_sugerido_centavos ?? null,
    estoque: stock,
    fotos: pictures,
    capa: 0,
    atributos: attributes,
    canais: {
      ...(existing?.canais ?? {}),
      'mercado-livre': mlStatusToStore(mlItem.status)
    },
    criado_em: existing?.criado_em ?? mlItem.last_updated ?? now,
    atualizado_em: mlItem.last_updated ?? existing?.atualizado_em ?? now
  };
}

/**
 * Ler e gravar sempre juntos, sem await no meio (a latência simulada vem antes): assim
 * duas ações seguidas, como pausar um anúncio e duplicar outro, não se atropelam.
 */
const load = (accountId) => readJson(userKey(accountId, USER_KEYS.LISTINGS), []);

/** Lança StorageFullError (localStore) quando as fotos não cabem mais no navegador. */
const save = (accountId, anuncios) => writeJson(userKey(accountId, USER_KEYS.LISTINGS), anuncios);

const byUpdatedDesc = (a, b) => String(b.atualizado_em).localeCompare(String(a.atualizado_em));

export async function listListings(accountId) {
  await simulateLatency(180);
  const anuncios = load(accountId);
  return [...anuncios].sort(byUpdatedDesc).map(toListing);
}

export async function getListing(accountId, id) {
  await simulateLatency(120);
  const anuncios = load(accountId);
  const anuncio = anuncios.find((item) => item.id === id);
  if (!anuncio) throw new ListingNotFoundError();
  return toListing(anuncio);
}

/**
 * Sincroniza a lista de anúncios locais com os produtos reais retornados pelo Mercado Livre.
 * Atualiza fotos, título, descrição, atributos, preço, estoque, vendas e status.
 */
export async function syncListingsWithMercadoLivre(accountId, mlProducts) {
  if (!Array.isArray(mlProducts)) return listListings(accountId);
  const anuncios = load(accountId);
  const next = [...anuncios];
  const matchedIndices = new Set();

  for (const mlItem of mlProducts) {
    if (!mlItem?.id) continue;
    let index = next.findIndex((item) => item.ml_item_id === mlItem.id);
    if (index < 0) {
      const targetTitle = normalizeTitle(mlItem.title);
      index = next.findIndex(
        (item, idx) => !matchedIndices.has(idx) && !item.ml_item_id && normalizeTitle(item.titulo) === targetTitle
      );
    }
    if (index >= 0) {
      matchedIndices.add(index);
      next[index] = applyMlItemToStoreRecord(next[index], mlItem);
    } else {
      const created = applyMlItemToStoreRecord(null, mlItem);
      next.unshift(created);
      matchedIndices.add(0);
    }
  }

  save(accountId, next);
  return [...next].sort(byUpdatedDesc).map(toListing);
}

/** Atualiza um anúncio local específico com os dados frescos vindos do Mercado Livre. */
export async function mergeMercadoLivreItem(accountId, id, mlItem) {
  const anuncios = load(accountId);
  const index = anuncios.findIndex((item) => item.id === id);
  if (index < 0) throw new ListingNotFoundError();
  const updated = applyMlItemToStoreRecord(anuncios[index], mlItem);
  const next = [...anuncios];
  next[index] = updated;
  save(accountId, next);
  return toListing(updated);
}

export async function createListing(accountId, data) {
  await simulateLatency(200);
  const anuncios = load(accountId);
  const now = nowIso();
  const anuncio = {
    id: newId('a'),
    ml_item_id: null,
    permalink: null,
    ml_categoria_id: null,
    saude_ml: null,
    vendidos: 0,
    titulo: '',
    descricao: '',
    categoria: 'outros',
    condicao: 'novo',
    preco_centavos: 0,
    preco_sugerido_centavos: null,
    estoque: 0,
    fotos: [],
    capa: 0,
    atributos: [],
    canais: {},
    ...toStoreFields(data),
    criado_em: now,
    atualizado_em: now
  };
  save(accountId, [anuncio, ...anuncios]);
  return toListing(anuncio);
}

export async function updateListing(accountId, id, patch) {
  await simulateLatency(160);
  const anuncios = load(accountId);
  const index = anuncios.findIndex((item) => item.id === id);
  if (index < 0) throw new ListingNotFoundError();
  const updated = { ...anuncios[index], ...toStoreFields(patch), atualizado_em: nowIso() };
  const next = [...anuncios];
  next[index] = updated;
  save(accountId, next);
  return toListing(updated);
}

/** Copia um anúncio. A cópia nasce fora do ar (não publicada), sem vínculo com o item original do ML. */
export async function duplicateListing(accountId, id, { title }) {
  await simulateLatency(200);
  const anuncios = load(accountId);
  const original = anuncios.find((item) => item.id === id);
  if (!original) throw new ListingNotFoundError();
  const now = nowIso();
  const copy = {
    ...original,
    id: newId('a'),
    ml_item_id: null,
    permalink: null,
    saude_ml: null,
    vendidos: 0,
    titulo: title,
    canais: mapChannels(original.canais, { publicado: 'nao_publicado', pausado: 'nao_publicado' }),
    criado_em: now,
    atualizado_em: now
  };
  save(accountId, [copy, ...anuncios]);
  return toListing(copy);
}

export async function removeListing(accountId, id) {
  await simulateLatency(160);
  const anuncios = load(accountId);
  const next = anuncios.filter((item) => item.id !== id);
  if (next.length === anuncios.length) throw new ListingNotFoundError();
  save(accountId, next);
}
