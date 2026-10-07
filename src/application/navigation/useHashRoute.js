import { useEffect, useRef, useState } from 'react';
import { getHash, scrollToTop, subscribeToHashChange } from '@/infrastructure/browser/location.js';
import { resolveRoute } from './routes.js';

/** Aplicação · Hook que devolve a rota atual e reage às mudanças da URL. */
export default function useHashRoute() {
  const [route, setRoute] = useState(() => resolveRoute(getHash()));
  const currentRoute = useRef(route);

  useEffect(
    () =>
      subscribeToHashChange(() => {
        const next = resolveRoute(getHash(), currentRoute.current);
        if (next === currentRoute.current) return; // era só uma âncora
        currentRoute.current = next;
        setRoute(next);
        scrollToTop();
      }),
    []
  );

  return route;
}
