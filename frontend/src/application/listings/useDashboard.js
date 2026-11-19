import { useCallback, useEffect, useMemo, useState } from 'react';
import useMountedRef from '@/application/ui/useMountedRef.js';
import useSession from '@/application/session/useSession.js';
import { dismissWelcome } from '@/application/session/sessionStore.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import {
  duplicateListing,
  listListings,
  listLocalListings,
  mergeMercadoLivreItem,
  mergeQuickStoreItem,
  removeListing,
  syncListingsWithMercadoLivre,
  syncListingsWithQuickStore,
  updateListing
} from '@/infrastructure/storage/listingsRepository.js';
import {
  fetchConnectedMarketplaces,
  fetchMarketplaceProducts
} from '@/infrastructure/marketplaces/marketplacesService.js';
import {
  deleteMercadoLivreItem,
  deleteQuickStoreItem,
  publishToMercadoLivre,
  publishToQuickStore,
  updateMercadoLivreStatus,
  updateQuickStoreStatus
} from '@/infrastructure/ai/iaService.js';
import { dataUrlToBlob } from '@/infrastructure/media/imageResizer.js';
import { currentHour } from '@/infrastructure/browser/events.js';
import {
  LISTING_STATUS,
  PRIMARY_CHANNEL,
  QUICKSTORE_CHANNEL,
  channelStatus,
  copyTitle,
  filterListings,
  listingStatus,
  sortListings,
  summarizeListings
} from '@/domain/listings/listingRules.js';
import { LISTINGS_PANEL } from '@/domain/content/dashboardContent.js';
import { aiErrorText } from '@/domain/content/listingContent.js';

export const DASHBOARD_TABS = { LISTINGS: 'listings', INSIGHTS: 'insights' };

const DEFAULT_FILTERS = { query: '', status: 'all', sort: 'recent' };

/** Rede fora ou servidor com erro (5xx): o painel mostra a cópia salva no navegador. */
const isConnectionError = (error) => error?.status === 0 || error?.status >= 500 || error?.code === 'sem_conexao';

function buildPublishInputs(listing) {
  const orderedPhotos = listing.photos ?? [];
  const keptPhotos = orderedPhotos.filter((p) => String(p).startsWith('https://'));
  const photoBlobs = orderedPhotos
    .filter((p) => String(p).startsWith('data:'))
    .map((p) => dataUrlToBlob(p));
  return {
    payload: {
      title: listing.title,
      description: listing.description,
      priceCents: listing.priceCents,
      stock: Math.max(1, Number(listing.stock) || 1),
      condition: listing.condition,
      attributes: listing.attributes,
      mlCategoryId: listing.mlCategoryId ?? listing.qsCategoryId,
      keptPhotos
    },
    photoBlobs
  };
}

/**
 * Aplicação · Caso de uso "painel do vendedor".
 *
 * Carrega os anúncios e as conexões da conta logada, sincroniza os dados reais
 * com o Mercado Livre e a QuickStore, calcula os números do topo, filtra e ordena a lista e cuida
 * das ações de cada anúncio (pausar, reativar, publicar em cada canal, duplicar e excluir com confirmação).
 */
export default function useDashboard() {
  const { account, welcome } = useSession();
  const accountId = account?.id;
  const [data, setData] = useState({ status: 'loading', listings: [], connections: [], offline: false });
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [tab, setTab] = useState(DASHBOARD_TABS.LISTINGS);
  const [busyId, setBusyId] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [pendingRemoval, setPendingRemoval] = useState(null);
  const [removing, setRemoving] = useState(false);
  const [hour] = useState(currentHour);
  const mounted = useMountedRef();

  const syncAllConnected = useCallback(
    async (connectionsList) => {
      if (!accountId) return null;
      const mlConnected = connectionsList.some((connection) => connection.slug === PRIMARY_CHANNEL);
      const qsConnected = connectionsList.some((connection) => connection.slug === QUICKSTORE_CHANNEL);
      let latest = null;
      if (mlConnected) {
        try {
          const mlProducts = await fetchMarketplaceProducts(PRIMARY_CHANNEL);
          if (!mounted.current) return null;
          latest = await syncListingsWithMercadoLivre(accountId, mlProducts);
        } catch {
          // Mantém a lista atual se o Mercado Livre não responder
        }
      }
      if (qsConnected) {
        try {
          const qsProducts = await fetchMarketplaceProducts(QUICKSTORE_CHANNEL);
          if (!mounted.current) return null;
          latest = await syncListingsWithQuickStore(accountId, qsProducts);
        } catch {
          // Mantém a lista atual se a QuickStore não responder
        }
      }
      return latest;
    },
    [accountId, mounted]
  );

  const load = useCallback(async () => {
    if (!accountId) return;
    setData((current) => ({ ...current, status: 'loading' }));
    try {
      const [{ listings, offline }, connections] = await Promise.all([
        listListings(accountId).then(
          (items) => ({ listings: items, offline: false }),
          async (error) => {
            if (!isConnectionError(error)) throw error;
            return { listings: await listLocalListings(accountId), offline: true };
          }
        ),
        fetchConnectedMarketplaces().catch(() => [])
      ]);
      if (!mounted.current) return;
      setData({ status: 'ready', listings, connections, offline });
      // Sem o servidor, o sync não roda: gravaria por cima de uma cópia que pode estar desatualizada.
      if (offline) return;

      const hasConnected = connections.some(
        (connection) => connection.slug === PRIMARY_CHANNEL || connection.slug === QUICKSTORE_CHANNEL
      );
      if (hasConnected) {
        setSyncing(true);
        try {
          const synced = await syncAllConnected(connections);
          if (mounted.current && synced) {
            setData((current) => ({ ...current, listings: synced }));
          }
        } finally {
          if (mounted.current) setSyncing(false);
        }
      }
    } catch {
      if (mounted.current) setData((current) => ({ ...current, status: 'error' }));
    }
  }, [accountId, mounted, syncAllConnected]);

  useEffect(() => {
    load();
  }, [load]);

  // Sincroniza automaticamente quando a aba do navegador volta a ficar ativa (ex.: após mexer na QuickStore)
  useEffect(() => {
    if (!accountId || data.offline) return undefined;
    const onFocus = async () => {
      if (document.visibilityState && document.visibilityState !== 'visible') return;
      try {
        const synced = await syncAllConnected(data.connections);
        if (mounted.current && synced) {
          setData((current) => ({ ...current, listings: synced }));
        }
      } catch {
        // silencioso no foco
      }
    };
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [accountId, data.connections, data.offline, mounted, syncAllConnected]);

  const summary = useMemo(() => summarizeListings(data.listings), [data.listings]);
  const visibleListings = useMemo(
    () => sortListings(filterListings(data.listings, filters), filters.sort),
    [data.listings, filters]
  );
  const mercadoLivreConnected = data.connections.some((connection) => connection.slug === PRIMARY_CHANNEL);
  const quickStoreConnected = data.connections.some((connection) => connection.slug === QUICKSTORE_CHANNEL);

  const setFilter = useCallback((event) => {
    const { name, value } = event.target;
    setFilters((current) => ({ ...current, [name]: value }));
  }, []);

  const clearFilters = useCallback(() => setFilters(DEFAULT_FILTERS), []);

  const replaceListing = useCallback((updated) => {
    setData((current) => ({
      ...current,
      listings: current.listings.map((listing) => (listing.id === updated.id ? updated : listing))
    }));
  }, []);

  const failed = useCallback((error) => {
    const message = error?.code ? aiErrorText(error.code, error.userMessage) : LISTINGS_PANEL.toasts.error;
    showToast({ tone: TOAST_TONES.ERROR, ...message });
  }, []);

  const syncNow = useCallback(async () => {
    if (!accountId || (!mercadoLivreConnected && !quickStoreConnected) || syncing) return;
    setSyncing(true);
    try {
      let synced = null;
      if (mercadoLivreConnected) {
        const mlProducts = await fetchMarketplaceProducts(PRIMARY_CHANNEL);
        synced = await syncListingsWithMercadoLivre(accountId, mlProducts);
      }
      if (quickStoreConnected) {
        const qsProducts = await fetchMarketplaceProducts(QUICKSTORE_CHANNEL);
        synced = await syncListingsWithQuickStore(accountId, qsProducts);
      }
      if (!mounted.current) return;
      if (synced) setData((current) => ({ ...current, listings: synced }));
      showToast({ tone: TOAST_TONES.SUCCESS, ...LISTINGS_PANEL.toasts.synced });
    } catch (error) {
      if (mounted.current) failed(error);
    } finally {
      if (mounted.current) setSyncing(false);
    }
  }, [accountId, failed, mercadoLivreConnected, quickStoreConnected, mounted, syncing]);

  /** Publica, pausa ou reativa um produto em um canal específico ('mercado-livre' ou 'quickstore'). */
  const toggleChannelStatus = useCallback(
    async (listing, channel = PRIMARY_CHANNEL) => {
      const isQs = channel === QUICKSTORE_CHANNEL;
      const connected = isQs ? quickStoreConnected : mercadoLivreConnected;
      if (!connected) return;

      const currentStatus = channelStatus(listing, channel);
      const itemId = isQs ? listing.qsItemId : listing.mlItemId;
      const next =
        currentStatus === LISTING_STATUS.PUBLISHED
          ? { status: LISTING_STATUS.PAUSED, toast: LISTINGS_PANEL.toasts.paused }
          : currentStatus === LISTING_STATUS.PAUSED
            ? { status: LISTING_STATUS.PUBLISHED, toast: LISTINGS_PANEL.toasts.resumed }
            : {
                status: LISTING_STATUS.PUBLISHED,
                toast: isQs ? LISTINGS_PANEL.toasts.publishedQs : LISTINGS_PANEL.toasts.publishedMl
              };

      setBusyId(listing.id);
      try {
        let updated;
        const shouldCreateFresh = !itemId || currentStatus === LISTING_STATUS.UNPUBLISHED;
        if (!shouldCreateFresh) {
          try {
            if (isQs) {
              const qsItem = await updateQuickStoreStatus(itemId, next.status);
              updated = await mergeQuickStoreItem(accountId, listing.id, qsItem);
            } else {
              const mlItem = await updateMercadoLivreStatus(itemId, next.status);
              updated = await mergeMercadoLivreItem(accountId, listing.id, mlItem);
            }
          } catch (error) {
            // Se o item antigo estava fechado ou excluído no canal, publica um novo anúncio ativo
            if (next.status === LISTING_STATUS.PUBLISHED && (error?.code === 'anuncio_nao_encontrado' || error?.code === 'publicacao_recusada')) {
              const { payload, photoBlobs } = buildPublishInputs(listing);
              const published = isQs
                ? await publishToQuickStore(payload, photoBlobs)
                : await publishToMercadoLivre(payload, photoBlobs);
              updated = await updateListing(
                accountId,
                listing.id,
                isQs
                  ? {
                      qsItemId: published.id,
                      qsPermalink: published.permalink,
                      qsCategoryId: published.categoryId ?? listing.qsCategoryId ?? listing.mlCategoryId,
                      channels: { ...listing.channels, [QUICKSTORE_CHANNEL]: LISTING_STATUS.PUBLISHED }
                    }
                  : {
                      mlItemId: published.id,
                      permalink: published.permalink,
                      mlCategoryId: published.categoryId ?? listing.mlCategoryId,
                      channels: { ...listing.channels, [PRIMARY_CHANNEL]: LISTING_STATUS.PUBLISHED }
                    }
              );
            } else {
              throw error;
            }
          }
        } else if (next.status === LISTING_STATUS.PUBLISHED) {
          const { payload, photoBlobs } = buildPublishInputs(listing);
          const published = isQs
            ? await publishToQuickStore(payload, photoBlobs)
            : await publishToMercadoLivre(payload, photoBlobs);
          updated = await updateListing(
            accountId,
            listing.id,
            isQs
              ? {
                  qsItemId: published.id,
                  qsPermalink: published.permalink,
                  qsCategoryId: published.categoryId ?? listing.qsCategoryId ?? listing.mlCategoryId,
                  channels: { ...listing.channels, [QUICKSTORE_CHANNEL]: next.status }
                }
              : {
                  mlItemId: published.id,
                  permalink: published.permalink,
                  mlCategoryId: published.categoryId ?? listing.mlCategoryId,
                  channels: { ...listing.channels, [PRIMARY_CHANNEL]: next.status }
                }
          );
        } else {
          updated = await updateListing(accountId, listing.id, {
            channels: { ...listing.channels, [channel]: next.status }
          });
        }
        if (!mounted.current) return;
        replaceListing(updated);
        showToast({ tone: TOAST_TONES.SUCCESS, ...next.toast });
      } catch (error) {
        if (mounted.current) failed(error);
      } finally {
        if (mounted.current) setBusyId(null);
      }
    },
    [accountId, failed, mercadoLivreConnected, quickStoreConnected, replaceListing, mounted]
  );

  /** Pausar (publicado), reativar (pausado) ou publicar (standby) nos canais conectados. */
  const toggleStatus = useCallback(
    async (listing) => {
      const mlStatus = channelStatus(listing, PRIMARY_CHANNEL);
      const qsStatus = channelStatus(listing, QUICKSTORE_CHANNEL);
      const targetChannel =
        mlStatus === LISTING_STATUS.UNPUBLISHED && qsStatus !== LISTING_STATUS.UNPUBLISHED
          ? QUICKSTORE_CHANNEL
          : PRIMARY_CHANNEL;
      await toggleChannelStatus(listing, targetChannel);
    },
    [toggleChannelStatus]
  );

  const duplicate = useCallback(
    async (listing) => {
      setBusyId(listing.id);
      try {
        const copy = await duplicateListing(accountId, listing.id, {
          title: copyTitle(listing.title, LISTINGS_PANEL.copySuffix)
        });
        if (!mounted.current) return;
        setData((current) => ({ ...current, listings: [copy, ...current.listings] }));
        showToast({ tone: TOAST_TONES.SUCCESS, ...LISTINGS_PANEL.toasts.duplicated });
      } catch (error) {
        if (mounted.current) failed(error);
      } finally {
        if (mounted.current) setBusyId(null);
      }
    },
    [accountId, failed, mounted]
  );

  const requestRemoval = useCallback((listing) => setPendingRemoval(listing), []);
  const cancelRemoval = useCallback(() => {
    if (!removing) setPendingRemoval(null);
  }, [removing]);

  const confirmRemoval = useCallback(async () => {
    if (!pendingRemoval) return;
    setRemoving(true);
    try {
      if (pendingRemoval.mlItemId) {
        try {
          await deleteMercadoLivreItem(pendingRemoval.mlItemId);
        } catch (error) {
          if (error?.code !== 'anuncio_nao_encontrado') throw error;
        }
      }
      if (pendingRemoval.qsItemId) {
        try {
          await deleteQuickStoreItem(pendingRemoval.qsItemId);
        } catch (error) {
          if (error?.code !== 'anuncio_nao_encontrado') throw error;
        }
      }
      await removeListing(accountId, pendingRemoval.id);
      if (!mounted.current) return;
      setData((current) => ({
        ...current,
        listings: current.listings.filter((listing) => listing.id !== pendingRemoval.id)
      }));
      setPendingRemoval(null);
      showToast({ tone: TOAST_TONES.SUCCESS, ...LISTINGS_PANEL.toasts.removed });
    } catch (error) {
      if (mounted.current) failed(error);
    } finally {
      if (mounted.current) setRemoving(false);
    }
  }, [accountId, failed, pendingRemoval, mounted]);

  return {
    account,
    hour,
    status: data.status,
    offline: data.offline,
    listings: data.listings,
    connections: data.connections,
    mercadoLivreConnected,
    quickStoreConnected,
    summary,
    visibleListings,
    filters,
    setFilter,
    clearFilters,
    tab,
    setTab,
    busyId,
    syncing,
    syncNow,
    toggleStatus,
    toggleChannelStatus,
    duplicate,
    pendingRemoval,
    removing,
    requestRemoval,
    cancelRemoval,
    confirmRemoval,
    retry: load,
    welcome,
    dismissWelcome
  };
}
