import { useEffect } from 'react';
import { runLoginAnimations, pressAnimation } from '../animations/login.js';

/**
 * Hook fino que amarra o setup/teardown de src/animations/login.js
 * ao ciclo de vida React.
 */
export default function useLoginAnimations(rootRef, options) {
  const ambient = options?.ambient;
  const respectReducedMotion = options?.respectReducedMotion;

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return undefined;
    return runLoginAnimations(el, { ambient, respectReducedMotion });
  }, [rootRef, ambient, respectReducedMotion]);
}

export { pressAnimation };
