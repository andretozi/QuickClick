import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import useMountedRef from '@/application/ui/useMountedRef.js';
import useSession from '@/application/session/useSession.js';
import { dismissWelcome } from '@/application/session/sessionStore.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import { CHANNEL_ADAPTERS, getChannelAdapter } from '@/application/listings/channels/channelRegistry.js';
import {
  duplicateListing,
  listListings,
  listLocalListings,
  removeListing,
  updateListing
} from '@/infrastructure/storage/listingsRepository.js';
import { fetchConnectedMarketplaces } from '@/infrastructure/marketplaces/marketplacesService.js';
import { currentHour } from '@/infrastructure/browser/events.js';
import {
  LISTING_STATUS,
  PRIMARY_CHANNEL,
  QUICKSTORE_CHANNEL,
  channelActionTargets,
  channelStatus,
  copyTitle,
  filterListings,
  sortListings,
  summarizeListings
} from '@/domain/listings/listingRules.js';
import { LISTINGS_PANEL } from '@/domain/content/dashboardContent.js';
import { aiErrorText } from '@/domain/content/listingContent.js';

export const DASHBOARD_TABS = { LISTINGS: 'listings', INSIGHTS: 'insights' };

const DEFAULT_FILTERS = { query: '', status: 'all', sort: 'recent' };

const formatChannelNames = (slugs) => slugs.map((slug) => getChannelAdapter(slug).name ?? slug).join(' e ');

/** Rede fora ou servidor com erro (5xx): o painel mostra a cópia salva no navegador. */
const isConnectionError = (error) => error?.status === 0 || error?.status >= 500 || error?.code === 'sem_conexao';

/**
 * Aplicação · Caso de uso "painel do vendedor".
 *
 * Carrega os anúncios e as conexões da conta logada, sincroniza os dados reais
 * com os canais conectados, calcula os números do topo, filtra e ordena a lista e cuida
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
  const busyLockRef = useRef(null);

  const markChannelDisconnected = useCallback((slug) => {
    setData((current) => ({
      ...current,
      connections: current.connections.filter((connection) => connection.slug !== slug)
    }));
  }, []);

  const syncAllConnected = useCallback(
    async (connectionsList) => {
      if (!accountId) return null;
      let latest = null;
      for (const adapter of Object.values(CHANNEL_ADAPTERS)) {
        const isConnected = connectionsList.some((connection) => connection.slug === adapter.slug);
        if (!isConnected) continue;
        try {
          const synced = await adapter.syncAll(accountId);
          if (!mounted.current) return null;
          latest = synced;
        } catch (error) {
          if (mounted.current && error?.code === adapter.disconnectedCode) {
            markChannelDisconnected(adapter.slug);
          }
        }
      }
      return latest;
    },
    [accountId, markChannelDisconnected, mounted]
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

      const hasConnected = connections.some((connection) => Boolean(CHANNEL_ADAPTERS[connection.slug]));
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

  // Sincroniza automaticamente quando a aba do navegador volta a ficar ativa (ex.: após mexer em outro canal)
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

  const failed = useCallback(
    (error, explicitChannel = null) => {
      for (const adapter of Object.values(CHANNEL_ADAPTERS)) {
        if (error?.code === adapter.disconnectedCode) markChannelDisconnected(adapter.slug);
      }
      const message = error?.code
        ? aiErrorText(error.code, error.userMessage, {
            channel: error.channel ?? explicitChannel,
            details: error.details
          })
        : LISTINGS_PANEL.toasts.error;
      showToast({ tone: TOAST_TONES.ERROR, ...message });
    },
    [markChannelDisconnected]
  );

  const syncNow = useCallback(async () => {
    if (!accountId || (!mercadoLivreConnected && !quickStoreConnected) || syncing) return;
    setSyncing(true);
    try {
      let synced = null;
      for (const adapter of Object.values(CHANNEL_ADAPTERS)) {
        const isConnected = data.connections.some((connection) => connection.slug === adapter.slug);
        if (!isConnected) continue;
        synced = await adapter.syncAll(accountId);
      }
      if (!mounted.current) return;
      if (synced) setData((current) => ({ ...current, listings: synced }));
      showToast({ tone: TOAST_TONES.SUCCESS, ...LISTINGS_PANEL.toasts.synced });
    } catch (error) {
      if (mounted.current) failed(error);
    } finally {
      if (mounted.current) setSyncing(false);
    }
  }, [accountId, data.connections, failed, mercadoLivreConnected, quickStoreConnected, mounted, syncing]);

  const applyChannelTransition = useCallback(
    async (currentListing, channel, targetStatus) => {
      const adapter = getChannelAdapter(channel);
      const itemId = adapter.getItemId(currentListing);

      if (itemId) {
        try {
          return await adapter.setStatus(accountId, currentListing.id, itemId, targetStatus);
        } catch (error) {
          if (targetStatus === LISTING_STATUS.PUBLISHED && error?.code === 'anuncio_nao_encontrado') {
            const { payload, photoBlobs } = adapter.buildPayload(currentListing);
            const published = await adapter.publish(payload, photoBlobs);
            return updateListing(
              accountId,
              currentListing.id,
              adapter.toPublishedPatch(currentListing, published, LISTING_STATUS.PUBLISHED),
              { syncQuickStore: false }
            );
          }
          throw error;
        }
      }

      if (targetStatus === LISTING_STATUS.PUBLISHED) {
        const { payload, photoBlobs } = adapter.buildPayload(currentListing);
        const published = await adapter.publish(payload, photoBlobs);
        return updateListing(
          accountId,
          currentListing.id,
          adapter.toPublishedPatch(currentListing, published, targetStatus),
          { syncQuickStore: false }
        );
      }

      return updateListing(
        accountId,
        currentListing.id,
        {
          channels: { ...currentListing.channels, [channel]: targetStatus }
        },
        { syncQuickStore: false }
      );
    },
    [accountId]
  );

  /** Publica, pausa ou reativa um produto em um canal específico. */
  const toggleChannelStatus = useCallback(
    async (listing, channel = PRIMARY_CHANNEL) => {
      if (busyLockRef.current) return;
      const adapter = getChannelAdapter(channel);
      const connected = data.connections.some((connection) => connection.slug === adapter.slug);
      if (!connected) {
        showToast({
          tone: TOAST_TONES.ERROR,
          ...aiErrorText(adapter.disconnectedCode)
        });
        return;
      }

      const currentStatus = channelStatus(listing, channel);
      const next =
        currentStatus === LISTING_STATUS.PUBLISHED
          ? { status: LISTING_STATUS.PAUSED, toast: LISTINGS_PANEL.toasts.paused }
          : currentStatus === LISTING_STATUS.PAUSED
            ? { status: LISTING_STATUS.PUBLISHED, toast: LISTINGS_PANEL.toasts.resumed }
            : {
                status: LISTING_STATUS.PUBLISHED,
                toast:
                  adapter.slug === QUICKSTORE_CHANNEL
                    ? LISTINGS_PANEL.toasts.publishedQs
                    : LISTINGS_PANEL.toasts.publishedMl
              };

      busyLockRef.current = listing.id;
      setBusyId(listing.id);
      try {
        const updated = await applyChannelTransition(listing, channel, next.status);
        if (!mounted.current) return;
        replaceListing(updated);
        showToast({ tone: TOAST_TONES.SUCCESS, ...next.toast });
      } catch (error) {
        if (mounted.current) failed(error, channel);
      } finally {
        busyLockRef.current = null;
        if (mounted.current) setBusyId(null);
      }
    },
    [applyChannelTransition, data.connections, failed, replaceListing, mounted]
  );

  /** Ação geral do painel principal: atua em todos os e-commerces relevantes e sinaliza vínculos ausentes. */
  const toggleStatus = useCallback(
    async (listing) => {
      if (busyLockRef.current) return;
      const connectedByChannel = {
        [PRIMARY_CHANNEL]: mercadoLivreConnected,
        [QUICKSTORE_CHANNEL]: quickStoreConnected
      };
      const { overall, nextStatus, connectedTargets, disconnectedTargets } = channelActionTargets(
        listing,
        connectedByChannel
      );

      if (connectedTargets.length === 0) {
        if (disconnectedTargets.length === 1) {
          const slug = disconnectedTargets[0];
          showToast({
            tone: TOAST_TONES.ERROR,
            ...aiErrorText(getChannelAdapter(slug).disconnectedCode)
          });
        } else {
          showToast({
            tone: TOAST_TONES.ERROR,
            ...LISTINGS_PANEL.toasts.disconnectedMultiple(formatChannelNames(disconnectedTargets))
          });
        }
        return;
      }

      busyLockRef.current = listing.id;
      setBusyId(listing.id);
      try {
        let current = listing;
        for (const channel of connectedTargets) {
          current = await applyChannelTransition(current, channel, nextStatus);
        }
        if (!mounted.current) return;
        replaceListing(current);

        const activeDisconnected = disconnectedTargets.filter(
          (slug) => channelStatus(listing, slug) !== LISTING_STATUS.UNPUBLISHED
        );
        if (activeDisconnected.length > 0) {
          showToast({
            tone: TOAST_TONES.INFO,
            ...LISTINGS_PANEL.toasts.partialSuccess(
              formatChannelNames(connectedTargets),
              formatChannelNames(activeDisconnected)
            )
          });
        } else {
          const toast =
            overall === LISTING_STATUS.PUBLISHED
              ? LISTINGS_PANEL.toasts.paused
              : overall === LISTING_STATUS.PAUSED
                ? LISTINGS_PANEL.toasts.resumed
                : connectedTargets.length > 1
                  ? LISTINGS_PANEL.toasts.publishedBoth
                  : connectedTargets[0] === QUICKSTORE_CHANNEL
                    ? LISTINGS_PANEL.toasts.publishedQs
                    : LISTINGS_PANEL.toasts.publishedMl;
          showToast({ tone: TOAST_TONES.SUCCESS, ...toast });
        }
      } catch (error) {
        if (mounted.current) failed(error, connectedTargets.length === 1 ? connectedTargets[0] : null);
      } finally {
        busyLockRef.current = null;
        if (mounted.current) setBusyId(null);
      }
    },
    [applyChannelTransition, failed, mercadoLivreConnected, mounted, quickStoreConnected, replaceListing]
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

  const confirmChannelRemoval = useCallback(
    async (channel) => {
      if (!pendingRemoval || removing) return;
      const adapter = getChannelAdapter(channel);
      const itemId = adapter.getItemId(pendingRemoval);
      const connected = data.connections.some((connection) => connection.slug === adapter.slug);
      if (itemId && !connected) {
        showToast({
          tone: TOAST_TONES.ERROR,
          ...aiErrorText(adapter.disconnectedCode)
        });
        return;
      }
      setRemoving(true);
      try {
        if (itemId) {
          try {
            await adapter.remove(itemId);
          } catch (error) {
            if (error?.code !== 'anuncio_nao_encontrado') throw error;
          }
        }
        const updated = await updateListing(accountId, pendingRemoval.id, adapter.toClearedPatch(pendingRemoval), {
          syncQuickStore: false
        });
        if (!mounted.current) return;
        replaceListing(updated);
        setPendingRemoval(null);
        showToast({
          tone: TOAST_TONES.SUCCESS,
          ...(LISTINGS_PANEL.toasts.removedChannel
            ? LISTINGS_PANEL.toasts.removedChannel(adapter.name)
            : LISTINGS_PANEL.toasts.removed)
        });
      } catch (error) {
        if (mounted.current) failed(error, channel);
      } finally {
        if (mounted.current) setRemoving(false);
      }
    },
    [accountId, data.connections, failed, mounted, pendingRemoval, removing, replaceListing]
  );

  const confirmRemoval = useCallback(async () => {
    if (!pendingRemoval) return;
    setRemoving(true);
    try {
      for (const adapter of Object.values(CHANNEL_ADAPTERS)) {
        const itemId = adapter.getItemId(pendingRemoval);
        if (!itemId) continue;
        try {
          await adapter.remove(itemId);
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
    confirmChannelRemoval,
    retry: load,
    welcome,
    dismissWelcome
  };
}
