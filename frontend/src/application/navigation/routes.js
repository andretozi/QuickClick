/**
 * Aplicação · Rotas
 *
 * Páginas usam "#/" (ex.: "#/login", "#/marketplaces").
 * Hashes sem barra (ex.: "#como", "#planos") são seções da landing: na própria landing
 * o navegador só rola até a seção; em outra página, a landing abre já na seção.
 */
export const ROUTES = {
  LANDING: 'landing',
  LOGIN: 'login',
  MARKETPLACES: 'marketplaces'
};

/** Endereço de cada página. */
export const ROUTE_HASH = {
  [ROUTES.LANDING]: '#/',
  [ROUTES.LOGIN]: '#/login',
  [ROUTES.MARKETPLACES]: '#/marketplaces'
};

const ROUTE_BY_PATH = Object.fromEntries(Object.entries(ROUTE_HASH).map(([route, hash]) => [hash.slice(1), route]));

/**
 * Lê o hash da URL e diz qual página abrir e, se houver, a seção da landing.
 * @param {string} hash  ex.: "#/login", "#planos" ou ""
 * @returns {{ route: string, anchor: string | null }}
 */
export function parseHash(hash) {
  if (!hash || hash === '#') return { route: ROUTES.LANDING, anchor: null };
  if (hash.startsWith('#/')) {
    return { route: ROUTE_BY_PATH[hash.slice(1).toLowerCase()] ?? ROUTES.LANDING, anchor: null };
  }
  return { route: ROUTES.LANDING, anchor: decodeURIComponent(hash.slice(1)) };
}
