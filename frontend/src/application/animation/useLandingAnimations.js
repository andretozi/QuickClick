import { runLandingAnimations } from '@/infrastructure/animation/landing/index.js';
import useAnimationRunner from './useAnimationRunner.js';

/** Aplicação · Liga todas as animações da landing ao elemento raiz da página. */
export default function useLandingAnimations(rootRef) {
  useAnimationRunner(rootRef, runLandingAnimations);
}
