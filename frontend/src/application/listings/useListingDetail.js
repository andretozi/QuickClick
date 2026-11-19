import { useCallback, useEffect, useState } from 'react';
import useMountedRef from '@/application/ui/useMountedRef.js';
import useSession from '@/application/session/useSession.js';
import { replaceHash } from '@/infrastructure/browser/location.js';
import { ROUTE_HASH, ROUTES, hrefForListing } from '@/application/navigation/routes.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import {
  duplicateListing,
  getListing,
  mergeMercadoLivreItem,
  mergeQuickStoreItem,
  removeListing,
  updateListing
} from '@/infrastructure/storage/listingsRepository.js';
import { fetchConnectedMarketplaces } from '@/infrastructure/marketplaces/marketplacesService.js';
import {
  deleteMercadoLivreItem,
  deleteQuickStoreItem,
  fetchMercadoLivreItem,
  fetchQuickStoreItem,
  publishToMercadoLivre,
  publishToQuickStore,
  updateMercadoLivreStatus,
  updateQuickStoreStatus
} from '@/infrastructure/ai/iaService.js';
import { dataUrlToBlob } from '@/infrastructure/media/imageResizer.js';
import {
  LISTING_STATUS,
  PRIMARY_CHANNEL,
  QUICKSTORE_CHANNEL,
  channelActionTargets,
  channelStatus,
  copyTitle
} from '@/domain/listings/listingRules.js';
import { LISTINGS_PANEL } from '@/domain/content/dashboardContent.js';
import { LISTING_DETAIL, aiErrorText } from '@/domain/content/listingContent.js';

const CHANNEL_NAMES = {
  [PRIMARY_CHANNEL]: 'Mercado Livre',
  [QUICKSTORE_CHANNEL]: 'QuickStore'
};

const formatChannelNames = (slugs) => slugs.map((slug) => CHANNEL_NAMES[slug] ?? slug).join(' e ');

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
 * Aplicação · Caso de uso "visão geral das macroinformações do anúncio" (#/anuncios/:id).
 *
 * Carrega o anúncio local e sincroniza automaticamente com o Mercado Livre e a QuickStore
 * (quando publicado e conectado) para exibir fotos, descrição, ficha técnica, preço, estoque,
 * vendas e status sempre atualizados. Também permite publicar, pausar, reativar, colocar em standby,
 * duplicar e excluir.
 */
export default function useListingDetail(listingId) {
  const { account } = useSession();
  const accountId = account?.id;

  const [status, setStatus] = useState('loading');
  const [listing, setListing] = useState(null);
  const [mlConnected, setMlConnected] = useState(false);
  const [qsConnected, setQsConnected] = useState(false);
  const [authErrorByChannel, setAuthErrorByChannel] = useState({});
  const [syncing, setSyncing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState(0);

  const mounted = useMountedRef();

  const effectiveMlConnected = mlConnected && !authErrorByChannel[PRIMARY_CHANNEL];
  const effectiveQsConnected = qsConnected && !authErrorByChannel[QUICKSTORE_CHANNEL];

  const failed = useCallback((error) => {
    if (error?.code === 'mercado_livre_desconectado') {
      setAuthErrorByChannel((prev) => ({ ...prev, [PRIMARY_CHANNEL]: true }));
    }
    if (error?.code === 'quickstore_desconectada') {
      setAuthErrorByChannel((prev) => ({ ...prev, [QUICKSTORE_CHANNEL]: true }));
    }
    const message = error?.code ? aiErrorText(error.code, error.userMessage) : LISTINGS_PANEL.toasts.error;
    showToast({ tone: TOAST_TONES.ERROR, ...message });
  }, []);

  const syncChannelsForItem = useCallback(
    async (item, hasMl, hasQs) => {
      let current = item;
      if (hasMl && current.mlItemId) {
        try {
          const freshMl = await fetchMercadoLivreItem(current.mlItemId);
          current = await mergeMercadoLivreItem(accountId, current.id, freshMl);
        } catch (error) {
          if (error?.code === 'mercado_livre_desconectado') {
            setAuthErrorByChannel((prev) => ({ ...prev, [PRIMARY_CHANNEL]: true }));
          } else if (error?.code === 'anuncio_nao_encontrado') {
            current = await updateListing(
              accountId,
              current.id,
              {
                mlItemId: null,
                permalink: null,
                health: null,
                channels: { ...current.channels, [PRIMARY_CHANNEL]: LISTING_STATUS.UNPUBLISHED }
              },
              { syncQuickStore: false }
            );
          }
        }
      }
      if (hasQs && current.qsItemId) {
        try {
          const freshQs = await fetchQuickStoreItem(current.qsItemId);
          current = await mergeQuickStoreItem(accountId, current.id, freshQs);
        } catch (error) {
          if (error?.code === 'quickstore_desconectada') {
            setAuthErrorByChannel((prev) => ({ ...prev, [QUICKSTORE_CHANNEL]: true }));
          } else if (error?.code === 'anuncio_nao_encontrado') {
            current = await updateListing(
              accountId,
              current.id,
              {
                qsItemId: null,
                qsPermalink: null,
                qsHealth: null,
                channels: { ...current.channels, [QUICKSTORE_CHANNEL]: LISTING_STATUS.UNPUBLISHED }
              },
              { syncQuickStore: false }
            );
          }
        }
      }
      return current;
    },
    [accountId]
  );

  useEffect(() => {
    if (!accountId || !listingId) return;
    setStatus('loading');
    (async () => {
      try {
        const [local, connections] = await Promise.all([
          getListing(accountId, listingId),
          fetchConnectedMarketplaces().catch(() => [])
        ]);
        if (!mounted.current) return;
        const hasMl = connections.some((c) => c.slug === PRIMARY_CHANNEL);
        const hasQs = connections.some((c) => c.slug === QUICKSTORE_CHANNEL);
        setMlConnected(hasMl);
        setQsConnected(hasQs);
        setAuthErrorByChannel({});
        setListing(local);
        setSelectedPhoto(local.coverIndex ?? 0);
        setStatus('ready');

        if ((hasMl && local.mlItemId) || (hasQs && local.qsItemId)) {
          setSyncing(true);
          try {
            const merged = await syncChannelsForItem(local, hasMl, hasQs);
            if (mounted.current) {
              setListing(merged);
              setSelectedPhoto(merged.coverIndex ?? 0);
            }
          } catch {
            // Mantém os dados locais caso o canal não responda no momento
          } finally {
            if (mounted.current) setSyncing(false);
          }
        }
      } catch {
        if (mounted.current) setStatus('not-found');
      }
    })();
  }, [accountId, listingId, mounted, syncChannelsForItem]);

  const syncNow = useCallback(async () => {
    if (!accountId || !listing || syncing) return;
    const canSyncMl = effectiveMlConnected && Boolean(listing.mlItemId);
    const canSyncQs = effectiveQsConnected && Boolean(listing.qsItemId);
    if (!canSyncMl && !canSyncQs) return;
    setSyncing(true);
    try {
      const merged = await syncChannelsForItem(listing, effectiveMlConnected, effectiveQsConnected);
      if (!mounted.current) return;
      setListing(merged);
      setSelectedPhoto(merged.coverIndex ?? 0);
      showToast({ tone: TOAST_TONES.SUCCESS, ...LISTING_DETAIL.toasts.synced });
    } catch {
      if (mounted.current) {
        showToast({ tone: TOAST_TONES.ERROR, ...LISTING_DETAIL.toasts.syncError });
      }
    } finally {
      if (mounted.current) setSyncing(false);
    }
  }, [accountId, effectiveMlConnected, effectiveQsConnected, listing, mounted, syncChannelsForItem, syncing]);

  const applyChannelTransition = useCallback(
    async (currentListing, channel, targetStatus) => {
      const isQs = channel === QUICKSTORE_CHANNEL;
      const current = channelStatus(currentListing, channel);
      const itemId = isQs ? currentListing.qsItemId : currentListing.mlItemId;
      const shouldCreateFresh = !itemId || current === LISTING_STATUS.UNPUBLISHED;

      if (!shouldCreateFresh) {
        try {
          if (isQs) {
            const qsItem = await updateQuickStoreStatus(itemId, targetStatus);
            return mergeQuickStoreItem(accountId, currentListing.id, qsItem);
          }
          const mlItem = await updateMercadoLivreStatus(itemId, targetStatus);
          return mergeMercadoLivreItem(accountId, currentListing.id, mlItem);
        } catch (error) {
          if (
            targetStatus === LISTING_STATUS.PUBLISHED &&
            (error?.code === 'anuncio_nao_encontrado' || error?.code === 'publicacao_recusada')
          ) {
            const { payload, photoBlobs } = buildPublishInputs(currentListing);
            const published = isQs
              ? await publishToQuickStore(payload, photoBlobs)
              : await publishToMercadoLivre(payload, photoBlobs);
            return updateListing(
              accountId,
              currentListing.id,
              isQs
                ? {
                    qsItemId: published.id,
                    qsPermalink: published.permalink,
                    qsCategoryId: published.categoryId ?? currentListing.qsCategoryId ?? currentListing.mlCategoryId,
                    channels: { ...currentListing.channels, [QUICKSTORE_CHANNEL]: LISTING_STATUS.PUBLISHED }
                  }
                : {
                    mlItemId: published.id,
                    permalink: published.permalink,
                    mlCategoryId: published.categoryId ?? currentListing.mlCategoryId,
                    channels: { ...currentListing.channels, [PRIMARY_CHANNEL]: LISTING_STATUS.PUBLISHED }
                  },
              { syncQuickStore: false }
            );
          }
          throw error;
        }
      }

      const { payload, photoBlobs } = buildPublishInputs(currentListing);
      const published = isQs
        ? await publishToQuickStore(payload, photoBlobs)
        : await publishToMercadoLivre(payload, photoBlobs);
      return updateListing(
        accountId,
        currentListing.id,
        isQs
          ? {
              qsItemId: published.id,
              qsPermalink: published.permalink,
              qsCategoryId: published.categoryId ?? currentListing.qsCategoryId ?? currentListing.mlCategoryId,
              channels: { ...currentListing.channels, [QUICKSTORE_CHANNEL]: targetStatus }
            }
          : {
              mlItemId: published.id,
              permalink: published.permalink,
              mlCategoryId: published.categoryId ?? currentListing.mlCategoryId,
              channels: { ...currentListing.channels, [PRIMARY_CHANNEL]: targetStatus }
            },
        { syncQuickStore: false }
      );
    },
    [accountId]
  );

  const toggleChannelStatus = useCallback(
    async (channel = PRIMARY_CHANNEL) => {
      if (!listing || busy) return;
      const isQs = channel === QUICKSTORE_CHANNEL;
      const connected = isQs ? effectiveQsConnected : effectiveMlConnected;
      if (!connected) {
        showToast({
          tone: TOAST_TONES.ERROR,
          ...aiErrorText(isQs ? 'quickstore_desconectada' : 'mercado_livre_desconectado')
        });
        return;
      }

      const current = channelStatus(listing, channel);
      const next =
        current === LISTING_STATUS.PUBLISHED
          ? { status: LISTING_STATUS.PAUSED, toast: LISTINGS_PANEL.toasts.paused }
          : current === LISTING_STATUS.PAUSED
            ? { status: LISTING_STATUS.PUBLISHED, toast: LISTINGS_PANEL.toasts.resumed }
            : {
                status: LISTING_STATUS.PUBLISHED,
                toast: isQs ? LISTINGS_PANEL.toasts.publishedQs : LISTINGS_PANEL.toasts.publishedMl
              };

      setBusy(true);
      try {
        const updated = await applyChannelTransition(listing, channel, next.status);
        if (!mounted.current) return;
        setListing(updated);
        showToast({ tone: TOAST_TONES.SUCCESS, ...next.toast });
      } catch (error) {
        if (mounted.current) failed(error);
      } finally {
        if (mounted.current) setBusy(false);
      }
    },
    [applyChannelTransition, busy, effectiveMlConnected, effectiveQsConnected, failed, listing, mounted]
  );

  const toggleStatus = useCallback(() => toggleChannelStatus(PRIMARY_CHANNEL), [toggleChannelStatus]);

  /** Ação geral da tela de macro dados: atua em todos os canais conectados e informa desconectados. */
  const toggleAllChannels = useCallback(async () => {
    if (!listing || busy) return;
    const connectedByChannel = {
      [PRIMARY_CHANNEL]: effectiveMlConnected,
      [QUICKSTORE_CHANNEL]: effectiveQsConnected
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
          ...aiErrorText(slug === QUICKSTORE_CHANNEL ? 'quickstore_desconectada' : 'mercado_livre_desconectado')
        });
      } else {
        showToast({
          tone: TOAST_TONES.ERROR,
          ...LISTINGS_PANEL.toasts.disconnectedMultiple(formatChannelNames(disconnectedTargets))
        });
      }
      return;
    }

    setBusy(true);
    try {
      let current = listing;
      for (const channel of connectedTargets) {
        current = await applyChannelTransition(current, channel, nextStatus);
      }
      if (!mounted.current) return;
      setListing(current);

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
      if (mounted.current) failed(error);
    } finally {
      if (mounted.current) setBusy(false);
    }
  }, [applyChannelTransition, busy, effectiveMlConnected, effectiveQsConnected, failed, listing, mounted]);

  /** Publica de uma só vez nos dois canais (Mercado Livre e QuickStore) quando o produto está em standby. */
  const publishBothChannels = useCallback(async () => {
    if (!listing || !effectiveMlConnected || !effectiveQsConnected || busy) return;
    setBusy(true);
    try {
      const { payload, photoBlobs } = buildPublishInputs(listing);
      const mlUnpublished = channelStatus(listing, PRIMARY_CHANNEL) === LISTING_STATUS.UNPUBLISHED || !listing.mlItemId;
      const qsUnpublished = channelStatus(listing, QUICKSTORE_CHANNEL) === LISTING_STATUS.UNPUBLISHED || !listing.qsItemId;

      const [pubMl, pubQs] = await Promise.all([
        mlUnpublished ? publishToMercadoLivre(payload, photoBlobs) : Promise.resolve(null),
        qsUnpublished ? publishToQuickStore(payload, photoBlobs) : Promise.resolve(null)
      ]);

      const updated = await updateListing(
        accountId,
        listing.id,
        {
          ...(pubMl
            ? {
                mlItemId: pubMl.id,
                permalink: pubMl.permalink,
                mlCategoryId: pubMl.categoryId ?? listing.mlCategoryId
              }
            : {}),
          ...(pubQs
            ? {
                qsItemId: pubQs.id,
                qsPermalink: pubQs.permalink,
                qsCategoryId: pubQs.categoryId ?? listing.qsCategoryId ?? listing.mlCategoryId
              }
            : {}),
          channels: {
            ...listing.channels,
            [PRIMARY_CHANNEL]: LISTING_STATUS.PUBLISHED,
            [QUICKSTORE_CHANNEL]: LISTING_STATUS.PUBLISHED
          }
        },
        { syncQuickStore: false }
      );
      if (!mounted.current) return;
      setListing(updated);
      showToast({ tone: TOAST_TONES.SUCCESS, ...LISTINGS_PANEL.toasts.publishedBoth });
    } catch (error) {
      if (mounted.current) failed(error);
    } finally {
      if (mounted.current) setBusy(false);
    }
  }, [accountId, busy, effectiveMlConnected, effectiveQsConnected, failed, listing, mounted]);

  /** Tira o produto de venda em um canal e deixa-o em standby na Quick Click (para republicar quando quiser). */
  const putInStandby = useCallback(
    async (channel = PRIMARY_CHANNEL) => {
      const isQs = channel === QUICKSTORE_CHANNEL;
      if (!listing || busy) return;
      const itemId = isQs ? listing.qsItemId : listing.mlItemId;
      const connected = isQs ? effectiveQsConnected : effectiveMlConnected;
      if (itemId && !connected) {
        showToast({
          tone: TOAST_TONES.ERROR,
          ...LISTING_DETAIL.toasts.standbyDisconnected(CHANNEL_NAMES[channel] ?? channel)
        });
        return;
      }
      setBusy(true);
      try {
        if (itemId) {
          try {
            if (isQs) await deleteQuickStoreItem(itemId);
            else await deleteMercadoLivreItem(itemId);
          } catch (error) {
            if (error?.code !== 'anuncio_nao_encontrado') throw error;
          }
        }
        const updated = await updateListing(
          accountId,
          listing.id,
          isQs
            ? {
                qsItemId: null,
                qsPermalink: null,
                qsHealth: null,
                channels: { ...listing.channels, [QUICKSTORE_CHANNEL]: LISTING_STATUS.UNPUBLISHED }
              }
            : {
                mlItemId: null,
                permalink: null,
                health: null,
                channels: { ...listing.channels, [PRIMARY_CHANNEL]: LISTING_STATUS.UNPUBLISHED }
              },
          { syncQuickStore: false }
        );
        if (!mounted.current) return;
        setListing(updated);
        showToast({ tone: TOAST_TONES.INFO, ...LISTING_DETAIL.toasts.standby });
      } catch (error) {
        if (mounted.current) failed(error);
      } finally {
        if (mounted.current) setBusy(false);
      }
    },
    [accountId, busy, effectiveMlConnected, effectiveQsConnected, failed, listing, mounted]
  );

  const duplicate = useCallback(async () => {
    if (!listing || busy) return;
    setBusy(true);
    try {
      const copy = await duplicateListing(accountId, listing.id, {
        title: copyTitle(listing.title, LISTINGS_PANEL.copySuffix)
      });
      if (!mounted.current) return;
      showToast({ tone: TOAST_TONES.SUCCESS, ...LISTINGS_PANEL.toasts.duplicated });
      replaceHash(hrefForListing(copy.id));
    } catch (error) {
      if (mounted.current) failed(error);
    } finally {
      if (mounted.current) setBusy(false);
    }
  }, [accountId, busy, failed, listing, mounted]);

  const requestRemoval = useCallback(() => setConfirmingDelete(true), []);
  const cancelRemoval = useCallback(() => {
    if (!removing) setConfirmingDelete(false);
  }, [removing]);

  const confirmRemoval = useCallback(async () => {
    if (!listing || removing) return;
    setRemoving(true);
    try {
      if (listing.mlItemId) {
        try {
          await deleteMercadoLivreItem(listing.mlItemId);
        } catch (error) {
          if (error?.code !== 'anuncio_nao_encontrado') throw error;
        }
      }
      if (listing.qsItemId) {
        try {
          await deleteQuickStoreItem(listing.qsItemId);
        } catch (error) {
          if (error?.code !== 'anuncio_nao_encontrado') throw error;
        }
      }
      await removeListing(accountId, listing.id);
      if (!mounted.current) return;
      setConfirmingDelete(false);
      showToast({ tone: TOAST_TONES.SUCCESS, ...LISTINGS_PANEL.toasts.removed });
      replaceHash(ROUTE_HASH[ROUTES.DASHBOARD]);
    } catch (error) {
      if (mounted.current) failed(error);
    } finally {
      if (mounted.current) setRemoving(false);
    }
  }, [accountId, failed, listing, mounted, removing]);

  return {
    status,
    listing,
    mlConnected: effectiveMlConnected,
    qsConnected: effectiveQsConnected,
    authErrorByChannel,
    syncing,
    busy,
    selectedPhoto,
    setSelectedPhoto,
    syncNow,
    toggleStatus,
    toggleChannelStatus,
    toggleAllChannels,
    publishBothChannels,
    putInStandby,
    duplicate,
    confirmingDelete,
    removing,
    requestRemoval,
    cancelRemoval,
    confirmRemoval
  };
}
