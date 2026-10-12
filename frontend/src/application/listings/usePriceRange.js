import { useCallback, useEffect, useMemo, useState } from 'react';
import { suggestPriceRange } from '@/infrastructure/ai/suggestionService.js';
import { centsToInput, parseMoney } from '@/domain/format/format.js';
import { pricePositionIn } from '@/domain/listings/listingDraft.js';

/**
 * Aplicação · Faixa de preço de itens parecidos (IA SIMULADA, infrastructure/ai).
 * Pede a faixa quando o vendedor chega no passo de preço (`active`), diz onde o preço
 * dele cai (abaixo, justo ou acima) e aplica o preço sugerido.
 * Devolve { range, priceCents, position, acceptSuggested, reset }.
 */
export default function usePriceRange({ active, draft, update, mounted }) {
  const [range, setRange] = useState({ status: 'idle' });

  useEffect(() => {
    if (!active || !draft.category) return;
    let alive = true;
    setRange({ status: 'loading' });
    suggestPriceRange({ category: draft.category, condition: draft.condition, title: draft.title }).then((value) => {
      if (alive && mounted.current) setRange({ status: 'ready', ...value });
    });
    return () => {
      alive = false;
    };
  }, [active, draft.category, draft.condition, draft.title, mounted]);

  const acceptSuggested = useCallback(() => {
    if (range.status === 'ready') update({ priceInput: centsToInput(range.suggestedCents) });
  }, [range, update]);

  const priceCents = parseMoney(draft.priceInput);
  const position = useMemo(() => pricePositionIn(range, priceCents), [priceCents, range]);
  const reset = useCallback(() => setRange({ status: 'idle' }), []);

  return { range, priceCents, position, acceptSuggested, reset };
}
