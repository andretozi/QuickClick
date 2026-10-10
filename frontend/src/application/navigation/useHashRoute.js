import { useEffect, useRef, useState } from 'react';
import { getHash, scrollToAnchor, scrollToTop, subscribeToHashChange } from '@/infrastructure/browser/location.js';
import { focusPageStart } from '@/infrastructure/browser/focus.js';
import { ROUTES, parseHash } from './routes.js';

const TOP = 'topo';

const sameAddress = (a, b) =>
  a.route === b.route && a.path === b.path && JSON.stringify(a.query) === JSON.stringify(b.query);

/**
 * Aplicação · Hook que devolve a página atual ({ route, params, query, path }) e
 * reage às mudanças da URL.
 * Ao trocar de página, rola para o topo (ou até a seção da landing que o link
 * apontou, ex.: "#planos") e leva o foco do teclado para o começo da página nova.
 */
export default function useHashRoute() {
  const [location, setLocation] = useState(() => parseHash(getHash()));
  const current = useRef(location);
  const pendingScroll = useRef(null);
  const firstRender = useRef(true);

  useEffect(() => {
    // Link direto para uma seção (ex.: o site aberto já em "#planos")
    pendingScroll.current = parseHash(getHash()).anchor;

    return subscribeToHashChange(() => {
      const next = parseHash(getHash());
      // Seção da landing estando na landing: o navegador rola sozinho
      if (next.route === ROUTES.LANDING && current.current.route === ROUTES.LANDING) return;
      if (sameAddress(next, current.current)) return;
      current.current = next;
      pendingScroll.current = next.anchor ?? TOP;
      setLocation(next);
    });
  }, []);

  useEffect(() => {
    const target = pendingScroll.current;
    const isFirst = firstRender.current;
    firstRender.current = false;
    if (!target) return;
    pendingScroll.current = null;
    if (target === TOP) {
      scrollToTop();
      if (!isFirst) focusPageStart();
    } else {
      scrollToAnchor(target);
    }
  }, [location]);

  return location;
}
