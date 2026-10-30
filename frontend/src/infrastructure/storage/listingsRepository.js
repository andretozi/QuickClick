/**
 * Infraestrutura · Repositório de anúncios (API /api/produtos + sincronização com o Mercado Livre)
 *
 * Os anúncios ficam no banco, por vendedor. As funções exportadas mantêm a assinatura e o
 * retorno de quando tudo ficava no localStorage. No navegador ficam só:
 * - as fotos fora do https (anúncio sem publicar), na chave "fotos_anuncio:<id>" do produto;
 * - a cópia da última lista boa ("anuncios_cache"), para o painel sem conexão;
 * - a chave antiga "anuncios", importada uma vez por conta e nunca escrita nem apagada aqui.
 * As conversões puras estão em listingRecord.js.
 */
import { ApiError, requestJson } from '../http/httpClient.js';
import { STORAGE_KEYS, USER_KEYS, newId, nowIso, readJson, removeKey, userKey, writeJson } from './localStore.js';
import {
  allHttps,
  applyMlItemToStoreRecord,
  byUpdatedDesc,
  fromApi,
  mapChannels,
  matchMlItems,
  pickPhotos,
  samePhotos,
  sameRecord,
  toApi,
  toListing,
  toStoreFields
} from './listingRecord.js';

class ListingNotFoundError extends Error {
  constructor() {
    super('anuncio_nao_encontrado');
    this.name = 'ListingNotFoundError';
    this.code = 'anuncio_nao_encontrado';
  }
}

const productPath = (id) => `/produtos/${encodeURIComponent(id)}`;
const photosKey = (accountId, id) => userKey(accountId, `${USER_KEYS.LISTING_PHOTOS}:${id}`);

const legacyRecords = (accountId) => {
  const records = readJson(userKey(accountId, USER_KEYS.LISTINGS), []);
  return Array.isArray(records) ? records.filter((record) => record?.id) : [];
};

/** Rede fora, back fora do ar ou 5xx. */
const isConnectionError = (error) => error?.status === 0 || error?.status >= 500 || error?.code === 'sem_conexao';

/**
 * O token sai da sessão gravada, que todas as abas dividem; a conta vem da memória desta aba.
 * Se outra aba trocou de conta, nada é pedido nem gravado em nome desta (vira 401).
 */
function assertSessionAccount(accountId) {
  const sessao = readJson(STORAGE_KEYS.SESSION, null);
  if (sessao?.conta_id == null || String(sessao.conta_id) !== String(accountId)) {
    throw new ApiError({ status: 401, code: 'nao_autenticado' });
  }
}

/** requestJson conferindo a conta antes do pedido e depois da resposta. */
async function api(accountId, path, options) {
  assertSessionAccount(accountId);
  const data = await requestJson(path, options);
  assertSessionAccount(accountId);
  return data;
}

const notFound = (error) => {
  throw error?.status === 404 ? new ListingNotFoundError() : error;
};

/** Junta as fotos guardadas no navegador aos registros que vieram do servidor sem foto. */
function withPhotos(accountId, records) {
  let legacy;
  return records.map((record) => {
    if (record.fotos?.length) return record;
    legacy ??= new Map(legacyRecords(accountId).map((item) => [item.id, item]));
    const local = readJson(photosKey(accountId, record.id), null);
    return { ...record, fotos: pickPhotos(record, local, legacy.get(record.id)) };
  });
}

const imports = new Map();

/** Importação única da chave antiga, uma Promise por conta e por carga da página. */
function importOnce(accountId) {
  if (!imports.has(accountId)) imports.set(accountId, importLegacy(accountId).catch(() => {}));
  return imports.get(accountId);
}

async function importLegacy(accountId) {
  const markKey = userKey(accountId, USER_KEYS.LISTINGS_IMPORTED);
  if (readJson(markKey, null)) return;
  const records = legacyRecords(accountId);
  // Só o registro: foto fora do https não vai (fica na chave antiga, onde a leitura acha).
  const results = await Promise.allSettled(
    records.map(async (record) => api(accountId, '/produtos/importar', { method: 'POST', body: toApi(record) }))
  );
  const failures = results.filter((result) => result.status === 'rejected').map((result) => result.reason);
  // Rede, 5xx ou sessão vencida: sem marca, tenta de novo na próxima carga. Outro 4xx conta como recusado.
  if (failures.some((error) => isConnectionError(error) || error?.status === 401)) return;
  try {
    writeJson(markKey, { em: nowIso(), total: records.length, recusados: failures.length });
  } catch {
    // sem espaço para a marca: a importação roda de novo na próxima carga, e o servidor não duplica
  }
}

/** Lista do servidor; grava a cópia local e junta as fotos. */
async function loadRecords(accountId) {
  await importOnce(accountId);
  const data = await api(accountId, '/produtos');
  const records = data.produtos.map(fromApi);
  try {
    writeJson(userKey(accountId, USER_KEYS.LISTINGS_CACHE), records);
  } catch {
    // a cópia é só para o painel sem conexão: sem espaço, fica a anterior
  }
  return withPhotos(accountId, records);
}

async function fetchRecord(accountId, id) {
  const produto = await api(accountId, productPath(id)).catch(notFound);
  return withPhotos(accountId, [fromApi(produto)])[0];
}

/**
 * PUT com a versão lida do servidor (`version`). Fotos fora do https vão para a chave local do
 * produto antes do PUT (pode lançar StorageFullError, como antes); se o PUT falhar, a chave volta
 * ao que era. `shownPhotos` são as fotos que o registro já tinha: iguais, a chave não é regravada.
 */
async function saveRecord(accountId, record, version, shownPhotos = []) {
  assertSessionAccount(accountId);
  const key = photosKey(accountId, record.id);
  const fotos = record.fotos ?? [];
  const local = !allHttps(fotos);
  const writeLocal = local && !samePhotos(fotos, shownPhotos);
  const before = writeLocal ? readJson(key, null) : null;
  if (writeLocal) writeJson(key, fotos);
  let produto;
  try {
    // Conta conferida só antes (início da função): depois da resposta, o servidor já gravou e as fotos locais não podem voltar
    produto = await requestJson(productPath(record.id), { method: 'PUT', body: toApi({ ...record, atualizado_em: version }) });
  } catch (error) {
    if (writeLocal) {
      try {
        if (before === null) removeKey(key);
        else writeJson(key, before);
      } catch {
        // sem espaço para voltar: ficam as fotos novas
      }
    }
    throw error;
  }
  if (!local) removeKey(key);
  return withPhotos(accountId, [fromApi(produto)])[0];
}

export async function listListings(accountId) {
  const records = await loadRecords(accountId);
  return records.sort(byUpdatedDesc).map(toListing);
}

/** Cópia salva neste navegador (última lista boa do servidor; sem ela, a chave antiga), para o painel sem conexão. */
export async function listLocalListings(accountId) {
  const cached = readJson(userKey(accountId, USER_KEYS.LISTINGS_CACHE), null);
  const records = Array.isArray(cached) ? cached : legacyRecords(accountId);
  return withPhotos(accountId, records).sort(byUpdatedDesc).map(toListing);
}

export async function getListing(accountId, id) {
  await importOnce(accountId);
  return toListing(await fetchRecord(accountId, id));
}

/**
 * Sincroniza os anúncios com os produtos reais retornados pelo Mercado Livre.
 * Grava (em paralelo) só os que mudaram; 409 é pulado (o próximo sync acerta) e outro erro
 * sobe depois de todos terminarem.
 */
export async function syncListingsWithMercadoLivre(accountId, mlProducts) {
  if (!Array.isArray(mlProducts)) return listListings(accountId);
  const records = await loadRecords(accountId);
  const before = new Map(records.map((record) => [record.id, record]));
  const next = matchMlItems(records, mlProducts);
  const results = await Promise.allSettled(
    next.map(async (record) => {
      const old = before.get(record.id);
      if (old && sameRecord(old, record)) return old;
      return saveRecord(accountId, record, old?.atualizado_em ?? record.atualizado_em, old?.fotos ?? []);
    })
  );
  const failure = results.find((result) => result.status === 'rejected' && result.reason?.status !== 409);
  if (failure) throw failure.reason;
  return results
    .map((result, index) => (result.status === 'fulfilled' ? result.value : before.get(next[index].id)))
    .filter(Boolean)
    .sort(byUpdatedDesc)
    .map(toListing);
}

/** Atualiza um anúncio específico com os dados frescos vindos do Mercado Livre. */
export async function mergeMercadoLivreItem(accountId, id, mlItem) {
  const current = await fetchRecord(accountId, id);
  const updated = applyMlItemToStoreRecord(current, mlItem);
  // Abrir o anúncio não grava nada se o ML não mudou (gravar levaria o anúncio para o topo do painel)
  if (sameRecord(current, updated)) return toListing(current);
  return toListing(await saveRecord(accountId, updated, current.atualizado_em, current.fotos));
}

export async function createListing(accountId, data) {
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
    analise_id: null,
    canais: {},
    ...toStoreFields(data),
    criado_em: now,
    atualizado_em: now
  };
  return toListing(await saveRecord(accountId, anuncio, now));
}

export async function updateListing(accountId, id, patch) {
  const current = await fetchRecord(accountId, id);
  const updated = { ...current, ...toStoreFields(patch) };
  return toListing(await saveRecord(accountId, updated, current.atualizado_em, current.fotos));
}

/** Copia um anúncio. A cópia nasce fora do ar (não publicada), sem vínculo com o item original do ML. */
export async function duplicateListing(accountId, id, { title }) {
  const original = await fetchRecord(accountId, id);
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
  return toListing(await saveRecord(accountId, copy, now));
}

export async function removeListing(accountId, id) {
  await api(accountId, productPath(id), { method: 'DELETE' }).catch(notFound);
  removeKey(photosKey(accountId, id));
}
