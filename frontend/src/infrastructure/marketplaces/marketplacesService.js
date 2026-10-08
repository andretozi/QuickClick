/**
 * Infraestrutura · Serviço de marketplaces
 *
 * Conversa com a API do back e traduz o JSON (em português) para o formato do front.
 * A autorização OAuth ainda é simulada no back: aqui o "Autorizando…" dura um instante,
 * como se o vendedor tivesse ido até o marketplace e voltado. Com a integração real,
 * connectMarketplace passa a levar o vendedor para a URL de autorização do marketplace.
 */
import { ApiError, requestJson } from '@/infrastructure/http/httpClient.js';

const SIMULATED_AUTHORIZATION_MS = 1500; // tempo do "Autorizando…" quando dá certo
const MIN_FEEDBACK_MS = 450; // quando dá errado, o suficiente para a tela não piscar

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

const waitUntil = (timestamp) => new Promise((resolve) => setTimeout(resolve, Math.max(0, timestamp - Date.now())));

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
  connected: marketplace.conectado
});

const connectionPath = (slug) => `/marketplaces/${encodeURIComponent(slug)}/connection`;

export async function fetchSeller() {
  return toSeller(await requestJson('/me'));
}

export async function fetchMarketplaces() {
  const { marketplaces } = await requestJson('/marketplaces');
  return marketplaces.map(toMarketplace);
}

export async function connectMarketplace(slug) {
  const startedAt = Date.now();
  try {
    const marketplace = await requestJson(connectionPath(slug), { method: 'POST' });
    await waitUntil(startedAt + SIMULATED_AUTHORIZATION_MS);
    return toMarketplace(marketplace);
  } catch (error) {
    await waitUntil(startedAt + MIN_FEEDBACK_MS);
    throw error;
  }
}

export async function disconnectMarketplace(slug) {
  return toMarketplace(await requestJson(connectionPath(slug), { method: 'DELETE' }));
}
