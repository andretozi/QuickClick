import { runMarketplacesAnimations } from '@/infrastructure/animation/marketplaces/index.js';
import useAnimationRunner from './useAnimationRunner.js';

/** Aplicação · Liga as animações da tela de marketplaces (fundo e topo) ao elemento raiz. */
export default function useMarketplacesAnimations(rootRef) {
  useAnimationRunner(rootRef, runMarketplacesAnimations);
}
