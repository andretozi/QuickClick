/**
 * Infraestrutura · Rascunho do assistente "criar anúncio" (localStorage)
 * Um rascunho por conta ("quickclick:v1:usuario:<id>:rascunho"), salvo sozinho
 * enquanto o vendedor preenche.
 */
import { USER_KEYS, nowIso, readJson, removeKey, userKey, writeJson } from './localStore.js';

const keyFor = (accountId) => userKey(accountId, USER_KEYS.DRAFT);

export async function getDraft(accountId) {
  const rascunho = readJson(keyFor(accountId), null);
  return rascunho ? { step: rascunho.etapa, data: rascunho.dados, savedAt: rascunho.salvo_em } : null;
}

/** Lança StorageFullError (localStore) se as fotos não couberem mais no navegador. */
export async function saveDraft(accountId, { step, data }) {
  writeJson(keyFor(accountId), { etapa: step, dados: data, salvo_em: nowIso() });
}

export async function clearDraft(accountId) {
  removeKey(keyFor(accountId));
}
