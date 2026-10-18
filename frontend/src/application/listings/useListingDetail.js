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
  removeListing,
  updateListing
} from '@/infrastructure/storage/listingsRepository.js';
import { fetchConnectedMarketplaces } from '@/infrastructure/marketplaces/marketplacesService.js';
import {
  deleteMercadoLivreItem,
  fetchMercadoLivreItem,
  publishToMercadoLivre,
  updateMercadoLivreStatus
} from '@/infrastructure/ai/iaService.js';
import { dataUrlToBlob } from '@/infrastructure/media/imageResizer.js';
import {
  LISTING_STATUS,
  PRIMARY_CHANNEL,
  copyTitle,
  listingStatus
} from '@/domain/listings/listingRules.js';
import { LISTINGS_PANEL } from '@/domain/content/dashboardContent.js';
import { LISTING_DETAIL, aiErrorText } from '@/domain/content/listingContent.js';

/**
 * Aplicação · Caso de uso "visão geral das macroinformações do anúncio" (#/anuncios/:id).
 *
 * Carrega o anúncio local e sincroniza automaticamente com o Mercado Livre (quando
 * publicado e conectado) para exibir fotos, descrição, ficha técnica, preço, estoque,
 * vendas e status sempre atualizados. Também permite pausar, reativar, duplicar e excluir.
 */
export default function useListingDetail(listingId) {
  const { account } = useSession();
  const accountId = account?.id;

  const [status, setStatus] = useState('loading');
  const [listing, setListing] = useState(null);
  const [mlConnected, setMlConnected] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState(0);

  const mounted = useMountedRef();

  const failed = useCallback((error) => {
    const message = error?.code ? aiErrorText(error.code, error.userMessage) : LISTINGS_PANEL.toasts.error;
    showToast({ tone: TOAST_TONES.ERROR, ...message });
  }, []);

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
        const connected = connections.some((c) => c.slug === PRIMARY_CHANNEL);
        setMlConnected(connected);
        setListing(local);
        setSelectedPhoto(local.coverIndex ?? 0);
        setStatus('ready');

        if (connected && local.mlItemId) {
          setSyncing(true);
          try {
            const fresh = await fetchMercadoLivreItem(local.mlItemId);
            const merged = await mergeMercadoLivreItem(accountId, listingId, fresh);
            if (mounted.current) {
              setListing(merged);
              setSelectedPhoto(merged.coverIndex ?? 0);
            }
          } catch {
            // Mantém os dados locais caso o Mercado Livre não responda no momento
          } finally {
            if (mounted.current) setSyncing(false);
          }
        }
      } catch {
        if (mounted.current) setStatus('not-found');
      }
    })();
  }, [accountId, listingId, mounted]);

  const syncNow = useCallback(async () => {
    if (!accountId || !listing?.mlItemId || !mlConnected || syncing) return;
    setSyncing(true);
    try {
      const fresh = await fetchMercadoLivreItem(listing.mlItemId);
      const merged = await mergeMercadoLivreItem(accountId, listing.id, fresh);
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
  }, [accountId, listing, mlConnected, mounted, syncing]);

  const toggleStatus = useCallback(async () => {
    if (!listing || !mlConnected || busy) return;
    const current = listingStatus(listing);
    const next =
      current === LISTING_STATUS.PUBLISHED
        ? { status: LISTING_STATUS.PAUSED, toast: LISTINGS_PANEL.toasts.paused }
        : current === LISTING_STATUS.PAUSED
          ? { status: LISTING_STATUS.PUBLISHED, toast: LISTINGS_PANEL.toasts.resumed }
          : { status: LISTING_STATUS.PUBLISHED, toast: LISTINGS_PANEL.toasts.published };
    setBusy(true);
    try {
      let updated;
      if (listing.mlItemId) {
        const mlItem = await updateMercadoLivreStatus(listing.mlItemId, next.status);
        updated = await mergeMercadoLivreItem(accountId, listing.id, mlItem);
      } else {
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
      }
      if (!mounted.current) return;
      setListing(updated);
      showToast({ tone: TOAST_TONES.SUCCESS, ...next.toast });
    } catch (error) {
      if (mounted.current) failed(error);
    } finally {
      if (mounted.current) setBusy(false);
    }
  }, [accountId, busy, failed, listing, mlConnected, mounted]);

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
    mlConnected,
    syncing,
    busy,
    selectedPhoto,
    setSelectedPhoto,
    syncNow,
    toggleStatus,
    duplicate,
    confirmingDelete,
    removing,
    requestRemoval,
    cancelRemoval,
    confirmRemoval
  };
}
