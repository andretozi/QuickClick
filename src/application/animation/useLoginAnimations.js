import { runLoginAnimations } from '@/infrastructure/animation/login/index.js';
import useAnimationRunner from './useAnimationRunner.js';

/** Aplicação · Liga as animações do login ao elemento raiz da página. */
export default function useLoginAnimations(rootRef) {
  useAnimationRunner(rootRef, runLoginAnimations);
}
