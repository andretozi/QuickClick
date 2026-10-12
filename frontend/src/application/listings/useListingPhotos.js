import { useCallback, useState } from 'react';
import { resizeImage } from '@/infrastructure/media/imageResizer.js';
import { LISTING_LIMITS } from '@/domain/listings/listingRules.js';
import { withoutPhoto } from '@/domain/listings/listingDraft.js';

/**
 * Aplicação · Fotos do anúncio no editor: reduz e junta os arquivos escolhidos (até 6),
 * tira uma foto e escolhe a capa. O rascunho mora no useListingEditor (setDraft e update).
 * Devolve { add, remove, setCover, busy, error }; error é 'full' ou 'invalid'.
 */
export default function useListingPhotos({ photoCount, setDraft, setErrors, update, mounted }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const add = useCallback(
    async (fileList) => {
      const files = Array.from(fileList ?? []);
      if (!files.length) return;
      setError(null);
      const room = LISTING_LIMITS.PHOTOS_MAX - photoCount;
      if (room <= 0) {
        setError('full');
        return;
      }
      setBusy(true);
      const added = [];
      let invalid = false;
      for (const file of files.slice(0, room)) {
        try {
          added.push(await resizeImage(file));
        } catch {
          invalid = true;
        }
      }
      if (!mounted.current) return;
      setBusy(false);
      if (invalid) setError('invalid');
      else if (files.length > room) setError('full');
      if (added.length) {
        setDraft((current) => ({ ...current, photos: [...current.photos, ...added].slice(0, LISTING_LIMITS.PHOTOS_MAX) }));
        setErrors((current) => ({ ...current, photos: undefined }));
      }
    },
    [photoCount, setDraft, setErrors, mounted]
  );

  const remove = useCallback(
    (index) => {
      setError(null);
      setDraft((current) => withoutPhoto(current, index));
    },
    [setDraft]
  );

  const setCover = useCallback((index) => update({ coverIndex: index }), [update]);

  return { add, remove, setCover, busy, error };
}
