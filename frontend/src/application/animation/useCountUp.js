import { useLayoutEffect } from 'react';
import { createAnimator } from '@/infrastructure/animation/core/createAnimator.js';
import { shouldReduceMotion } from '@/infrastructure/animation/core/motion.js';
import { countUp } from '@/infrastructure/animation/core/effects.js';

/**
 * Aplicação · O número conta do zero até `to` quando aparece (e de novo se o valor mudar).
 * Roda antes da pintura: o número nunca aparece vazio. format: 'number' | 'money' (centavos).
 */
export default function useCountUp(ref, { to, format = 'number', delay = 0, duration = 1400 }) {
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return undefined;
    const animator = createAnimator(element);
    countUp(animator, element, { to, from: shouldReduceMotion() ? to : 0, format, delay, duration });
    return animator.dispose;
  }, [ref, to, format, delay, duration]);
}
