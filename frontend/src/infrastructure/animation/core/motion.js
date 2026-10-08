import { MOTION_CONFIG } from './config.js';

/** Curvas de animação compartilhadas (as mesmas dos tokens CSS). */
export const EASE_OUT_EXPO = 'cubic-bezier(.16,1,.3,1)';
export const EASE_SPRING = 'cubic-bezier(.34,1.56,.64,1)';
export const EASE_DRAW = 'cubic-bezier(.65,0,.35,1)';

/** Intensidade do movimento: distância dos deslocamentos e uso de desfoque. */
const INTENSITY = {
  sutil: { amplitude: 0.4, blur: false },
  equilibrada: { amplitude: 0.7, blur: true },
  cinematografica: { amplitude: 1, blur: true }
};

/** true quando o sistema do usuário pede menos movimento. */
function systemPrefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

/** true só quando a configuração manda respeitar o "reduzir movimento" E o sistema pede isso. */
export function shouldReduceMotion() {
  return MOTION_CONFIG.respectReducedMotion && systemPrefersReducedMotion();
}

/** Parâmetros de movimento já resolvidos a partir da configuração. */
export function getMotionSettings() {
  const intensity = INTENSITY[MOTION_CONFIG.intensity] ?? INTENSITY.cinematografica;
  return { ...intensity, loop: MOTION_CONFIG.loopScenes, parallax: MOTION_CONFIG.parallax };
}
