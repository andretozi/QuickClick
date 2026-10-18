import { useCallback, useRef, useState } from 'react';
import { dataUrlToBlob, preparePhotoVersions } from '@/infrastructure/media/imageResizer.js';
import { LISTING_LIMITS } from '@/domain/listings/listingRules.js';
import { withoutPhoto } from '@/domain/listings/listingDraft.js';

/**
 * Aplicação · Fotos do anúncio no editor: de cada arquivo saem a versão de guardar (800 px,
 * no rascunho) e a de leitura (1568 px, só na memória, para a IA). Junta até 6, tira uma
 * foto e escolhe a capa. O rascunho mora no useListingEditor (setDraft e update).
 * Devolve { add, remove, setCover, readingBlobs, release, busy, error }; error é 'full' ou 'invalid'.
 */
export default function useListingPhotos({ photoCount, setDraft, setErrors, update, mounted }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const reading = useRef(new Map()); // foto guardada (data URL) → versão de leitura (Blob)

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
          const versions = await preparePhotoVersions(file);
          reading.current.set(versions.stored, versions.reading);
          added.push(versions.stored);
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
      setDraft((current) => {
        reading.current.delete(current.photos[index]);
        return withoutPhoto(current, index);
      });
    },
    [setDraft]
  );

  const setCover = useCallback((index) => update({ coverIndex: index }), [update]);

  /** As fotos para mandar ao back: a de leitura quando ainda está na memória, senão a guardada. */
  const readingBlobs = useCallback(
    (photos) => photos.map((photo) => reading.current.get(photo) ?? dataUrlToBlob(photo)),
    []
  );

  /** Depois de mandadas para a análise, as versões de leitura saem da memória. */
  const release = useCallback(() => reading.current.clear(), []);

  return { add, remove, setCover, readingBlobs, release, busy, error };
}
