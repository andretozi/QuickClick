import { useLayoutEffect } from 'react';
import {
  playMenuEnter,
  playMenuExit,
  playModalEnter,
  playModalExit,
  playToastEnter,
  playToastExit
} from '@/infrastructure/animation/app/overlays.js';

/**
 * Aplicação · Entrada (ao montar) e saída (quando `closing` vira true) de uma camada
 * por cima da página. Roda antes da pintura, então nada pisca.
 */
function useOverlayAnimation(ref, closing, enter, exit) {
  useLayoutEffect(() => (ref.current ? enter(ref.current) : undefined), [ref, enter]);
  useLayoutEffect(() => (closing && ref.current ? exit(ref.current) : undefined), [ref, closing, exit]);
}

export function useModalAnimation(ref, closing) {
  useOverlayAnimation(ref, closing, playModalEnter, playModalExit);
}

export function useMenuAnimation(ref, closing) {
  useOverlayAnimation(ref, closing, playMenuEnter, playMenuExit);
}

export function useToastAnimation(ref, closing) {
  useOverlayAnimation(ref, closing, playToastEnter, playToastExit);
}
