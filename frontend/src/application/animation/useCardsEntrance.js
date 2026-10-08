import { runCardsEntrance } from '@/infrastructure/animation/marketplaces/cards.js';
import useAnimationRunner from './useAnimationRunner.js';

/** Aplicação · Os cards de marketplace entram em sequência quando a grade aparece. */
export default function useCardsEntrance(containerRef) {
  useAnimationRunner(containerRef, runCardsEntrance);
}
