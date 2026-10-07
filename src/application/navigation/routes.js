/**
 * Aplicação · Rotas
 *
 * Rotas de página usam "#/" (ex.: "#/login").
 * Hashes sem barra (ex.: "#como", "#preco") são âncoras dentro da página
 * e não trocam de rota — assim o menu rola até a seção em vez de voltar ao topo.
 */
export const ROUTES = {
  LANDING: 'landing',
  LOGIN: 'login'
};

const PATHS = {
  '/': ROUTES.LANDING,
  '/login': ROUTES.LOGIN
};

/**
 * Descobre a rota a partir do hash da URL.
 * @param {string} hash          ex.: "#/login"
 * @param {string} currentRoute  rota atual (mantida quando o hash é só uma âncora)
 */
export function resolveRoute(hash, currentRoute = ROUTES.LANDING) {
  if (hash === '') return ROUTES.LANDING;
  if (!hash.startsWith('#/')) return currentRoute;
  return PATHS[hash.slice(1).toLowerCase()] ?? ROUTES.LANDING;
}
