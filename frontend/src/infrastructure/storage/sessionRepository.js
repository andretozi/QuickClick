/**
 * Infraestrutura · Repositório da sessão (localStorage)
 * Guarda a conta logada e o token JWT para autenticação nas requisições.
 */
import { STORAGE_KEYS, nowIso, readJson, removeKey, simulateLatency, writeJson } from './localStore.js';

export async function getSession() {
  await simulateLatency(80);
  const sessao = readJson(STORAGE_KEYS.SESSION, null);
  return sessao ? { accountId: sessao.conta_id, startedAt: sessao.iniciada_em, token: sessao.token ?? null } : null;
}

export async function startSession(accountId, token = null) {
  writeJson(STORAGE_KEYS.SESSION, { conta_id: accountId, token, iniciada_em: nowIso() });
}

export async function endSession() {
  await simulateLatency(120);
  removeKey(STORAGE_KEYS.SESSION);
}

/** Recupera o token JWT de forma síncrona para anexar aos cabeçalhos HTTP. */
export function getStoredToken() {
  const sessao = readJson(STORAGE_KEYS.SESSION, null);
  return sessao?.token ?? null;
}
