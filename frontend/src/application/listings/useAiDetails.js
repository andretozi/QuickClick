import { useCallback, useState } from 'react';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import { suggestListing } from '@/infrastructure/ai/suggestionService.js';
import { coverPhoto } from '@/domain/listings/listingRules.js';
import { LISTING_WIZARD } from '@/domain/content/listingContent.js';

const AI_STEP_MS = 700;

/**
 * Aplicação · "Sugestão da IA" no passo de detalhes (IA SIMULADA, infrastructure/ai):
 * olha a capa e preenche título, descrição, categoria e condição, com os passos
 * ("Olhando a foto", "Reconhecendo o produto"...) aparecendo um a um.
 * Devolve { ai: { status, step }, suggest, reset }.
 */
export default function useAiDetails({ draft, update, mounted }) {
  const [ai, setAi] = useState({ status: 'idle', step: 0 });
  const cover = coverPhoto(draft);

  const suggest = useCallback(async () => {
    if (ai.status === 'working') return;
    if (!cover) {
      setAi({ status: 'needs-photo', step: 0 });
      return;
    }
    setAi({ status: 'working', step: 0 });
    const ticker = window.setInterval(() => {
      setAi((current) => (current.status === 'working' ? { ...current, step: Math.min(current.step + 1, 2) } : current));
    }, AI_STEP_MS);
    try {
      const suggestion = await suggestListing({ photo: cover });
      if (!mounted.current) return;
      update(suggestion);
      setAi({ status: 'done', step: 2 });
      showToast({ tone: TOAST_TONES.SUCCESS, ...LISTING_WIZARD.details.ai.done });
    } catch {
      // a foto não abriu (rascunho corrompido, por exemplo): o botão volta a funcionar
      if (!mounted.current) return;
      setAi({ status: 'idle', step: 0 });
      showToast({ tone: TOAST_TONES.ERROR, ...LISTING_WIZARD.details.ai.error });
    } finally {
      window.clearInterval(ticker);
    }
  }, [ai.status, cover, update, mounted]);

  const reset = useCallback(() => setAi({ status: 'idle', step: 0 }), []);

  return { ai, suggest, reset };
}
