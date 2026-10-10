import { useCallback, useEffect, useRef } from 'react';
import { createCelebration } from '@/infrastructure/animation/app/celebrate.js';

/**
 * Aplicação · Liga a comemoração (cursor, clique e partículas que formam a palavra)
 * ao elemento raiz e devolve `celebrate(word)`, que resolve quando a animação termina.
 */
export default function useCelebration(rootRef) {
  const celebration = useRef(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return undefined;
    celebration.current = createCelebration(root);
    return () => {
      celebration.current?.dispose();
      celebration.current = null;
    };
  }, [rootRef]);

  return useCallback((word) => celebration.current?.play(word) ?? Promise.resolve(), []);
}
