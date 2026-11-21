import { useCallback, useEffect, useState } from 'react';
import useMountedRef from '@/application/ui/useMountedRef.js';
import useSession from '@/application/session/useSession.js';
import { replaceHash } from '@/infrastructure/browser/location.js';
import { ROUTE_HASH, ROUTES, hrefForListing } from '@/application/navigation/routes.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import { CHANNEL_ADAPTERS, getChannelAdapter } from '@/application/listings/channels/channelRegistry.js';
import {
  duplicateListing,
  getListing,
  removeListing,
  updateListing
} from '@/infrastructure/storage/listingsRepository.js';
import { fetchConnectedMarketplaces } from '@/infrastructure/marketplaces/marketplacesService.js';
import {
  LISTING_LIMITS,
  LISTING_STATUS,
  PRIMARY_CHANNEL,
  QUICKSTORE_CHANNEL,
  channelActionTargets,
  channelStatus,
  copyTitle
} from '@/domain/listings/listingRules.js';
import { LISTINGS_PANEL } from '@/domain/content/dashboardContent.js';
import { LISTING_DETAIL, aiErrorText } from '@/domain/content/listingContent.js';

const formatChannelNames = (slugs) => slugs.map((slug) => getChannelAdapter(slug).name ?? slug).join(' e ');

/**
 * Aplicação · Caso de uso "visão geral das macroinformações do anúncio" (#/anuncios/:id).
 *
 * Carrega o anúncio local e sincroniza automaticamente com os canais conectados
 * (quando publicado e conectado) para exibir fotos, descrição, ficha técnica, preço, estoque,
 * vendas e status sempre atualizados. Também permite publicar, pausar, reativar, excluir por canal,
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
  const [pendingChannelRemoval, setPendingChannelRemoval] = useState(null);
  const [removingChannel, setRemovingChannel] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState(0);

  const mounted = useMountedRef();

  const effectiveMlConnected = mlConnected && !authErrorByChannel[PRIMARY_CHANNEL];
  const effectiveQsConnected = qsConnected && !authErrorByChannel[QUICKSTORE_CHANNEL];

  const isChannelConnected = useCallback(
    (slug) => (slug === QUICKSTORE_CHANNEL ? effectiveQsConnected : effectiveMlConnected),
    [effectiveMlConnected, effectiveQsConnected]
  );

  const failed = useCallback((error, explicitChannel = null) => {
    for (const adapter of Object.values(CHANNEL_ADAPTERS)) {
      if (error?.code === adapter.disconnectedCode) {
        setAuthErrorByChannel((prev) => ({ ...prev, [adapter.slug]: true }));
      }
    }
    const message = error?.code
      ? aiErrorText(error.code, error.userMessage, {
          channel: error.channel ?? explicitChannel,
          details: error.details
        })
      : LISTINGS_PANEL.toasts.error;
    showToast({ tone: TOAST_TONES.ERROR, ...message });
  }, []);

  const syncChannelsForItem = useCallback(
    async (item, connectedBySlug) => {
      let current = item;
      for (const adapter of Object.values(CHANNEL_ADAPTERS)) {
        if (!connectedBySlug[adapter.slug] || !adapter.getItemId(current)) continue;
        try {
          current = await adapter.syncOne(accountId, current);
        } catch (error) {
          if (error?.code === adapter.disconnectedCode) {
            setAuthErrorByChannel((prev) => ({ ...prev, [adapter.slug]: true }));
          } else if (error?.code === 'anuncio_nao_encontrado') {
            current = await updateListing(accountId, current.id, adapter.toClearedPatch(current), {
              syncQuickStore: false
            });
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
        const [localRaw, connections] = await Promise.all([
          getListing(accountId, listingId),
          fetchConnectedMarketplaces().catch(() => [])
        ]);
        if (!mounted.current) return;
        const hasMl = connections.some((c) => c.slug === PRIMARY_CHANNEL);
        const hasQs = connections.some((c) => c.slug === QUICKSTORE_CHANNEL);
        setMlConnected(hasMl);
        setQsConnected(hasQs);
        setAuthErrorByChannel({});
        let local = localRaw;
        setListing(local);
        setSelectedPhoto(local.coverIndex ?? 0);
        setStatus('ready');

        const connectedBySlug = {
          [PRIMARY_CHANNEL]: hasMl,
          [QUICKSTORE_CHANNEL]: hasQs
        };

        for (const adapter of Object.values(CHANNEL_ADAPTERS)) {
          if (!connectedBySlug[adapter.slug]) continue;
          try {
            const reconciled = await adapter.reconcileIfNeeded(accountId, local);
            if (!mounted.current) return;
            if (reconciled !== local) {
              local = reconciled;
              setListing(local);
              setSelectedPhoto(local.coverIndex ?? 0);
            }
          } catch (error) {
            if (mounted.current && error?.code === adapter.disconnectedCode) {
              setAuthErrorByChannel((prev) => ({ ...prev, [adapter.slug]: true }));
            }
          }
        }

        const anyLinked = Object.values(CHANNEL_ADAPTERS).some(
          (adapter) => connectedBySlug[adapter.slug] && Boolean(adapter.getItemId(local))
        );
        if (anyLinked) {
          setSyncing(true);
          try {
            const merged = await syncChannelsForItem(local, connectedBySlug);
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
    const connectedBySlug = {
      [PRIMARY_CHANNEL]: effectiveMlConnected,
      [QUICKSTORE_CHANNEL]: effectiveQsConnected
    };
    const canSyncAny = Object.values(CHANNEL_ADAPTERS).some(
      (adapter) => connectedBySlug[adapter.slug] && Boolean(adapter.getItemId(listing))
    );
    if (!canSyncAny) return;
    setSyncing(true);
    try {
      const merged = await syncChannelsForItem(listing, connectedBySlug);
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

      const { payload, photoBlobs } = adapter.buildPayload(currentListing);
      const published = await adapter.publish(payload, photoBlobs);
      return updateListing(
        accountId,
        currentListing.id,
        adapter.toPublishedPatch(currentListing, published, targetStatus),
        { syncQuickStore: false }
      );
    },
    [accountId]
  );

  const toggleChannelStatus = useCallback(
    async (channel = PRIMARY_CHANNEL) => {
      if (!listing || busy) return;
      const adapter = getChannelAdapter(channel);
      if (!isChannelConnected(adapter.slug)) {
        showToast({
          tone: TOAST_TONES.ERROR,
          ...aiErrorText(adapter.disconnectedCode)
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
                toast:
                  adapter.slug === QUICKSTORE_CHANNEL
                    ? LISTINGS_PANEL.toasts.publishedQs
                    : LISTINGS_PANEL.toasts.publishedMl
              };

      setBusy(true);
      try {
        const updated = await applyChannelTransition(listing, channel, next.status);
        if (!mounted.current) return;
        setListing(updated);
        showToast({ tone: TOAST_TONES.SUCCESS, ...next.toast });
      } catch (error) {
        if (mounted.current) failed(error, channel);
      } finally {
        if (mounted.current) setBusy(false);
      }
    },
    [applyChannelTransition, busy, failed, isChannelConnected, listing, mounted]
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
      if (mounted.current) failed(error, connectedTargets.length === 1 ? connectedTargets[0] : null);
    } finally {
      if (mounted.current) setBusy(false);
    }
  }, [applyChannelTransition, busy, effectiveMlConnected, effectiveQsConnected, failed, listing, mounted]);

  /** Publica de uma só vez nos dois canais (Mercado Livre e QuickStore) quando o produto está em standby. */
  const publishBothChannels = useCallback(async () => {
    if (!listing || !effectiveMlConnected || !effectiveQsConnected || busy) return;
    setBusy(true);
    try {
      const mlAdapter = getChannelAdapter(PRIMARY_CHANNEL);
      const qsAdapter = getChannelAdapter(QUICKSTORE_CHANNEL);
      const mlInputs = mlAdapter.buildPayload(listing);
      const qsInputs = qsAdapter.buildPayload(listing);
      const mlUnpublished =
        channelStatus(listing, PRIMARY_CHANNEL) === LISTING_STATUS.UNPUBLISHED || !mlAdapter.getItemId(listing);
      const qsUnpublished =
        channelStatus(listing, QUICKSTORE_CHANNEL) === LISTING_STATUS.UNPUBLISHED || !qsAdapter.getItemId(listing);

      const [pubMl, pubQs] = await Promise.all([
        mlUnpublished ? mlAdapter.publish(mlInputs.payload, mlInputs.photoBlobs) : Promise.resolve(null),
        qsUnpublished ? qsAdapter.publish(qsInputs.payload, qsInputs.photoBlobs) : Promise.resolve(null)
      ]);

      const mlPatch = pubMl ? mlAdapter.toPublishedPatch(listing, pubMl) : {};
      const qsPatch = pubQs ? qsAdapter.toPublishedPatch(listing, pubQs) : {};

      const updated = await updateListing(
        accountId,
        listing.id,
        {
          ...mlPatch,
          ...qsPatch,
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

  /** Atualiza o estoque na visão geral e sincroniza automaticamente nos canais conectados. */
  const updateStock = useCallback(
    async (rawQuantity) => {
      if (!listing || busy) return false;
      const parsed = Number(rawQuantity);
      if (!Number.isInteger(parsed) || parsed < 0 || parsed > LISTING_LIMITS.STOCK_MAX) {
        showToast({
          tone: TOAST_TONES.ERROR,
          ...(LISTING_DETAIL.toasts.stockInvalid ?? {
            title: 'Estoque inválido.',
            text: `Informe um número inteiro entre 0 e ${LISTING_LIMITS.STOCK_MAX}.`
          })
        });
        return false;
      }

      setBusy(true);
      try {
        const nextChannels = { ...listing.channels };
        let combinedPatch = {};
        const syncedChannels = [];
        const keptPhotos = (listing.photos ?? []).filter((p) => String(p).startsWith('https://')).slice(0, 12);

        for (const adapter of Object.values(CHANNEL_ADAPTERS)) {
          const itemId = adapter.getItemId(listing);
          if (!isChannelConnected(adapter.slug) || !itemId) continue;

          const prevStatus = channelStatus(listing, adapter.slug);
          const { payload } = adapter.buildPayload(listing, { stock: parsed, keptPhotos, photoBlobs: [] });
          let result = null;

          if (adapter.slug === PRIMARY_CHANNEL && parsed === 0) {
            if (prevStatus === LISTING_STATUS.PUBLISHED) {
              result = await adapter.setStatus(null, null, itemId, LISTING_STATUS.PAUSED);
            }
            result = await adapter.update(itemId, payload, []);
            nextChannels[adapter.slug] = LISTING_STATUS.PAUSED;
          } else {
            result = await adapter.update(itemId, payload, []);
            if (parsed === 0 && prevStatus === LISTING_STATUS.PUBLISHED) {
              result = await adapter.setStatus(null, null, itemId, LISTING_STATUS.PAUSED);
              nextChannels[adapter.slug] = LISTING_STATUS.PAUSED;
            } else if (parsed > 0 && prevStatus === LISTING_STATUS.PAUSED) {
              result = await adapter.setStatus(null, null, itemId, LISTING_STATUS.PUBLISHED);
              nextChannels[adapter.slug] = LISTING_STATUS.PUBLISHED;
            }
          }

          if (result) {
            const channelPatch = adapter.toUpdatedPatch(listing, result, listing.photos ?? [], false);
            delete channelPatch.photos;
            delete channelPatch.coverIndex;
            combinedPatch = { ...combinedPatch, ...channelPatch };
          }
          syncedChannels.push(adapter.name);
        }

        const updated = await updateListing(
          accountId,
          listing.id,
          {
            stock: parsed,
            ...combinedPatch,
            channels: nextChannels
          },
          { syncQuickStore: false }
        );
        if (!mounted.current) return false;
        setListing(updated);
        const toastMsg =
          syncedChannels.length > 0 && LISTING_DETAIL.toasts.stockSynced
            ? LISTING_DETAIL.toasts.stockSynced(syncedChannels.join(' e '))
            : (LISTING_DETAIL.toasts.stockSaved ?? {
                title: 'Estoque atualizado.',
                text: 'A quantidade disponível já foi salva no anúncio.'
              });
        showToast({ tone: TOAST_TONES.SUCCESS, ...toastMsg });
        return true;
      } catch (error) {
        if (mounted.current) failed(error);
        return false;
      } finally {
        if (mounted.current) setBusy(false);
      }
    },
    [accountId, busy, failed, isChannelConnected, listing, mounted]
  );

  const requestChannelRemoval = useCallback((channel = PRIMARY_CHANNEL) => {
    setPendingChannelRemoval(channel);
  }, []);

  const cancelChannelRemoval = useCallback(() => {
    if (!removingChannel) setPendingChannelRemoval(null);
  }, [removingChannel]);

  /** Exclui o produto apenas na plataforma selecionada, mantendo-o salvo na Quick Click e nos outros canais. */
  const confirmChannelRemoval = useCallback(
    async (explicitChannel) => {
      const channel = explicitChannel || pendingChannelRemoval;
      if (!channel || !listing || removingChannel) return;
      const adapter = getChannelAdapter(channel);
      const itemId = adapter.getItemId(listing);
      const connected = isChannelConnected(adapter.slug);
      if (itemId && !connected) {
        const toastMsg = LISTING_DETAIL.toasts.deleteChannelDisconnected
          ? LISTING_DETAIL.toasts.deleteChannelDisconnected(adapter.name)
          : LISTING_DETAIL.toasts.standbyDisconnected(adapter.name);
        showToast({
          tone: TOAST_TONES.ERROR,
          ...toastMsg
        });
        return;
      }
      setRemovingChannel(true);
      try {
        if (itemId) {
          try {
            await adapter.remove(itemId);
          } catch (error) {
            if (error?.code !== 'anuncio_nao_encontrado') throw error;
          }
        }
        const updated = await updateListing(accountId, listing.id, adapter.toClearedPatch(listing), {
          syncQuickStore: false
        });
        if (!mounted.current) return;
        setListing(updated);
        setPendingChannelRemoval(null);
        const toastDone = LISTING_DETAIL.toasts.deletedChannel
          ? LISTING_DETAIL.toasts.deletedChannel(adapter.name)
          : LISTING_DETAIL.toasts.standby;
        showToast({ tone: TOAST_TONES.SUCCESS, ...toastDone });
      } catch (error) {
        if (mounted.current) failed(error, channel);
      } finally {
        if (mounted.current) setRemovingChannel(false);
      }
    },
    [accountId, failed, isChannelConnected, listing, mounted, pendingChannelRemoval, removingChannel]
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
      for (const adapter of Object.values(CHANNEL_ADAPTERS)) {
        const itemId = adapter.getItemId(listing);
        if (!itemId) continue;
        try {
          await adapter.remove(itemId);
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
    updateStock,
    toggleStatus,
    toggleChannelStatus,
    toggleAllChannels,
    publishBothChannels,
    putInStandby: requestChannelRemoval,
    pendingChannelRemoval,
    removingChannel,
    requestChannelRemoval,
    cancelChannelRemoval,
    confirmChannelRemoval,
    duplicate,
    confirmingDelete,
    removing,
    requestRemoval,
    cancelRemoval,
    confirmRemoval
  };
}
