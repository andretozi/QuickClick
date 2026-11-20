/**
 * Infraestrutura · Registro de anúncio: conversões puras, sem I/O (o self-check roda no Node).
 *
 * O formato guardado (titulo, canais, ml_item_id...) é o formato interno do front. toApi e
 * fromApi traduzem para o Produto da API (/api/produtos), em que canais e os campos ml_* viram
 * publicacoes. Fotos no modo híbrido: o servidor guarda só URLs https; uma lista com alguma
 * foto fora do https (dataURL de anúncio sem publicar) vai inteira para a chave local do produto.
 * Quem usa: listingsRepository.js e scripts/listings.check.mjs.
 */
import { newId, nowIso } from './localStore.js';

const ML_CHANNEL = 'mercado-livre';
const QS_CHANNEL = 'quickstore';
const STATUS_TO_FRONT = { publicado: 'published', pausado: 'paused', nao_publicado: 'unpublished' };
const STATUS_TO_STORE = { published: 'publicado', paused: 'pausado', unpublished: 'nao_publicado' };
const CONDITION_TO_FRONT = { novo: 'new', usado: 'used' };
const CONDITION_TO_STORE = { new: 'novo', used: 'usado' };
const NO_EXTERNAL_DATA = { id_externo: null, permalink: null, categoria_id: null, saude: null, vendidos: 0 };

export const mapChannels = (channels, table) =>
  Object.fromEntries(Object.entries(channels ?? {}).map(([slug, status]) => [slug, table[status] ?? status]));

const normalizeTitle = (text) =>
  String(text ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim();

const asExternalId = (value) => (value != null && String(value).trim() !== '' ? String(value).trim() : null);

export const safeHttpsUrl = (url, fallback = null) => {
  if (typeof url !== 'string') return fallback;
  const clean = url.trim();
  return clean.startsWith('https://') && clean.length <= 500 ? clean : fallback;
};

export const clampHealth = (value, fallback = null) => {
  if (value === null || value === undefined || value === '' || typeof value === 'boolean') return fallback;
  const num = Number(value);
  return Number.isFinite(num) && num >= 0 && num <= 100 ? num : fallback;
};

const optionalCents = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const num = Number(value);
  return Number.isFinite(num) && num >= 0 ? Math.round(num) : null;
};

const isChannelActiveInStore = (canais, slug) => {
  const st = canais?.[slug];
  return st === 'publicado' || st === 'pausado' || st === 'published' || st === 'paused';
};

function mlStatusToStore(status) {
  const clean = String(status ?? '').trim().toLowerCase();
  if (clean === 'active') return 'publicado';
  if (clean === 'paused' || clean === 'under_review') return 'pausado';
  return 'nao_publicado';
}

function isClosedExternalStatus(status) {
  const clean = String(status ?? '').toLowerCase();
  return clean === 'closed' || clean === 'inactive';
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
export const toListing = (anuncio) => {
  const mlSold = Number(anuncio.vendidos ?? 0);
  const qsSold = Number(anuncio.vendidos_qs ?? 0);
  return {
    id: anuncio.id,
    mlItemId: anuncio.ml_item_id ?? null,
    permalink: anuncio.permalink ?? null,
    mlCategoryId: anuncio.ml_categoria_id ?? null,
    health: anuncio.saude_ml ?? null,
    mlSoldQuantity: mlSold,
    mlPriceCents: optionalCents(anuncio.preco_centavos_ml),
    qsItemId: anuncio.qs_item_id ?? null,
    qsPermalink: anuncio.qs_permalink ?? null,
    qsCategoryId: anuncio.qs_categoria_id ?? null,
    qsHealth: anuncio.saude_qs ?? null,
    qsSoldQuantity: qsSold,
    qsPriceCents: optionalCents(anuncio.preco_centavos_qs),
    soldQuantity: mlSold + qsSold,
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
    analysisId: anuncio.analise_id ?? null,
    channels: mapChannels(anuncio.canais, STATUS_TO_FRONT),
    createdAt: anuncio.criado_em,
    updatedAt: anuncio.atualizado_em
  };
};

/** Campos do front (só os presentes) → campos guardados. */
export function toStoreFields(data) {
  const fields = {};
  if (data.mlItemId !== undefined) fields.ml_item_id = asExternalId(data.mlItemId);
  if (data.permalink !== undefined) fields.permalink = safeHttpsUrl(data.permalink);
  if (data.mlCategoryId !== undefined) fields.ml_categoria_id = data.mlCategoryId;
  if (data.health !== undefined) fields.saude_ml = clampHealth(data.health);
  if (data.mlSoldQuantity !== undefined) fields.vendidos = Number(data.mlSoldQuantity);
  else if (data.soldQuantity !== undefined && data.qsSoldQuantity === undefined) fields.vendidos = Number(data.soldQuantity);
  if (data.mlPriceCents !== undefined) fields.preco_centavos_ml = optionalCents(data.mlPriceCents);
  if (data.qsItemId !== undefined) fields.qs_item_id = asExternalId(data.qsItemId);
  if (data.qsPermalink !== undefined) fields.qs_permalink = safeHttpsUrl(data.qsPermalink);
  if (data.qsCategoryId !== undefined) fields.qs_categoria_id = data.qsCategoryId;
  if (data.qsHealth !== undefined) fields.saude_qs = clampHealth(data.qsHealth);
  if (data.qsSoldQuantity !== undefined) fields.vendidos_qs = Number(data.qsSoldQuantity);
  if (data.qsPriceCents !== undefined) fields.preco_centavos_qs = optionalCents(data.qsPriceCents);
  if (data.title !== undefined) fields.titulo = data.title.trim();
  if (data.description !== undefined) fields.descricao = data.description.trim();
  if (data.category !== undefined) fields.categoria = data.category;
  if (data.condition !== undefined) fields.condicao = CONDITION_TO_STORE[data.condition] ?? 'novo';
  if (data.priceCents !== undefined) fields.preco_centavos = data.priceCents;
  if (data.suggestedPriceCents !== undefined) fields.preco_sugerido_centavos = data.suggestedPriceCents;
  if (data.stock !== undefined) fields.estoque = Number(data.stock);
  if (data.photos !== undefined) fields.fotos = data.photos;
  if (data.coverIndex !== undefined) fields.capa = data.coverIndex;
  // O editor manda analysisId nulo ao editar (o rascunho de edição não tem a análise): nulo não apaga a ligação.
  if (data.analysisId) fields.analise_id = data.analysisId;
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

export function applyMlItemToStoreRecord(existing, mlItem) {
  const now = nowIso();
  const closed = isClosedExternalStatus(mlItem.status);
  const pictures = Array.isArray(mlItem.pictures) && mlItem.pictures.length
    ? mlItem.pictures.slice(0, 12) // o servidor aceita até 12 fotos; acima disso o sync daria 422
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
  const hasIncomingPrice = mlItem.price !== undefined && mlItem.price !== null;
  const incomingPriceCents = hasIncomingPrice
    ? Math.round(Number(mlItem.price) * 100)
    : existing?.preco_centavos_ml ?? existing?.preco_centavos ?? 0;
  const otherChannelActive = isChannelActiveInStore(existing?.canais, QS_CHANNEL);
  const existingQsPrice = optionalCents(existing?.preco_centavos_qs);
  const hasDistinctOtherPrice =
    Boolean(existing) &&
    otherChannelActive &&
    ((existingQsPrice !== null && existingQsPrice !== incomingPriceCents) ||
      (existingQsPrice === null && existing?.preco_centavos !== undefined && existing.preco_centavos !== incomingPriceCents));
  const basePriceCents = hasDistinctOtherPrice ? existing.preco_centavos : incomingPriceCents;
  const mlPriceCents = closed
    ? null
    : hasDistinctOtherPrice
      ? incomingPriceCents
      : optionalCents(existing?.preco_centavos_ml) !== null
        ? incomingPriceCents
        : null;
  const qsPriceCents =
    hasDistinctOtherPrice && existingQsPrice === null ? optionalCents(existing?.preco_centavos) : existingQsPrice;
  const stock = closed
    ? (existing?.estoque ?? Number(mlItem.available_quantity ?? 1))
    : mlItem.available_quantity !== undefined && mlItem.available_quantity !== null
      ? Number(mlItem.available_quantity)
      : existing?.estoque ?? 0;

  return {
    ...(existing ?? {}),
    id: existing?.id ?? newId('a'),
    ml_item_id: closed ? null : (asExternalId(mlItem.id) ?? asExternalId(existing?.ml_item_id)),
    permalink: closed ? null : safeHttpsUrl(mlItem.permalink, safeHttpsUrl(existing?.permalink)),
    ml_categoria_id: mlItem.category_id ?? existing?.ml_categoria_id ?? null,
    saude_ml: closed ? null : clampHealth(mlItem.health, clampHealth(existing?.saude_ml)),
    vendidos: Number(mlItem.sold_quantity ?? existing?.vendidos ?? 0),
    ...(mlPriceCents !== null || existing?.preco_centavos_ml !== undefined ? { preco_centavos_ml: mlPriceCents } : {}),
    qs_item_id: existing?.qs_item_id ?? null,
    qs_permalink: existing?.qs_permalink ?? null,
    qs_categoria_id: existing?.qs_categoria_id ?? null,
    saude_qs: existing?.saude_qs ?? null,
    vendidos_qs: Number(existing?.vendidos_qs ?? 0),
    ...(qsPriceCents !== null || existing?.preco_centavos_qs !== undefined ? { preco_centavos_qs: qsPriceCents } : {}),
    titulo: title,
    descricao: description,
    categoria: existing?.categoria || inferCategoryFromTitle(title),
    condicao: mlItem.condition === 'used' ? 'usado' : 'novo',
    preco_centavos: basePriceCents,
    preco_sugerido_centavos: existing?.preco_sugerido_centavos ?? null,
    estoque: stock,
    fotos: pictures,
    capa: existing?.capa ?? 0,
    atributos: attributes,
    analise_id: existing?.analise_id ?? null,
    canais: {
      ...(existing?.canais ?? {}),
      [ML_CHANNEL]: mlStatusToStore(mlItem.status)
    },
    criado_em: existing?.criado_em ?? mlItem.last_updated ?? now,
    atualizado_em: mlItem.last_updated ?? existing?.atualizado_em ?? now
  };
}

export function applyQuickStoreItemToStoreRecord(existing, qsItem) {
  const now = nowIso();
  const closed = isClosedExternalStatus(qsItem.status);
  const httpsPictures = (Array.isArray(qsItem.pictures) ? qsItem.pictures : [])
    .filter((p) => typeof p === 'string' && p.startsWith('https://'))
    .slice(0, 12);
  const pictures = httpsPictures.length
    ? httpsPictures
    : (typeof qsItem.thumbnail === 'string' && qsItem.thumbnail.startsWith('https://'))
      ? [qsItem.thumbnail]
      : existing?.fotos ?? [];
  const attributes = Array.isArray(qsItem.attributes) && qsItem.attributes.length
    ? qsItem.attributes.map((a) => ({ id: a.id ?? null, nome: a.name ?? a.id ?? '', valor: a.value ?? '' }))
    : existing?.atributos ?? [];
  const title = String(qsItem.title || existing?.titulo || '').trim();
  const description = qsItem.description !== undefined && qsItem.description !== ''
    ? String(qsItem.description)
    : existing?.descricao ?? '';
  const hasIncomingPrice = qsItem.price !== undefined && qsItem.price !== null;
  const incomingPriceCents = hasIncomingPrice
    ? Math.round(Number(qsItem.price) * 100)
    : existing?.preco_centavos_qs ?? existing?.preco_centavos ?? 0;
  const otherChannelActive = isChannelActiveInStore(existing?.canais, ML_CHANNEL);
  const existingMlPrice = optionalCents(existing?.preco_centavos_ml);
  const hasDistinctOtherPrice =
    Boolean(existing) &&
    otherChannelActive &&
    ((existingMlPrice !== null && existingMlPrice !== incomingPriceCents) ||
      (existingMlPrice === null && existing?.preco_centavos !== undefined && existing.preco_centavos !== incomingPriceCents));
  const basePriceCents = hasDistinctOtherPrice ? existing.preco_centavos : incomingPriceCents;
  const qsPriceCents = closed
    ? null
    : hasDistinctOtherPrice
      ? incomingPriceCents
      : optionalCents(existing?.preco_centavos_qs) !== null
        ? incomingPriceCents
        : null;
  const mlPriceCents =
    hasDistinctOtherPrice && existingMlPrice === null ? optionalCents(existing?.preco_centavos) : existingMlPrice;
  const stock = closed
    ? (existing?.estoque ?? Number(qsItem.available_quantity ?? 1))
    : qsItem.available_quantity !== undefined && qsItem.available_quantity !== null
      ? Number(qsItem.available_quantity)
      : existing?.estoque ?? 0;

  return {
    ...(existing ?? {}),
    id: existing?.id ?? newId('a'),
    ml_item_id: existing?.ml_item_id ?? null,
    permalink: existing?.permalink ?? null,
    ml_categoria_id: existing?.ml_categoria_id ?? null,
    saude_ml: existing?.saude_ml ?? null,
    vendidos: Number(existing?.vendidos ?? 0),
    ...(mlPriceCents !== null || existing?.preco_centavos_ml !== undefined ? { preco_centavos_ml: mlPriceCents } : {}),
    qs_item_id: closed ? null : (asExternalId(qsItem.id) ?? asExternalId(existing?.qs_item_id)),
    qs_permalink: closed ? null : safeHttpsUrl(qsItem.permalink, safeHttpsUrl(existing?.qs_permalink)),
    qs_categoria_id: qsItem.category_id ?? existing?.qs_categoria_id ?? null,
    saude_qs: closed ? null : clampHealth(qsItem.health, clampHealth(existing?.saude_qs)),
    vendidos_qs: Number(qsItem.sold_quantity ?? existing?.vendidos_qs ?? 0),
    ...(qsPriceCents !== null || existing?.preco_centavos_qs !== undefined ? { preco_centavos_qs: qsPriceCents } : {}),
    titulo: title,
    descricao: description,
    categoria: existing?.categoria || inferCategoryFromTitle(title),
    condicao: qsItem.condition === 'used' ? 'usado' : 'novo',
    preco_centavos: basePriceCents,
    preco_sugerido_centavos: existing?.preco_sugerido_centavos ?? null,
    estoque: stock,
    fotos: pictures,
    capa: existing?.capa ?? 0,
    atributos: attributes,
    analise_id: existing?.analise_id ?? null,
    canais: {
      ...(existing?.canais ?? {}),
      [QS_CHANNEL]: mlStatusToStore(qsItem.status)
    },
    criado_em: existing?.criado_em ?? qsItem.last_updated ?? now,
    atualizado_em: qsItem.last_updated ?? existing?.atualizado_em ?? now
  };
}

/**
 * Casa os itens do Mercado Livre com os registros: pelo ml_item_id e, sem ele, pelo título
 * normalizado. Os já casados ficam marcados por id (não por posição, que anda quando um item novo
 * entra no topo): dois itens de mesmo título nunca caem no mesmo anúncio.
 */
export function matchMlItems(records, mlProducts) {
  const next = [...records];
  const matched = new Set();
  const list = mlProducts ?? [];
  const seenIds = new Set(list.map((item) => asExternalId(item?.id)).filter(Boolean));
  for (const mlItem of list) {
    const extId = asExternalId(mlItem?.id);
    if (!extId) continue;
    let index = next.findIndex((item) => asExternalId(item.ml_item_id) === extId);
    if (index < 0) {
      const targetTitle = normalizeTitle(mlItem.title);
      index = next.findIndex(
        (item) => !matched.has(item.id) && !asExternalId(item.ml_item_id) && normalizeTitle(item.titulo) === targetTitle
      );
    }
    if (index < 0 && isClosedExternalStatus(mlItem.status)) continue;
    const updated = applyMlItemToStoreRecord(index >= 0 ? next[index] : null, mlItem);
    matched.add(updated.id);
    if (index >= 0) next[index] = updated;
    else next.unshift(updated);
  }
  const canClearMissing = list.length < 50;
  return next.map((record) => {
    const recId = asExternalId(record.ml_item_id);
    if (!recId || seenIds.has(recId) || !canClearMissing) return record;
    return {
      ...record,
      ml_item_id: null,
      permalink: null,
      saude_ml: null,
      canais: { ...(record.canais ?? {}), [ML_CHANNEL]: 'nao_publicado' }
    };
  });
}

/**
 * Casa os itens da QuickStore com os registros: pelo qs_item_id e, sem ele, pelo título normalizado.
 */
export function matchQuickStoreItems(records, qsProducts) {
  const next = [...records];
  const matched = new Set();
  const list = qsProducts ?? [];
  const seenIds = new Set(list.map((item) => asExternalId(item?.id)).filter(Boolean));
  for (const qsItem of list) {
    const extId = asExternalId(qsItem?.id);
    if (!extId) continue;
    let index = next.findIndex((item) => asExternalId(item.qs_item_id) === extId);
    if (index < 0) {
      const targetTitle = normalizeTitle(qsItem.title);
      index = next.findIndex(
        (item) => !matched.has(item.id) && !asExternalId(item.qs_item_id) && normalizeTitle(item.titulo) === targetTitle
      );
    }
    if (index < 0 && isClosedExternalStatus(qsItem.status)) continue;
    const updated = applyQuickStoreItemToStoreRecord(index >= 0 ? next[index] : null, qsItem);
    matched.add(updated.id);
    if (index >= 0) next[index] = updated;
    else next.unshift(updated);
  }
  const canClearMissing = list.length < 50;
  return next.map((record) => {
    const recId = asExternalId(record.qs_item_id);
    if (!recId || seenIds.has(recId) || !canClearMissing) return record;
    return {
      ...record,
      qs_item_id: null,
      qs_permalink: null,
      saude_qs: null,
      canais: { ...(record.canais ?? {}), [QS_CHANNEL]: 'nao_publicado' }
    };
  });
}

export const byUpdatedDesc = (a, b) => (Date.parse(b.atualizado_em) || 0) - (Date.parse(a.atualizado_em) || 0);

/** Todas as fotos são https (lista vazia também): podem ir para o servidor. */
export const allHttps = (fotos) => (fotos ?? []).every((foto) => String(foto).startsWith('https://'));

export const samePhotos = (a = [], b = []) => a.length === b.length && a.every((foto, i) => foto === b[i]);

/**
 * Fotos de um registro, na ordem de leitura: as do servidor; vazias, as da chave local do
 * produto; sem ela, as do registro antigo na chave "anuncios" (importado sem publicar); senão, nada.
 */
export function pickPhotos(record, localPhotos, legacyRecord) {
  if (record.fotos?.length) return record.fotos;
  if (Array.isArray(localPhotos) && localPhotos.length) return localPhotos;
  const legacy = legacyRecord?.fotos ?? [];
  return legacy.length && !allHttps(legacy) ? legacy : [];
}

function externalDataForChannel(record, canal) {
  if (canal === ML_CHANNEL) {
    const mlPrice = optionalCents(record.preco_centavos_ml);
    return {
      id_externo: asExternalId(record.ml_item_id),
      permalink: safeHttpsUrl(record.permalink),
      categoria_id: record.ml_categoria_id ? String(record.ml_categoria_id).slice(0, 40) : null,
      saude: clampHealth(record.saude_ml),
      vendidos: Math.max(0, Math.min(10_000_000, Math.trunc(Number(record.vendidos ?? 0) || 0))),
      ...(mlPrice !== null ? { preco_centavos: mlPrice } : {})
    };
  }
  if (canal === QS_CHANNEL) {
    const qsPrice = optionalCents(record.preco_centavos_qs);
    return {
      id_externo: asExternalId(record.qs_item_id),
      permalink: safeHttpsUrl(record.qs_permalink),
      categoria_id: record.qs_categoria_id ? String(record.qs_categoria_id).slice(0, 40) : null,
      saude: clampHealth(record.saude_qs),
      vendidos: Math.max(0, Math.min(10_000_000, Math.trunc(Number(record.vendidos_qs ?? 0) || 0))),
      ...(qsPrice !== null ? { preco_centavos: qsPrice } : {})
    };
  }
  return NO_EXTERNAL_DATA;
}

/** Registro → Produto completo (fotos como estão, publicações em ordem fixa). */
function toProduct(record) {
  const canais = record.canais ?? {};
  const rawAttrs = Array.isArray(record.atributos) ? record.atributos.slice(0, 30) : [];
  const atributos = rawAttrs.map(({ id, nome, valor }) => ({
    id: id != null && String(id).trim() !== '' ? String(id).trim().slice(0, 60) : null,
    nome: String(nome ?? '').slice(0, 60),
    valor:
      typeof valor === 'string'
        ? valor.slice(0, 120)
        : typeof valor === 'number' && Number.isFinite(valor)
          ? valor
          : typeof valor === 'boolean'
            ? valor
            : valor == null
              ? null
              : String(valor).slice(0, 120)
  }));
  const fotos = Array.isArray(record.fotos) ? record.fotos.slice(0, 12) : [];
  const rawCover = Math.trunc(Number(record.capa ?? 0) || 0);
  const maxCover = fotos.length > 0 ? Math.min(11, fotos.length - 1) : 11;
  const capa = Math.max(0, Math.min(maxCover, rawCover));
  return {
    id: record.id,
    titulo: String(record.titulo ?? '').slice(0, 120),
    descricao: String(record.descricao ?? '').slice(0, 4000),
    categoria: String(record.categoria || inferCategoryFromTitle(record.titulo)).slice(0, 40),
    condicao: record.condicao === 'usado' ? 'usado' : 'novo',
    preco_centavos: Math.max(0, Math.min(1_000_000_000, Math.round(Number(record.preco_centavos ?? 0) || 0))),
    preco_sugerido_centavos: optionalCents(record.preco_sugerido_centavos),
    estoque: Math.max(0, Math.min(1_000_000, Math.trunc(Number(record.estoque ?? 0) || 0))),
    fotos,
    capa,
    atributos,
    analise_id: record.analise_id ? String(record.analise_id).slice(0, 36) : null,
    criado_em: record.criado_em,
    atualizado_em: record.atualizado_em,
    publicacoes: Object.keys(canais)
      .sort()
      .map((canal) => ({
        canal,
        status: STATUS_TO_STORE[canais[canal]] ?? canais[canal],
        ...externalDataForChannel(record, canal)
      }))
  };
}

/** Registro → corpo do PUT e da importação. Foto fora do https nunca vai: a lista fica vazia. */
export function toApi(record) {
  const product = toProduct(record);
  const rawPhotos = Array.isArray(record.fotos) ? record.fotos : [];
  const canSendPhotos = allHttps(rawPhotos);
  const httpsPhotos = canSendPhotos
    ? rawPhotos.filter((foto) => typeof foto === 'string' && foto.startsWith('https://') && foto.length <= 1000).slice(0, 12)
    : [];
  const rawCover = Math.trunc(Number(record.capa ?? 0) || 0);
  const maxCover = httpsPhotos.length > 0 ? Math.min(11, httpsPhotos.length - 1) : 11;
  const capa = Math.max(0, Math.min(maxCover, rawCover));
  return { ...product, fotos: httpsPhotos, capa };
}

/** Produto da API → registro guardado. */
export function fromApi(produto) {
  const publicacoes = produto.publicacoes ?? [];
  const ml = publicacoes.find((publicacao) => publicacao.canal === ML_CHANNEL);
  const qs = publicacoes.find((publicacao) => publicacao.canal === QS_CHANNEL);
  const mlPrice = optionalCents(ml?.preco_centavos);
  const qsPrice = optionalCents(qs?.preco_centavos);
  return {
    id: produto.id,
    ml_item_id: ml?.id_externo ?? null,
    permalink: ml?.permalink ?? null,
    ml_categoria_id: ml?.categoria_id ?? null,
    saude_ml: ml?.saude ?? null,
    vendidos: Number(ml?.vendidos ?? 0),
    ...(mlPrice !== null ? { preco_centavos_ml: mlPrice } : {}),
    qs_item_id: qs?.id_externo ?? null,
    qs_permalink: qs?.permalink ?? null,
    qs_categoria_id: qs?.categoria_id ?? null,
    saude_qs: qs?.saude ?? null,
    vendidos_qs: Number(qs?.vendidos ?? 0),
    ...(qsPrice !== null ? { preco_centavos_qs: qsPrice } : {}),
    titulo: produto.titulo,
    descricao: produto.descricao ?? '',
    categoria: produto.categoria,
    condicao: produto.condicao,
    preco_centavos: produto.preco_centavos,
    preco_sugerido_centavos: produto.preco_sugerido_centavos ?? null,
    estoque: produto.estoque,
    fotos: produto.fotos ?? [],
    capa: produto.capa ?? 0,
    atributos: produto.atributos ?? [],
    analise_id: produto.analise_id ?? null,
    canais: Object.fromEntries(publicacoes.map((publicacao) => [publicacao.canal, publicacao.status])),
    criado_em: produto.criado_em,
    atualizado_em: produto.atualizado_em
  };
}

/** Mesmo conteúdo, sem contar atualizado_em: o sync só grava o que mudou. */
export function sameRecord(a, b) {
  const comparable = (record) => JSON.stringify({ ...toProduct(record), atualizado_em: null });
  return comparable(a) === comparable(b);
}
