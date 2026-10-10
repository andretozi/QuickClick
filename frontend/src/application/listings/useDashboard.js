import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import useSession from '@/application/session/useSession.js';
import { dismissWelcome } from '@/application/session/sessionStore.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import {
  duplicateListing,
  listListings,
  removeListing,
  updateListing
} from '@/infrastructure/storage/listingsRepository.js';
import { listConnections } from '@/infrastructure/storage/connectionsRepository.js';
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

export const DASHBOARD_TABS = { LISTINGS: 'listings', INSIGHTS: 'insights' };

const DEFAULT_FILTERS = { query: '', status: 'all', sort: 'recent' };

/**
 * Aplicação · Caso de uso "painel do vendedor".
 *
 * Carrega os anúncios e as conexões da conta logada, calcula os números do topo,
 * filtra e ordena a lista e cuida das ações de cada anúncio (pausar, reativar,
 * publicar, duplicar e excluir com confirmação). A tela só desenha o que este hook devolve.
 */
export default function useDashboard() {
  const { account, welcome } = useSession();
  const accountId = account?.id;
  const [data, setData] = useState({ status: 'loading', listings: [], connections: [] });
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [tab, setTab] = useState(DASHBOARD_TABS.LISTINGS);
  const [busyId, setBusyId] = useState(null);
  const [pendingRemoval, setPendingRemoval] = useState(null);
  const [removing, setRemoving] = useState(false);
  const [hour] = useState(currentHour);
  const mounted = useRef(true);

  const load = useCallback(async () => {
    if (!accountId) return;
    setData((current) => ({ ...current, status: 'loading' }));
    try {
      const [listings, connections] = await Promise.all([listListings(accountId), listConnections(accountId)]);
      if (mounted.current) setData({ status: 'ready', listings, connections });
    } catch {
      if (mounted.current) setData((current) => ({ ...current, status: 'error' }));
    }
  }, [accountId]);

  useEffect(() => {
    mounted.current = true;
    load();
    return () => {
      mounted.current = false;
    };
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

  const failed = () => showToast({ tone: TOAST_TONES.ERROR, ...LISTINGS_PANEL.toasts.error });

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
      if (status === LISTING_STATUS.UNPUBLISHED && !mercadoLivreConnected) return;
      setBusyId(listing.id);
      try {
        const updated = await updateListing(accountId, listing.id, {
          channels: { ...listing.channels, [PRIMARY_CHANNEL]: next.status }
        });
        if (!mounted.current) return;
        replaceListing(updated);
        showToast({ tone: TOAST_TONES.SUCCESS, ...next.toast });
      } catch {
        if (mounted.current) failed();
      } finally {
        if (mounted.current) setBusyId(null);
      }
    },
    [accountId, mercadoLivreConnected, replaceListing]
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
      } catch {
        if (mounted.current) failed();
      } finally {
        if (mounted.current) setBusyId(null);
      }
    },
    [accountId]
  );

  const requestRemoval = useCallback((listing) => setPendingRemoval(listing), []);
  const cancelRemoval = useCallback(() => {
    if (!removing) setPendingRemoval(null);
  }, [removing]);

  const confirmRemoval = useCallback(async () => {
    if (!pendingRemoval) return;
    setRemoving(true);
    try {
      await removeListing(accountId, pendingRemoval.id);
      if (!mounted.current) return;
      setData((current) => ({
        ...current,
        listings: current.listings.filter((listing) => listing.id !== pendingRemoval.id)
      }));
      setPendingRemoval(null);
      showToast({ tone: TOAST_TONES.SUCCESS, ...LISTINGS_PANEL.toasts.removed });
    } catch {
      if (mounted.current) failed();
    } finally {
      if (mounted.current) setRemoving(false);
    }
  }, [accountId, pendingRemoval]);

  return {
    account,
    hour,
    status: data.status,
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
