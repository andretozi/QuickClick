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
export const toListing = (anuncio) => ({
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
  analysisId: anuncio.analise_id ?? null,
  channels: mapChannels(anuncio.canais, STATUS_TO_FRONT),
  createdAt: anuncio.criado_em,
  updatedAt: anuncio.atualizado_em
});

/** Campos do front (só os presentes) → campos guardados. */
export function toStoreFields(data) {
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
    analise_id: existing?.analise_id ?? null,
    canais: {
      ...(existing?.canais ?? {}),
      [ML_CHANNEL]: mlStatusToStore(mlItem.status)
    },
    criado_em: existing?.criado_em ?? mlItem.last_updated ?? now,
    atualizado_em: mlItem.last_updated ?? existing?.atualizado_em ?? now
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
  for (const mlItem of mlProducts) {
    if (!mlItem?.id) continue;
    let index = next.findIndex((item) => item.ml_item_id === mlItem.id);
    if (index < 0) {
      const targetTitle = normalizeTitle(mlItem.title);
      index = next.findIndex(
        (item) => !matched.has(item.id) && !item.ml_item_id && normalizeTitle(item.titulo) === targetTitle
      );
    }
    const updated = applyMlItemToStoreRecord(index >= 0 ? next[index] : null, mlItem);
    matched.add(updated.id);
    if (index >= 0) next[index] = updated;
    else next.unshift(updated);
  }
  return next;
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

/** Registro → Produto completo (fotos como estão, publicações em ordem fixa). */
function toProduct(record) {
  const canais = record.canais ?? {};
  return {
    id: record.id,
    titulo: String(record.titulo ?? ''),
    descricao: String(record.descricao ?? ''),
    categoria: record.categoria || inferCategoryFromTitle(record.titulo),
    condicao: record.condicao === 'usado' ? 'usado' : 'novo',
    preco_centavos: Number(record.preco_centavos ?? 0),
    preco_sugerido_centavos: record.preco_sugerido_centavos ?? null,
    estoque: Number(record.estoque ?? 0),
    fotos: record.fotos ?? [],
    capa: record.capa ?? 0,
    atributos: (record.atributos ?? []).map(({ id, nome, valor }) => ({ id: id ?? null, nome: nome ?? '', valor: valor ?? null })),
    analise_id: record.analise_id ?? null,
    criado_em: record.criado_em,
    atualizado_em: record.atualizado_em,
    publicacoes: Object.keys(canais)
      .sort()
      .map((canal) => ({
        canal,
        status: STATUS_TO_STORE[canais[canal]] ?? canais[canal],
        ...(canal === ML_CHANNEL
          ? {
              id_externo: record.ml_item_id ?? null,
              permalink: record.permalink ?? null,
              categoria_id: record.ml_categoria_id ?? null,
              saude: record.saude_ml ?? null,
              vendidos: Number(record.vendidos ?? 0)
            }
          : NO_EXTERNAL_DATA)
      }))
  };
}

/** Registro → corpo do PUT e da importação. Foto fora do https nunca vai: a lista fica vazia. */
export function toApi(record) {
  return { ...toProduct(record), fotos: allHttps(record.fotos) ? record.fotos ?? [] : [] };
}

/** Produto da API → registro guardado. */
export function fromApi(produto) {
  const publicacoes = produto.publicacoes ?? [];
  const ml = publicacoes.find((publicacao) => publicacao.canal === ML_CHANNEL);
  return {
    id: produto.id,
    ml_item_id: ml?.id_externo ?? null,
    permalink: ml?.permalink ?? null,
    ml_categoria_id: ml?.categoria_id ?? null,
    saude_ml: ml?.saude ?? null,
    vendidos: Number(ml?.vendidos ?? 0),
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
