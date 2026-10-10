/**
 * Aplicação · Rotas
 *
 * Páginas usam "#/" (ex.: "#/login", "#/anuncios/a_k3f9"). Hashes sem barra
 * (ex.: "#como", "#planos") são seções da landing: na própria landing o navegador
 * só rola até a seção; em outra página, a landing abre já na seção.
 *
 * Rotas privadas exigem conta logada: sem sessão, viram "#/login?volta=..." e,
 * depois de entrar, o vendedor volta para onde queria ir.
 */
export const ROUTES = {
  LANDING: 'landing',
  LOGIN: 'login',
  SIGNUP: 'signup',
  DASHBOARD: 'dashboard',
  NEW_LISTING: 'new-listing',
  LISTING: 'listing',
  MARKETPLACES: 'marketplaces',
  SETTINGS: 'settings',
  NOT_FOUND: 'not-found'
};

/** Ordem importa: "/anuncios/novo" precisa vir antes de "/anuncios/:id". */
const ROUTE_TABLE = [
  { route: ROUTES.LANDING, path: '/' },
  { route: ROUTES.LOGIN, path: '/login', guestOnly: true },
  { route: ROUTES.SIGNUP, path: '/cadastro', guestOnly: true },
  { route: ROUTES.DASHBOARD, path: '/painel', private: true },
  { route: ROUTES.NEW_LISTING, path: '/anuncios/novo', private: true },
  { route: ROUTES.LISTING, path: '/anuncios/:id', private: true },
  { route: ROUTES.MARKETPLACES, path: '/marketplaces', private: true },
  { route: ROUTES.SETTINGS, path: '/configuracoes', private: true }
];

const RETURN_PARAM = 'volta';

/** Endereço de cada página sem parâmetros (ex.: ROUTE_HASH[ROUTES.DASHBOARD] → "#/painel"). */
export const ROUTE_HASH = Object.fromEntries(
  ROUTE_TABLE.filter(({ path }) => !path.includes(':')).map(({ route, path }) => [route, `#${path}`])
);

const definitionOf = (route) => ROUTE_TABLE.find((item) => item.route === route);

/** A rota exige conta logada? */
export function isPrivateRoute(route) {
  return Boolean(definitionOf(route)?.private);
}

/** A rota é só para quem ainda não entrou (login e cadastro)? */
export function isGuestOnlyRoute(route) {
  return Boolean(definitionOf(route)?.guestOnly);
}

function safeDecode(text) {
  try {
    return decodeURIComponent(text);
  } catch {
    return text;
  }
}

const splitPath = (path) => path.split('/').filter(Boolean);

function parseQuery(text) {
  const query = {};
  new URLSearchParams(text).forEach((value, key) => {
    query[key] = value;
  });
  return query;
}

/** Procura a rota que casa com o caminho. Partes fixas ignoram maiúsculas; parâmetros não. */
function matchPath(path) {
  const segments = splitPath(path);
  for (const definition of ROUTE_TABLE) {
    const pattern = splitPath(definition.path);
    if (pattern.length !== segments.length) continue;
    const params = {};
    const matches = pattern.every((part, index) => {
      if (part.startsWith(':')) {
        params[part.slice(1)] = safeDecode(segments[index]);
        return true;
      }
      return part === segments[index].toLowerCase();
    });
    if (matches) return { route: definition.route, params };
  }
  return { route: ROUTES.NOT_FOUND, params: {} };
}

/**
 * Lê o hash da URL.
 * @param {string} hash  ex.: "#/anuncios/a_k3f9", "#/login?volta=%2Fpainel", "#planos" ou ""
 * @returns {{ route: string, params: object, query: object, path: string, anchor: string | null }}
 */
export function parseHash(hash) {
  if (!hash || hash === '#' || hash === '#/') {
    return { route: ROUTES.LANDING, params: {}, query: {}, path: '/', anchor: null };
  }
  if (!hash.startsWith('#/')) {
    return { route: ROUTES.LANDING, params: {}, query: {}, path: '/', anchor: safeDecode(hash.slice(1)) };
  }
  const [rawPath, rawQuery = ''] = hash.slice(1).split('?');
  const path = rawPath.length > 1 ? rawPath.replace(/\/+$/, '') : rawPath;
  const { route, params } = matchPath(path);
  return { route, params, query: parseQuery(rawQuery), path, anchor: null };
}

/** Monta o endereço de uma página com parâmetros: hrefFor(ROUTES.LISTING, { id }) → "#/anuncios/a_k3f9". */
export function hrefFor(route, params = {}) {
  const definition = definitionOf(route);
  if (!definition) return ROUTE_HASH[ROUTES.LANDING];
  const path = definition.path.replace(/:(\w+)/g, (_, name) => encodeURIComponent(params[name] ?? ''));
  return `#${path}`;
}

/** "#/login?volta=..." para quem tentou abrir uma página privada sem estar logado. */
export function loginHrefFor(returnPath) {
  return `${ROUTE_HASH[ROUTES.LOGIN]}?${RETURN_PARAM}=${encodeURIComponent(returnPath)}`;
}

/**
 * Para onde ir depois de entrar. Só aceita caminhos de páginas conhecidas que exigem
 * login; qualquer outra coisa (ou nada) leva ao painel.
 */
export function returnHrefFrom(query) {
  const target = query?.[RETURN_PARAM];
  if (target && target.startsWith('/')) {
    const { route } = matchPath(target.split('?')[0]);
    if (isPrivateRoute(route)) return `#${target}`;
  }
  return ROUTE_HASH[ROUTES.DASHBOARD];
}

/** Endereço de um anúncio: "#/anuncios/a_k3f9". */
export function hrefForListing(id) {
  return hrefFor(ROUTES.LISTING, { id });
}
