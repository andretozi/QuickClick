import { useCallback, useEffect, useState } from 'react';
import { saveDraft } from '@/infrastructure/storage/draftsRepository.js';
import { StorageFullError } from '@/infrastructure/storage/localStore.js';
import { formatTime } from '@/domain/format/format.js';
import { isBlankDraft } from '@/domain/listings/listingDraft.js';

const AUTOSAVE_MS = 500;

/**
 * Aplicação · Rascunho salvo sozinho no "criar anúncio": meio segundo depois da última
 * mudança, grava o passo e os campos (nunca um rascunho vazio, nem enquanto publica).
 * Avisa quando o navegador fica sem espaço (fotos grandes).
 * Devolve { savedAt ("14:05"), storageFull, clearSavedAt }.
 */
export default function useDraftAutosave({ accountId, draft, stepIndex, enabled, loaded, finishing, mounted }) {
  const [savedAt, setSavedAt] = useState(null);
  const [storageFull, setStorageFull] = useState(false);

  useEffect(() => {
    if (!enabled || !loaded.current || !accountId || isBlankDraft(draft)) return undefined;
    const timer = window.setTimeout(async () => {
      if (finishing.current) return;
      try {
        await saveDraft(accountId, { step: stepIndex, data: draft });
        if (!mounted.current) return;
        setSavedAt(formatTime(new Date()));
        setStorageFull(false);
      } catch (error) {
        if (mounted.current && error instanceof StorageFullError) setStorageFull(true);
      }
    }, AUTOSAVE_MS);
    return () => window.clearTimeout(timer);
  }, [accountId, draft, enabled, stepIndex, loaded, finishing, mounted]);

  const clearSavedAt = useCallback(() => setSavedAt(null), []);

  return { savedAt, storageFull, clearSavedAt };
}
