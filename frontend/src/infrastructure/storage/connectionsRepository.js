/**
 * Infraestrutura · Conexões com marketplaces (SIMULADAS no localStorage)
 *
 * Faz o papel do fluxo OAuth com o marketplace: conectar, desconectar e sincronizar.
 * Nada sai do navegador. Na integração real (veja backend/infrastructure/marketplaces),
 * conectar leva o vendedor até o marketplace, que devolve um código; o back troca o
 * código por um token e guarda o apelido da conta. Aqui o apelido sai do nome da loja.
 */
import { STORAGE_KEYS, USER_KEYS, nowIso, readJson, simulateLatency, userKey, writeJson } from './localStore.js';

import { canConnectMore } from '@/domain/plans/planRules.js';

const SYNC_MS = 2200; // quanto dura uma sincronização simulada

/** Só o Mercado Livre conecta por enquanto (o mesmo que o catálogo do front marca como disponível). */
const AVAILABLE_SLUGS = ['mercado-livre'];

const toConnection = (conexao) => ({
  slug: conexao.marketplace,
  nickname: conexao.apelido,
  connectedAt: conexao.conectado_em,
  syncedAt: conexao.sincronizado_em ?? conexao.conectado_em
});

/** Conexões da conta ("quickclick:v1:usuario:<id>:conexoes"). */
const load = (accountId) => readJson(userKey(accountId, USER_KEYS.CONNECTIONS), []);

const save = (accountId, conexoes) => writeJson(userKey(accountId, USER_KEYS.CONNECTIONS), conexoes);

/** "Bazar da Ana" → "BAZARDAANA" (do jeito que os apelidos aparecem no Mercado Livre). */
function nicknameFor(accountId) {
  const conta = readJson(STORAGE_KEYS.ACCOUNTS, []).find((item) => item.id === accountId);
  const base = String(conta?.loja ?? conta?.nome ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '')
    .slice(0, 20);
  return base || 'MINHALOJA';
}

export async function listConnections(accountId) {
  await simulateLatency(180);
  return load(accountId).map(toConnection);
}

/** Erros estáveis da conexão, como os do back (marketplace_em_breve, limite_do_plano). */
export const CONNECTION_ERRORS = { COMING_SOON: 'marketplace_em_breve', PLAN_LIMIT: 'limite_do_plano' };

export class ConnectionError extends Error {
  constructor(code) {
    super(code);
    this.name = 'ConnectionError';
    this.code = code;
  }
}

/**
 * Conecta (ou devolve a conexão que já existe: conectar duas vezes não dá erro, como no back).
 * Como o back, confere aqui mesmo se o marketplace já está disponível e o limite do plano
 * (a tela também confere, mas quem decide é o "servidor").
 */
export async function connectMarketplace(accountId, slug) {
  await simulateLatency(700);
  const conexoes = load(accountId);
  const existing = conexoes.find((conexao) => conexao.marketplace === slug);
  if (existing) return toConnection(existing);
  if (!AVAILABLE_SLUGS.includes(slug)) throw new ConnectionError(CONNECTION_ERRORS.COMING_SOON);
  const plano = readJson(STORAGE_KEYS.ACCOUNTS, []).find((item) => item.id === accountId)?.plano;
  if (!canConnectMore(plano, conexoes.length)) throw new ConnectionError(CONNECTION_ERRORS.PLAN_LIMIT);
  const now = nowIso();
  const conexao = {
    marketplace: slug,
    apelido: nicknameFor(accountId),
    conectado_em: now,
    sincronizado_em: now
  };
  save(accountId, [...conexoes, conexao]);
  return toConnection(conexao);
}

export async function disconnectMarketplace(accountId, slug) {
  await simulateLatency(520);
  save(accountId, load(accountId).filter((conexao) => conexao.marketplace !== slug));
}

/** Sincroniza pedidos e estoque (simulado: só espera e atualiza a hora da última sincronização). */
export async function syncMarketplace(accountId, slug) {
  await simulateLatency(SYNC_MS);
  const conexoes = load(accountId);
  const index = conexoes.findIndex((conexao) => conexao.marketplace === slug);
  if (index < 0) return null;
  const next = [...conexoes];
  next[index] = { ...conexoes[index], sincronizado_em: nowIso() };
  save(accountId, next);
  return toConnection(next[index]);
}

export const SYNC_DURATION_MS = SYNC_MS;
