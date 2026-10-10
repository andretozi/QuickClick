/**
 * Infraestrutura · Armazenamento local
 *
 * Por enquanto o "servidor" da área logada é o localStorage do navegador. Todas as
 * chaves usam o prefixo versionado "quickclick:v1:". Se o formato dos dados mudar,
 * troque para v2 e migre. Não existe conta pré-criada: cada vendedor cria a sua.
 *
 * O JSON guardado imita o da API futura (nomes em português, como no back). Quem
 * traduz para os objetos do front são os repositórios desta pasta.
 *
 * Se o navegador bloquear o localStorage (aba anônima restrita, por exemplo), os
 * dados ficam só na memória até a página fechar, e a tela continua funcionando.
 */

const PREFIX = 'quickclick:v1:';

/**
 * Nome de cada coleção guardada.
 * Globais (do navegador): contas e sessão.
 * Por conta: use userKey(id, USER_KEYS.X), que vira "quickclick:v1:usuario:<id>:anuncios".
 */
export const STORAGE_KEYS = {
  ACCOUNTS: 'contas',
  SESSION: 'sessao'
};

export const USER_KEYS = {
  LISTINGS: 'anuncios',
  CONNECTIONS: 'conexoes',
  PREFERENCES: 'preferencias',
  DRAFT: 'rascunho'
};

const userPrefix = (accountId) => `usuario:${accountId}:`;

/** Chave de uma coleção da conta: userKey('c_1', 'anuncios') → "usuario:c_1:anuncios". */
export function userKey(accountId, collection) {
  return `${userPrefix(accountId)}${collection}`;
}

/**
 * Formato antigo (antes de as chaves levarem o id da conta): coleções globais e a conta
 * de demonstração criada sozinha. Some na primeira abertura com esta versão.
 */
const LEGACY_KEYS = ['anuncios', 'conexoes', 'preferencias', 'rascunhos', 'semente'];
const LEGACY_DEMO_EMAIL = 'demo@quickclick.com.br';

/** Latência simulada de uma ida ao "servidor", para a tela ter estado de carregando. */
const DEFAULT_LATENCY_MS = 160;

/** O navegador recusou gravar: o espaço do site acabou (fotos grandes, por exemplo). */
export class StorageFullError extends Error {
  constructor() {
    super('armazenamento_cheio');
    this.name = 'StorageFullError';
    this.code = 'armazenamento_cheio';
  }
}

const memory = new Map();
let browserStorage;

/** localStorage, se o navegador deixar usar; senão null (e usamos a memória). */
function storage() {
  if (browserStorage !== undefined) return browserStorage;
  try {
    const probe = `${PREFIX}teste`;
    window.localStorage.setItem(probe, '1');
    window.localStorage.removeItem(probe);
    browserStorage = window.localStorage;
  } catch {
    browserStorage = null;
  }
  if (browserStorage) dropLegacyData(browserStorage);
  return browserStorage;
}

/** Tira as coleções globais antigas e a conta de demonstração (e a sessão dela, se houver). */
function dropLegacyData(store) {
  if (store.getItem(`${PREFIX}semente`) === null) return;
  LEGACY_KEYS.forEach((name) => store.removeItem(PREFIX + name));
  try {
    const contas = JSON.parse(store.getItem(`${PREFIX}${STORAGE_KEYS.ACCOUNTS}`) ?? '[]');
    const demo = contas.find((conta) => conta.email === LEGACY_DEMO_EMAIL);
    if (!demo) return;
    store.setItem(`${PREFIX}${STORAGE_KEYS.ACCOUNTS}`, JSON.stringify(contas.filter((conta) => conta !== demo)));
    const sessao = JSON.parse(store.getItem(`${PREFIX}${STORAGE_KEYS.SESSION}`) ?? 'null');
    if (sessao?.conta_id === demo.id) store.removeItem(`${PREFIX}${STORAGE_KEYS.SESSION}`);
  } catch {
    // dados antigos corrompidos: as contas ficam como estão
  }
}

function isQuotaError(error) {
  return (
    error instanceof DOMException &&
    (error.name === 'QuotaExceededError' || error.name === 'NS_ERROR_DOM_QUOTA_REACHED' || error.code === 22)
  );
}

/** Lê uma coleção. Devolve `fallback` se ela não existe ou está corrompida. */
export function readJson(name, fallback) {
  const key = PREFIX + name;
  const store = storage();
  const raw = store ? store.getItem(key) : memory.get(key);
  if (raw === null || raw === undefined) return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

/** Grava uma coleção inteira. Lança StorageFullError quando o espaço acaba. */
export function writeJson(name, value) {
  const key = PREFIX + name;
  const raw = JSON.stringify(value);
  const store = storage();
  if (!store) {
    memory.set(key, raw);
    return;
  }
  try {
    store.setItem(key, raw);
  } catch (error) {
    if (isQuotaError(error)) throw new StorageFullError();
    throw error;
  }
}

export function removeKey(name) {
  const key = PREFIX + name;
  memory.delete(key);
  storage()?.removeItem(key);
}

/** Apaga as chaves que começam com o prefixo dado (dentro de "quickclick:v1:"). */
function removeByPrefix(prefix) {
  const full = PREFIX + prefix;
  [...memory.keys()].filter((key) => key.startsWith(full)).forEach((key) => memory.delete(key));
  const store = storage();
  if (!store) return;
  const keys = [];
  for (let i = 0; i < store.length; i += 1) {
    const key = store.key(i);
    if (key?.startsWith(full)) keys.push(key);
  }
  keys.forEach((key) => store.removeItem(key));
}

/** Apaga tudo o que é de uma conta (anúncios, conexões, preferências, rascunho). */
export function clearUser(accountId) {
  removeByPrefix(userPrefix(accountId));
}

/** Espera um pouco, como uma chamada de rede. */
export function simulateLatency(ms = DEFAULT_LATENCY_MS) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

/** Identificador curto e aleatório, ex.: "a_k3f9a2x7". */
export function newId(prefix) {
  const bytes = new Uint8Array(6);
  crypto.getRandomValues(bytes);
  const random = Array.from(bytes, (byte) => (byte % 36).toString(36)).join('');
  return `${prefix}_${Date.now().toString(36).slice(-4)}${random}`;
}

/** Agora, no formato guardado (ISO). */
export function nowIso() {
  return new Date().toISOString();
}
