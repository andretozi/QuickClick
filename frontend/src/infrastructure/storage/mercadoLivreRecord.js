/**
 * Infraestrutura · Mappers e reconciliadores específicos do Mercado Livre para o registro local
 */
import { newId, nowIso } from './localStore.js';
import {
  asExternalId,
  clampHealth,
  inferCategoryFromTitle,
  isChannelActiveInStore,
  isClosedExternalStatus,
  mlStatusToStore,
  normalizeTitle,
  optionalCents,
  safeHttpsUrl
} from './listingRecord.js';

export const ML_CHANNEL = 'mercado-livre';
const QS_CHANNEL = 'quickstore';

export function applyMlItemToStoreRecord(existing, mlItem) {
  const now = nowIso();
  const closed = isClosedExternalStatus(mlItem.status);
  const pictures =
    Array.isArray(mlItem.pictures) && mlItem.pictures.length
      ? mlItem.pictures.slice(0, 12) // o servidor aceita até 12 fotos; acima disso o sync daria 422
      : mlItem.thumbnail
        ? [mlItem.thumbnail]
        : (existing?.fotos ?? []);
  const attributes =
    Array.isArray(mlItem.attributes) && mlItem.attributes.length
      ? mlItem.attributes.map((a) => ({ id: a.id ?? null, nome: a.name ?? a.id ?? '', valor: a.value ?? '' }))
      : (existing?.atributos ?? []);
  const title = String(mlItem.title || existing?.titulo || '').trim();
  const description =
    mlItem.description !== undefined && mlItem.description !== ''
      ? String(mlItem.description)
      : (existing?.descricao ?? '');
  const hasIncomingPrice = mlItem.price !== undefined && mlItem.price !== null;
  const incomingPriceCents = hasIncomingPrice
    ? Math.round(Number(mlItem.price) * 100)
    : (existing?.preco_centavos_ml ?? existing?.preco_centavos ?? 0);
  const otherChannelActive = isChannelActiveInStore(existing?.canais, QS_CHANNEL);
  const existingQsPrice = optionalCents(existing?.preco_centavos_qs);
  const hasDistinctOtherPrice =
    Boolean(existing) &&
    otherChannelActive &&
    ((existingQsPrice !== null && existingQsPrice !== incomingPriceCents) ||
      (existingQsPrice === null &&
        existing?.preco_centavos !== undefined &&
        existing.preco_centavos !== incomingPriceCents));
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
      : (existing?.estoque ?? 0);

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
        (item) =>
          !matched.has(item.id) && !asExternalId(item.ml_item_id) && normalizeTitle(item.titulo) === targetTitle
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

export function mlExternalData(record) {
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

export function mlFromApi(publicacoes) {
  const ml = (publicacoes ?? []).find((publicacao) => publicacao.canal === ML_CHANNEL);
  const mlPrice = optionalCents(ml?.preco_centavos);
  return {
    ml_item_id: ml?.id_externo ?? null,
    permalink: ml?.permalink ?? null,
    ml_categoria_id: ml?.categoria_id ?? null,
    saude_ml: ml?.saude ?? null,
    vendidos: Number(ml?.vendidos ?? 0),
    ...(mlPrice !== null ? { preco_centavos_ml: mlPrice } : {})
  };
}
