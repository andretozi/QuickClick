/**
 * Aplicação · Adaptador do canal Mercado Livre
 */
import {
  deleteMercadoLivreItem,
  fetchMercadoLivreItem,
  fetchMercadoLivreProducts,
  publishToMercadoLivre,
  updateMercadoLivreItem,
  updateMercadoLivreStatus
} from '@/infrastructure/marketplaces/mercadoLivreService.js';
import { applyMlItemToStoreRecord, matchMlItems } from '@/infrastructure/storage/mercadoLivreRecord.js';
import { clampHealth, safeHttpsUrl } from '@/infrastructure/storage/listingRecord.js';
import { mergeChannelItem, syncListingsWithChannel } from '@/infrastructure/storage/listingsRepository.js';
import { dataUrlToBlob } from '@/infrastructure/media/imageResizer.js';
import { LISTING_STATUS, PRIMARY_CHANNEL, QUICKSTORE_CHANNEL, channelStatus } from '@/domain/listings/listingRules.js';

export const mercadoLivreChannel = {
  slug: PRIMARY_CHANNEL,
  name: 'Mercado Livre',
  disconnectedCode: 'mercado_livre_desconectado',

  getItemId(listing) {
    return listing?.mlItemId ?? null;
  },

  getPriceCents(listing) {
    return listing?.mlPriceCents ?? listing?.priceCents ?? 0;
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
        priceCents: overrides.priceCents ?? (listing.mlPriceCents ?? listing.priceCents),
        stock: overrides.stock !== undefined ? overrides.stock : Math.max(1, Number(listing.stock) || 1),
        condition: overrides.condition ?? listing.condition,
        attributes: overrides.attributes ?? listing.attributes,
        analysisId: overrides.analysisId ?? listing.analysisId ?? null,
        mlCategoryId: overrides.mlCategoryId ?? listing.mlCategoryId ?? null,
        keptPhotos
      },
      photoBlobs
    };
  },

  async syncAll(accountId) {
    const products = await fetchMercadoLivreProducts();
    return syncListingsWithChannel(accountId, products, matchMlItems);
  },

  async reconcileIfNeeded(accountId, listing) {
    return listing;
  },

  async syncOne(accountId, listing) {
    const itemId = this.getItemId(listing);
    if (!itemId) return listing;
    const fresh = await fetchMercadoLivreItem(itemId);
    return mergeChannelItem(accountId, listing.id, fresh, applyMlItemToStoreRecord);
  },

  async publish(payload, photoBlobs = []) {
    try {
      return await publishToMercadoLivre(payload, photoBlobs);
    } catch (error) {
      if (error && typeof error === 'object' && !error.channel) error.channel = this.slug;
      throw error;
    }
  },

  async update(itemId, payload, photoBlobs = []) {
    try {
      return await updateMercadoLivreItem(itemId, payload, photoBlobs);
    } catch (error) {
      if (error && typeof error === 'object' && !error.channel) error.channel = this.slug;
      throw error;
    }
  },

  async setStatus(accountId, listingId, itemId, targetStatus) {
    try {
      const fresh = await updateMercadoLivreStatus(itemId, targetStatus);
      if (!accountId || !listingId) return fresh;
      return await mergeChannelItem(accountId, listingId, fresh, applyMlItemToStoreRecord);
    } catch (error) {
      if (error && typeof error === 'object' && !error.channel) error.channel = this.slug;
      throw error;
    }
  },

  async remove(itemId) {
    try {
      return await deleteMercadoLivreItem(itemId);
    } catch (error) {
      if (error && typeof error === 'object' && !error.channel) error.channel = this.slug;
      throw error;
    }
  },

  toPublishedPatch(listing, published, targetStatus = LISTING_STATUS.PUBLISHED) {
    return {
      mlItemId: published.id,
      permalink: safeHttpsUrl(published.permalink),
      mlCategoryId: published.categoryId ?? listing?.mlCategoryId ?? null,
      channels: { ...(listing?.channels ?? {}), [PRIMARY_CHANNEL]: targetStatus }
    };
  },

  toUpdatedPatch(listing, mlUpdated, fallbackPhotos = []) {
    const mlHttpsPhotos = (Array.isArray(mlUpdated?.pictures) ? mlUpdated.pictures : [])
      .filter((p) => typeof p === 'string' && p.startsWith('https://'))
      .slice(0, 12);
    return {
      mlItemId: mlUpdated?.id ?? listing?.mlItemId ?? null,
      permalink: safeHttpsUrl(mlUpdated?.permalink ?? listing?.permalink),
      mlCategoryId: mlUpdated?.category_id ?? listing?.mlCategoryId ?? null,
      health: clampHealth(mlUpdated?.health ?? listing?.health ?? listing?.saudeMl),
      mlSoldQuantity: mlUpdated?.sold_quantity ?? listing?.mlSoldQuantity ?? listing?.soldQuantity ?? 0,
      photos: mlHttpsPhotos.length ? mlHttpsPhotos : fallbackPhotos.slice(0, 12),
      coverIndex: 0
    };
  },

  toClearedPatch(listing) {
    return {
      mlItemId: null,
      permalink: null,
      health: null,
      channels: { ...(listing?.channels ?? {}), [PRIMARY_CHANNEL]: LISTING_STATUS.UNPUBLISHED }
    };
  },

  buildPriceFieldsWhenScoped(original, priceCents) {
    const qsActive =
      Boolean(original?.qsItemId) || channelStatus(original, QUICKSTORE_CHANNEL) !== LISTING_STATUS.UNPUBLISHED;
    const preservedQsPrice = original?.qsPriceCents ?? (qsActive ? original?.priceCents : null);
    return {
      priceCents,
      mlPriceCents: priceCents,
      ...(preservedQsPrice !== null && preservedQsPrice !== undefined ? { qsPriceCents: preservedQsPrice } : {})
    };
  }
};
