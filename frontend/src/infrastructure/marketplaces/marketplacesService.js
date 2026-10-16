/**
 * Infraestrutura · Serviço de marketplaces
 *
 * Comunicação direta com a API do backend para listagem, autorização OAuth,
 * monitoramento e publicação de produtos nos marketplaces conectados.
 */
import { ApiError, requestJson } from '../http/httpClient.js';

/** Tipos de erro que a tela sabe explicar. */
export const CONNECTION_ERRORS = {
  PLAN_LIMIT: 'plan-limit',
  COMING_SOON: 'coming-soon',
  NOT_FOUND: 'not-found',
  OFFLINE: 'offline',
  UNKNOWN: 'unknown'
};

const ERROR_BY_CODE = {
  limite_do_plano: CONNECTION_ERRORS.PLAN_LIMIT,
  marketplace_em_breve: CONNECTION_ERRORS.COMING_SOON,
  marketplace_nao_encontrado: CONNECTION_ERRORS.NOT_FOUND,
  sem_conexao: CONNECTION_ERRORS.OFFLINE
};

/** Qualquer falha vira { kind, message }. `message` é o texto do back, quando ele mandou um. */
export function describeError(error) {
  if (error instanceof ApiError) {
    return { kind: ERROR_BY_CODE[error.code] ?? CONNECTION_ERRORS.UNKNOWN, message: error.userMessage };
  }
  return { kind: CONNECTION_ERRORS.UNKNOWN, message: '' };
}

const toPlan = (plano) => plano && { slug: plano.slug, name: plano.nome, limit: plano.limite_marketplaces };

const toSeller = (vendedor) => ({
  name: vendedor.nome,
  plan: toPlan(vendedor.plano),
  connectedCount: vendedor.marketplaces_conectados,
  canConnectMore: vendedor.pode_conectar_mais,
  upgradePlan: toPlan(vendedor.plano_para_mais_marketplaces)
});

const toMarketplace = (marketplace) => ({
  slug: marketplace.slug,
  name: marketplace.nome,
  available: marketplace.status === 'disponivel',
  connected: marketplace.conectado,
  connectedAt: marketplace.conectado_em
});

const marketplaceRoute = (slug, action = '') => `/marketplaces/${encodeURIComponent(slug)}${action}`;

export async function fetchSeller() {
  return toSeller(await requestJson('/me'));
}

export async function fetchMarketplaces() {
  const { marketplaces } = await requestJson('/marketplaces');
  return marketplaces.map(toMarketplace);
}

export async function fetchConnectedMarketplaces() {
  const marketplaces = await fetchMarketplaces();
  return marketplaces
    .filter((m) => m.connected)
    .map((m) => ({
      slug: m.slug,
      nickname: m.name,
      connectedAt: m.connectedAt ?? new Date().toISOString(),
      syncedAt: m.connectedAt ?? new Date().toISOString()
    }));
}

/** Obtém a URL de autorização OAuth real do marketplace para redirecionar o vendedor. */
export async function fetchAuthorizeUrl(slug) {
  const data = await requestJson(marketplaceRoute(slug, '/authorize-url'));
  return data.url;
}

export async function disconnectMarketplace(slug) {
  return toMarketplace(await requestJson(marketplaceRoute(slug, '/connection'), { method: 'DELETE' }));
}

/** Consulta os produtos/anúncios do marketplace para monitoramento. */
export async function fetchMarketplaceProducts(slug) {
  return await requestJson(marketplaceRoute(slug, '/products'));
}

/** Publica um novo anúncio na conta do vendedor no marketplace. */
export async function publishMarketplaceProduct(slug, productData) {
  return await requestJson(marketplaceRoute(slug, '/products'), {
    method: 'POST',
    body: productData
  });
}
