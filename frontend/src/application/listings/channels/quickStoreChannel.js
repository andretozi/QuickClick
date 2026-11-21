/**
 * Aplicação · Adaptador do canal QuickStore
 */
import {
  deleteQuickStoreItem,
  fetchQuickStoreItem,
  fetchQuickStoreProducts,
  publishToQuickStore,
  updateQuickStoreItem,
  updateQuickStoreStatus
} from '@/infrastructure/marketplaces/quickStoreService.js';
import { applyQuickStoreItemToStoreRecord, matchQuickStoreItems } from '@/infrastructure/storage/quickStoreRecord.js';
import { clampHealth, safeHttpsUrl } from '@/infrastructure/storage/listingRecord.js';
import {
  mergeChannelItem,
  reconcileListingWithChannel,
  syncListingsWithChannel
} from '@/infrastructure/storage/listingsRepository.js';
import { dataUrlToBlob } from '@/infrastructure/media/imageResizer.js';
import { LISTING_STATUS, PRIMARY_CHANNEL, QUICKSTORE_CHANNEL, channelStatus } from '@/domain/listings/listingRules.js';

export const quickStoreChannel = {
  slug: QUICKSTORE_CHANNEL,
  name: 'QuickStore',
  disconnectedCode: 'quickstore_desconectada',

  getItemId(listing) {
    return listing?.qsItemId ?? null;
  },

  getPriceCents(listing) {
    return listing?.qsPriceCents ?? listing?.priceCents ?? 0;
  },

  buildPayload(listing, overrides = {}) {
    const orderedPhotos = overrides.orderedPhotos ?? listing.photos ?? [];
    const keptPhotos =
      overrides.keptPhotos ?? orderedPhotos.filter((p) => String(p).startsWith('https://')).slice(0, 12);
    const photoBlobs =
      overrides.photoBlobs ??
      orderedPhotos
        .filter((p) => String(p).startsWith('data:'))
        .map((p) => dataUrlToBlob(p));
    return {
      payload: {
        ...(listing.id ? { id: listing.id } : {}),
        title: overrides.title ?? listing.title,
        description: overrides.description ?? listing.description,
        priceCents: overrides.priceCents ?? (listing.qsPriceCents ?? listing.priceCents),
        stock: overrides.stock !== undefined ? overrides.stock : Math.max(1, Number(listing.stock) || 1),
        condition: overrides.condition ?? listing.condition,
        attributes: overrides.attributes ?? listing.attributes,
        analysisId: overrides.analysisId ?? listing.analysisId ?? null,
        mlCategoryId: overrides.mlCategoryId ?? listing.qsCategoryId ?? listing.mlCategoryId ?? null,
        keptPhotos
      },
      photoBlobs
    };
  },

  async syncAll(accountId) {
    const products = await fetchQuickStoreProducts();
    return syncListingsWithChannel(accountId, products, matchQuickStoreItems);
  },

  async reconcileIfNeeded(accountId, listing) {
    if (!listing || this.getItemId(listing)) return listing;
    const products = await fetchQuickStoreProducts();
    return reconcileListingWithChannel(accountId, listing.id, products, matchQuickStoreItems);
  },

  async syncOne(accountId, listing) {
    const itemId = this.getItemId(listing);
    if (!itemId) return listing;
    const fresh = await fetchQuickStoreItem(itemId);
    return mergeChannelItem(accountId, listing.id, fresh, applyQuickStoreItemToStoreRecord);
  },

  async publish(payload, photoBlobs = []) {
    try {
      return await publishToQuickStore(payload, photoBlobs);
    } catch (error) {
      if (error && typeof error === 'object' && !error.channel) error.channel = this.slug;
      throw error;
    }
  },

  async update(itemId, payload, photoBlobs = []) {
    try {
      return await updateQuickStoreItem(itemId, payload, photoBlobs);
    } catch (error) {
      if (error && typeof error === 'object' && !error.channel) error.channel = this.slug;
      throw error;
    }
  },

  async setStatus(accountId, listingId, itemId, targetStatus) {
    try {
      const fresh = await updateQuickStoreStatus(itemId, targetStatus);
      if (!accountId || !listingId) return fresh;
      return await mergeChannelItem(accountId, listingId, fresh, applyQuickStoreItemToStoreRecord);
    } catch (error) {
      if (error && typeof error === 'object' && !error.channel) error.channel = this.slug;
      throw error;
    }
  },

  async remove(itemId) {
    try {
      return await deleteQuickStoreItem(itemId);
    } catch (error) {
      if (error && typeof error === 'object' && !error.channel) error.channel = this.slug;
      throw error;
    }
  },

  toPublishedPatch(listing, published, targetStatus = LISTING_STATUS.PUBLISHED) {
    const existingHttps = (Array.isArray(listing?.photos) ? listing.photos : [])
      .map((url) => safeHttpsUrl(url))
      .filter(Boolean);
    const publishedHttps = (Array.isArray(published?.photos) ? published.photos : [])
      .map((url) => safeHttpsUrl(url))
      .filter(Boolean)
      .slice(0, 12);
    return {
      qsItemId: published.id,
      qsPermalink: safeHttpsUrl(published.permalink),
      qsCategoryId: published.categoryId ?? listing?.qsCategoryId ?? listing?.mlCategoryId ?? null,
      ...(existingHttps.length === 0 && publishedHttps.length > 0
        ? { photos: publishedHttps, coverIndex: 0 }
        : {}),
      channels: { ...(listing?.channels ?? {}), [QUICKSTORE_CHANNEL]: targetStatus }
    };
  },

  toUpdatedPatch(listing, qsUpdated, fallbackPhotos = [], includePhotos = true) {
    const qsHttpsPhotos = (Array.isArray(qsUpdated?.pictures) ? qsUpdated.pictures : [])
      .filter((p) => typeof p === 'string' && p.startsWith('https://'))
      .slice(0, 12);
    return {
      qsItemId: qsUpdated?.id ?? listing?.qsItemId ?? null,
      qsPermalink: safeHttpsUrl(qsUpdated?.permalink ?? listing?.qsPermalink),
      qsCategoryId: qsUpdated?.category_id ?? listing?.qsCategoryId ?? listing?.mlCategoryId ?? null,
      qsHealth: clampHealth(qsUpdated?.health ?? listing?.qsHealth),
      qsSoldQuantity: qsUpdated?.sold_quantity ?? listing?.qsSoldQuantity ?? 0,
      ...(includePhotos && qsHttpsPhotos.length ? { photos: qsHttpsPhotos, coverIndex: 0 } : {})
    };
  },

  toClearedPatch(listing) {
    return {
      qsItemId: null,
      qsPermalink: null,
      qsHealth: null,
      channels: { ...(listing?.channels ?? {}), [QUICKSTORE_CHANNEL]: LISTING_STATUS.UNPUBLISHED }
    };
  },

  buildPriceFieldsWhenScoped(original, priceCents) {
    const mlActive =
      Boolean(original?.mlItemId) || channelStatus(original, PRIMARY_CHANNEL) !== LISTING_STATUS.UNPUBLISHED;
    const preservedMlPrice = original?.mlPriceCents ?? (mlActive ? original?.priceCents : null);
    return {
      priceCents: mlActive ? (original?.mlPriceCents ?? original?.priceCents) : priceCents,
      ...(preservedMlPrice !== null && preservedMlPrice !== undefined ? { mlPriceCents: preservedMlPrice } : {}),
      qsPriceCents: priceCents
    };
  }
};
