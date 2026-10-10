import { useLayoutEffect } from 'react';
import { playWelcome } from '@/infrastructure/animation/dashboard/welcome.js';

/** Aplicação · Toca a comemoração das boas vindas quando o banner aparece. */
export default function useWelcomeAnimation(ref) {
  useLayoutEffect(() => (ref.current ? playWelcome(ref.current) : undefined), [ref]);
}
