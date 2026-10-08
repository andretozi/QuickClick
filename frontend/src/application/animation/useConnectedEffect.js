import { useLayoutEffect } from 'react';
import { playConnected } from '@/infrastructure/animation/marketplaces/cards.js';

/**
 * Aplicação · Quando `active` vira true, o card comemora a conexão (check se
 * desenhando e onda). Roda antes da pintura para o check não aparecer pronto antes.
 */
export default function useConnectedEffect(cardRef, active) {
  useLayoutEffect(() => {
    const card = cardRef.current;
    if (!active || !card) return undefined;
    return playConnected(card);
  }, [cardRef, active]);
}
