import { useEffect, useLayoutEffect } from 'react';
import { placeIndicator, watchIndicator } from '@/infrastructure/animation/ui/indicator.js';

/** Aplicação · O indicador do grupo anda com mola até a opção ativa sempre que `value` muda. */
export default function useIndicator(containerRef, value) {
  useLayoutEffect(() => (containerRef.current ? placeIndicator(containerRef.current) : undefined), [containerRef, value]);
  useEffect(() => (containerRef.current ? watchIndicator(containerRef.current) : undefined), [containerRef]);
}
