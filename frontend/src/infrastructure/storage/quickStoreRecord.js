/**
 * Infraestrutura · Mappers e reconciliadores específicos da QuickStore para o registro local
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

export const QS_CHANNEL = 'quickstore';
const ML_CHANNEL = 'mercado-livre';

export function applyQuickStoreItemToStoreRecord(existing, qsItem) {
  const now = nowIso();
  const closed = isClosedExternalStatus(qsItem.status);
  const httpsPictures = (Array.isArray(qsItem.pictures) ? qsItem.pictures : [])
    .filter((p) => typeof p === 'string' && p.startsWith('https://'))
    .slice(0, 12);
  const pictures = httpsPictures.length
    ? httpsPictures
    : typeof qsItem.thumbnail === 'string' && qsItem.thumbnail.startsWith('https://')
      ? [qsItem.thumbnail]
      : (existing?.fotos ?? []);
  const attributes =
    Array.isArray(qsItem.attributes) && qsItem.attributes.length
      ? qsItem.attributes.map((a) => ({ id: a.id ?? null, nome: a.name ?? a.id ?? '', valor: a.value ?? '' }))
      : (existing?.atributos ?? []);
  const title = String(qsItem.title || existing?.titulo || '').trim();
  const description =
    qsItem.description !== undefined && qsItem.description !== ''
      ? String(qsItem.description)
      : (existing?.descricao ?? '');
  const hasIncomingPrice = qsItem.price !== undefined && qsItem.price !== null;
  const incomingPriceCents = hasIncomingPrice
    ? Math.round(Number(qsItem.price) * 100)
    : (existing?.preco_centavos_qs ?? existing?.preco_centavos ?? 0);
  const otherChannelActive = isChannelActiveInStore(existing?.canais, ML_CHANNEL);
  const existingMlPrice = optionalCents(existing?.preco_centavos_ml);
  const hasDistinctOtherPrice =
    Boolean(existing) &&
    otherChannelActive &&
    ((existingMlPrice !== null && existingMlPrice !== incomingPriceCents) ||
      (existingMlPrice === null &&
        existing?.preco_centavos !== undefined &&
        existing.preco_centavos !== incomingPriceCents));
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
      : (existing?.estoque ?? 0);

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
        (item) =>
          !matched.has(item.id) && !asExternalId(item.qs_item_id) && normalizeTitle(item.titulo) === targetTitle
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

export function qsExternalData(record) {
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

export function qsFromApi(publicacoes) {
  const qs = (publicacoes ?? []).find((publicacao) => publicacao.canal === QS_CHANNEL);
  const qsPrice = optionalCents(qs?.preco_centavos);
  return {
    qs_item_id: qs?.id_externo ?? null,
    qs_permalink: qs?.permalink ?? null,
    qs_categoria_id: qs?.categoria_id ?? null,
    saude_qs: qs?.saude ?? null,
    vendidos_qs: Number(qs?.vendidos ?? 0),
    ...(qsPrice !== null ? { preco_centavos_qs: qsPrice } : {})
  };
}
