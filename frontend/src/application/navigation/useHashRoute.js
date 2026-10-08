import { useEffect, useRef, useState } from 'react';
import { getHash, scrollToAnchor, scrollToTop, subscribeToHashChange } from '@/infrastructure/browser/location.js';
import { parseHash } from './routes.js';

const TOP = 'topo';

/**
 * Aplicação · Hook que devolve a rota atual e reage às mudanças da URL.
 * Ao trocar de página, rola para o topo ou, se o link apontou uma seção da landing
 * ("#planos"), até essa seção, depois que a página nova aparece.
 */
export default function useHashRoute() {
  const [route, setRoute] = useState(() => parseHash(getHash()).route);
  const currentRoute = useRef(route);
  const pendingScroll = useRef(null);

  useEffect(() => {
    // Link direto para uma seção (ex.: o site aberto já em "#planos")
    pendingScroll.current = parseHash(getHash()).anchor;

    return subscribeToHashChange(() => {
      const next = parseHash(getHash());
      if (next.route === currentRoute.current) return; // seção da mesma página: o navegador rola sozinho
      currentRoute.current = next.route;
      pendingScroll.current = next.anchor ?? TOP;
      setRoute(next.route);
    });
  }, []);

  useEffect(() => {
    const target = pendingScroll.current;
    if (!target) return;
    pendingScroll.current = null;
    if (target === TOP) scrollToTop();
    else scrollToAnchor(target);
  }, [route]);

  return route;
}
