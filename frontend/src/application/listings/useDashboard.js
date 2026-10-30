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
  removeListing,
  syncListingsWithMercadoLivre,
  updateListing
} from '@/infrastructure/storage/listingsRepository.js';
import {
  fetchConnectedMarketplaces,
  fetchMarketplaceProducts
} from '@/infrastructure/marketplaces/marketplacesService.js';
import {
  deleteMercadoLivreItem,
  publishToMercadoLivre,
  updateMercadoLivreStatus
} from '@/infrastructure/ai/iaService.js';
import { dataUrlToBlob } from '@/infrastructure/media/imageResizer.js';
import { currentHour } from '@/infrastructure/browser/events.js';
import {
  LISTING_STATUS,
  PRIMARY_CHANNEL,
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

/**
 * Aplicação · Caso de uso "painel do vendedor".
 *
 * Carrega os anúncios e as conexões da conta logada, sincroniza os dados reais
 * com o Mercado Livre, calcula os números do topo, filtra e ordena a lista e cuida
 * das ações de cada anúncio (pausar, reativar, publicar, duplicar e excluir com confirmação).
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

      const mlConnected = connections.some((connection) => connection.slug === PRIMARY_CHANNEL);
      if (mlConnected) {
        setSyncing(true);
        try {
          const mlProducts = await fetchMarketplaceProducts(PRIMARY_CHANNEL);
          if (!mounted.current) return;
          const synced = await syncListingsWithMercadoLivre(accountId, mlProducts);
          if (mounted.current) {
            setData((current) => ({ ...current, listings: synced }));
          }
        } catch {
          // Sem internet ou token expirado: mantém a lista já carregada
        } finally {
          if (mounted.current) setSyncing(false);
        }
      }
    } catch {
      if (mounted.current) setData((current) => ({ ...current, status: 'error' }));
    }
  }, [accountId, mounted]);

  useEffect(() => {
    load();
  }, [load]);

  const summary = useMemo(() => summarizeListings(data.listings), [data.listings]);
  const visibleListings = useMemo(
    () => sortListings(filterListings(data.listings, filters), filters.sort),
    [data.listings, filters]
  );
  const mercadoLivreConnected = data.connections.some((connection) => connection.slug === PRIMARY_CHANNEL);

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
    if (!accountId || !mercadoLivreConnected || syncing) return;
    setSyncing(true);
    try {
      const mlProducts = await fetchMarketplaceProducts(PRIMARY_CHANNEL);
      const synced = await syncListingsWithMercadoLivre(accountId, mlProducts);
      if (!mounted.current) return;
      setData((current) => ({ ...current, listings: synced }));
      showToast({ tone: TOAST_TONES.SUCCESS, ...LISTINGS_PANEL.toasts.synced });
    } catch (error) {
      if (mounted.current) failed(error);
    } finally {
      if (mounted.current) setSyncing(false);
    }
  }, [accountId, failed, mercadoLivreConnected, mounted, syncing]);

  /** Pausar (publicado), reativar (pausado) ou publicar (fora do ar, com o Mercado Livre conectado). */
  const toggleStatus = useCallback(
    async (listing) => {
      const status = listingStatus(listing);
      const next =
        status === LISTING_STATUS.PUBLISHED
          ? { status: LISTING_STATUS.PAUSED, toast: LISTINGS_PANEL.toasts.paused }
          : status === LISTING_STATUS.PAUSED
            ? { status: LISTING_STATUS.PUBLISHED, toast: LISTINGS_PANEL.toasts.resumed }
            : { status: LISTING_STATUS.PUBLISHED, toast: LISTINGS_PANEL.toasts.published };
      if (!mercadoLivreConnected) return;
      setBusyId(listing.id);
      try {
        let updated;
        if (listing.mlItemId) {
          const mlItem = await updateMercadoLivreStatus(listing.mlItemId, next.status);
          updated = await mergeMercadoLivreItem(accountId, listing.id, mlItem);
        } else if (next.status === LISTING_STATUS.PUBLISHED) {
          const orderedPhotos = listing.photos ?? [];
          const keptPhotos = orderedPhotos.filter((p) => String(p).startsWith('https://'));
          const photoBlobs = orderedPhotos
            .filter((p) => String(p).startsWith('data:'))
            .map((p) => dataUrlToBlob(p));
          const published = await publishToMercadoLivre(
            {
              title: listing.title,
              description: listing.description,
              priceCents: listing.priceCents,
              stock: Math.max(1, Number(listing.stock) || 1),
              condition: listing.condition,
              attributes: listing.attributes,
              mlCategoryId: listing.mlCategoryId,
              keptPhotos
            },
            photoBlobs
          );
          updated = await updateListing(accountId, listing.id, {
            mlItemId: published.id,
            permalink: published.permalink,
            mlCategoryId: published.categoryId ?? listing.mlCategoryId,
            channels: { ...listing.channels, [PRIMARY_CHANNEL]: next.status }
          });
        } else {
          updated = await updateListing(accountId, listing.id, {
            channels: { ...listing.channels, [PRIMARY_CHANNEL]: next.status }
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
    [accountId, failed, mercadoLivreConnected, replaceListing, mounted]
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
