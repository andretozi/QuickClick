/**
 * Infraestrutura · Repositório da sessão (localStorage)
 * Guarda só qual conta está logada neste navegador. Com o back, vira um cookie de sessão.
 */
import { STORAGE_KEYS, nowIso, readJson, removeKey, simulateLatency, writeJson } from './localStore.js';

export async function getSession() {
  await simulateLatency(80);
  const sessao = readJson(STORAGE_KEYS.SESSION, null);
  return sessao ? { accountId: sessao.conta_id, startedAt: sessao.iniciada_em } : null;
}

export async function startSession(accountId) {
  writeJson(STORAGE_KEYS.SESSION, { conta_id: accountId, iniciada_em: nowIso() });
}

export async function endSession() {
  await simulateLatency(120);
  removeKey(STORAGE_KEYS.SESSION);
}
