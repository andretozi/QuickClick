import { runShellAnimations, runStandaloneAnimations } from '@/infrastructure/animation/app/shell.js';
import useAnimationRunner from './useAnimationRunner.js';

/** Aplicação · Liga as animações da casca da área logada (fundo, navbar e entradas). */
export default function useShellAnimations(rootRef) {
  useAnimationRunner(rootRef, runShellAnimations);
}

/** Aplicação · Mesmas luzes e entradas para uma página sem navbar (404). */
export function useStandaloneAnimations(rootRef) {
  useAnimationRunner(rootRef, runStandaloneAnimations);
}
