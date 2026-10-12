import { useEffect, useRef } from 'react';

/**
 * Aplicação · Diz se o componente ainda está na tela.
 * Depois de uma espera (chamada ao "servidor", animação), confira `mounted.current`
 * antes de mexer no estado: a tela pode ter mudado no meio do caminho.
 */
export default function useMountedRef() {
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  return mounted;
}
