/**
 * Infraestrutura · Repositório de anúncios (localStorage)
 *
 * Faz o papel da API de anúncios. Os anúncios de cada conta ficam na chave dela
 * ("quickclick:v1:usuario:<id>:anuncios"): uma conta nunca enxerga os de outra.
 * O JSON guardado está em português (como a API terá); o front recebe nomes em inglês.
 */
import { USER_KEYS, newId, nowIso, readJson, simulateLatency, userKey, writeJson } from './localStore.js';

export class ListingNotFoundError extends Error {
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

/** JSON guardado → anúncio do front. */
const toListing = (anuncio) => ({
  id: anuncio.id,
  title: anuncio.titulo,
  description: anuncio.descricao ?? '',
  category: anuncio.categoria,
  condition: CONDITION_TO_FRONT[anuncio.condicao] ?? 'new',
  priceCents: anuncio.preco_centavos,
  suggestedPriceCents: anuncio.preco_sugerido_centavos ?? null,
  stock: anuncio.estoque,
  photos: anuncio.fotos ?? [],
  coverIndex: anuncio.capa ?? 0,
  illustration: anuncio.ilustracao ?? null,
  attributes: (anuncio.atributos ?? []).map(({ nome, valor }) => ({ name: nome, value: valor })),
  channels: mapChannels(anuncio.canais, STATUS_TO_FRONT),
  createdAt: anuncio.criado_em,
  updatedAt: anuncio.atualizado_em
});

/** Campos do front (só os presentes) → campos guardados. */
function toStoreFields(data) {
  const fields = {};
  if (data.title !== undefined) fields.titulo = data.title.trim();
  if (data.description !== undefined) fields.descricao = data.description.trim();
  if (data.category !== undefined) fields.categoria = data.category;
  if (data.condition !== undefined) fields.condicao = CONDITION_TO_STORE[data.condition] ?? 'novo';
  if (data.priceCents !== undefined) fields.preco_centavos = data.priceCents;
  if (data.suggestedPriceCents !== undefined) fields.preco_sugerido_centavos = data.suggestedPriceCents;
  if (data.stock !== undefined) fields.estoque = Number(data.stock);
  if (data.photos !== undefined) fields.fotos = data.photos;
  if (data.coverIndex !== undefined) fields.capa = data.coverIndex;
  if (data.illustration !== undefined) fields.ilustracao = data.illustration;
  if (data.attributes !== undefined) {
    fields.atributos = data.attributes.map(({ name, value }) => ({ nome: name, valor: value }));
  }
  if (data.channels !== undefined) fields.canais = mapChannels(data.channels, STATUS_TO_STORE);
  return fields;
}

async function load(accountId) {
  return readJson(userKey(accountId, USER_KEYS.LISTINGS), []);
}

/** Lança StorageFullError (localStore) quando as fotos não cabem mais no navegador. */
const save = (accountId, anuncios) => writeJson(userKey(accountId, USER_KEYS.LISTINGS), anuncios);

const byUpdatedDesc = (a, b) => String(b.atualizado_em).localeCompare(String(a.atualizado_em));

export async function listListings(accountId) {
  const anuncios = await load(accountId);
  await simulateLatency(220);
  return [...anuncios].sort(byUpdatedDesc).map(toListing);
}

export async function getListing(accountId, id) {
  const anuncios = await load(accountId);
  await simulateLatency(160);
  const anuncio = anuncios.find((item) => item.id === id);
  if (!anuncio) throw new ListingNotFoundError();
  return toListing(anuncio);
}

export async function createListing(accountId, data) {
  const anuncios = await load(accountId);
  await simulateLatency(240);
  const now = nowIso();
  const anuncio = {
    id: newId('a'),
    titulo: '',
    descricao: '',
    categoria: 'outros',
    condicao: 'novo',
    preco_centavos: 0,
    preco_sugerido_centavos: null,
    estoque: 0,
    fotos: [],
    capa: 0,
    ilustracao: null,
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
  const anuncios = await load(accountId);
  await simulateLatency(200);
  const index = anuncios.findIndex((item) => item.id === id);
  if (index < 0) throw new ListingNotFoundError();
  const updated = { ...anuncios[index], ...toStoreFields(patch), atualizado_em: nowIso() };
  const next = [...anuncios];
  next[index] = updated;
  save(accountId, next);
  return toListing(updated);
}

/** Copia um anúncio. A cópia nasce fora do ar (não publicada), com o título que a tela mandar. */
export async function duplicateListing(accountId, id, { title }) {
  const anuncios = await load(accountId);
  await simulateLatency(220);
  const original = anuncios.find((item) => item.id === id);
  if (!original) throw new ListingNotFoundError();
  const now = nowIso();
  const copy = {
    ...original,
    id: newId('a'),
    titulo: title,
    canais: mapChannels(original.canais, { publicado: 'nao_publicado', pausado: 'nao_publicado' }),
    criado_em: now,
    atualizado_em: now
  };
  save(accountId, [copy, ...anuncios]);
  return toListing(copy);
}

export async function removeListing(accountId, id) {
  const anuncios = await load(accountId);
  await simulateLatency(200);
  const next = anuncios.filter((item) => item.id !== id);
  if (next.length === anuncios.length) throw new ListingNotFoundError();
  save(accountId, next);
}
