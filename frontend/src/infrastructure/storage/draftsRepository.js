/**
 * Infraestrutura · Rascunho do assistente "criar anúncio" (localStorage)
 * Um rascunho por conta, salvo sozinho enquanto o vendedor preenche:
 * - "quickclick:v1:usuario:<id>:rascunho": passo e campos (pequeno, regravado a cada pausa);
 * - "quickclick:v1:usuario:<id>:rascunho_fotos": as fotos (grandes), regravadas só quando mudam.
 */
import { USER_KEYS, nowIso, readJson, removeKey, userKey, writeJson } from './localStore.js';

const keyFor = (accountId) => userKey(accountId, USER_KEYS.DRAFT);
const photosKeyFor = (accountId) => userKey(accountId, USER_KEYS.DRAFT_PHOTOS);

/** As últimas fotos gravadas (a lista do estado muda de referência só quando as fotos mudam). */
let savedPhotos = { accountId: null, photos: null };

export async function getDraft(accountId) {
  const rascunho = readJson(keyFor(accountId), null);
  if (!rascunho) return null;
  const fotos = readJson(photosKeyFor(accountId), null);
  // rascunho do formato anterior: as fotos vinham dentro dos campos
  const data = fotos ? { ...rascunho.dados, photos: fotos } : rascunho.dados;
  return { step: rascunho.etapa, data, savedAt: rascunho.salvo_em };
}

/** Lança StorageFullError (localStore) se as fotos não couberem mais no navegador. */
export async function saveDraft(accountId, { step, data }) {
  const { photos = [], ...fields } = data;
  if (savedPhotos.accountId !== accountId || savedPhotos.photos !== photos) {
    writeJson(photosKeyFor(accountId), photos);
    savedPhotos = { accountId, photos };
  }
  writeJson(keyFor(accountId), { etapa: step, dados: fields, salvo_em: nowIso() });
}

export async function clearDraft(accountId) {
  removeKey(keyFor(accountId));
  removeKey(photosKeyFor(accountId));
  if (savedPhotos.accountId === accountId) savedPhotos = { accountId: null, photos: null };
}
