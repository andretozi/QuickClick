import { useCallback } from 'react';
import { press } from '@/infrastructure/animation/core/effects.js';

/** Aplicação · Devolve um onClick que faz o elemento clicado "afundar" e voltar. */
export default function usePressFeedback() {
  return useCallback((event) => press(event.currentTarget), []);
}
