/**
 * Infraestrutura · Repositório de contas (localStorage)
 *
 * Faz o papel da API de contas: criar, ler, atualizar, conferir a senha e excluir.
 * Não existe conta pré-criada: cada vendedor cria a sua em #/cadastro. Várias contas
 * podem morar no mesmo navegador; os dados de cada uma ficam nas chaves dela.
 * Devolve sempre Promises, como uma chamada de rede. Para trocar pela API de verdade,
 * mantenha as mesmas funções e troque o corpo por chamadas ao httpClient.
 */
import { STORAGE_KEYS, clearUser, newId, nowIso, readJson, simulateLatency, writeJson } from './localStore.js';
import { hashPassword, verifyPassword } from '../security/passwordHasher.js';

/** Códigos de erro estáveis (como os do back). Os textos ficam no domain/content. */
export const ACCOUNT_ERRORS = {
  EMAIL_TAKEN: 'email_em_uso',
  INVALID_CREDENTIALS: 'credenciais_invalidas',
  WRONG_PASSWORD: 'senha_atual_incorreta',
  NOT_FOUND: 'conta_nao_encontrada'
};

export class AccountError extends Error {
  constructor(code) {
    super(code);
    this.name = 'AccountError';
    this.code = code;
  }
}

const normalizeEmail = (email) => String(email ?? '').trim().toLowerCase();

/** JSON guardado (português) → conta do front. A senha nunca sai daqui. */
const toAccount = (conta) =>
  conta
    ? {
        id: conta.id,
        name: conta.nome,
        email: conta.email,
        phone: conta.telefone ?? '',
        store: conta.loja,
        plan: conta.plano,
        avatarColor: conta.cor_avatar ?? 'coral',
        createdAt: conta.criada_em,
        updatedAt: conta.atualizada_em
      }
    : null;

async function load() {
  return readJson(STORAGE_KEYS.ACCOUNTS, []);
}

const save = (contas) => writeJson(STORAGE_KEYS.ACCOUNTS, contas);

export async function getAccount(id) {
  const contas = await load();
  await simulateLatency(90);
  return toAccount(contas.find((conta) => conta.id === id));
}

export async function createAccount({ name, email, store, password }) {
  const contas = await load();
  await simulateLatency(320);
  const normalized = normalizeEmail(email);
  if (contas.some((conta) => conta.email === normalized)) throw new AccountError(ACCOUNT_ERRORS.EMAIL_TAKEN);

  const now = nowIso();
  const conta = {
    id: newId('c'),
    nome: name.trim(),
    email: normalized,
    telefone: '',
    loja: store.trim(),
    plano: 'gratis',
    cor_avatar: 'coral',
    senha: await hashPassword(password),
    criada_em: now,
    atualizada_em: now
  };
  save([...contas, conta]);
  return toAccount(conta);
}

/** Confere email e senha. Erro genérico de propósito: não contamos qual dos dois errou. */
export async function authenticate(email, password) {
  const contas = await load();
  await simulateLatency(420);
  const conta = contas.find((item) => item.email === normalizeEmail(email));
  const ok = conta ? await verifyPassword(password, conta.senha) : false;
  if (!ok) throw new AccountError(ACCOUNT_ERRORS.INVALID_CREDENTIALS);
  return toAccount(conta);
}

/** Atualiza o perfil. `patch` usa os nomes do front: name, email, phone, store, avatarColor. */
export async function updateAccount(id, patch) {
  const contas = await load();
  await simulateLatency(260);
  const index = contas.findIndex((conta) => conta.id === id);
  if (index < 0) throw new AccountError(ACCOUNT_ERRORS.NOT_FOUND);

  const changes = {};
  if (patch.name !== undefined) changes.nome = patch.name.trim();
  if (patch.store !== undefined) changes.loja = patch.store.trim();
  if (patch.phone !== undefined) changes.telefone = patch.phone.trim();
  if (patch.avatarColor !== undefined) changes.cor_avatar = patch.avatarColor;
  if (patch.email !== undefined) {
    const normalized = normalizeEmail(patch.email);
    if (contas.some((conta) => conta.email === normalized && conta.id !== id)) {
      throw new AccountError(ACCOUNT_ERRORS.EMAIL_TAKEN);
    }
    changes.email = normalized;
  }

  const updated = { ...contas[index], ...changes, atualizada_em: nowIso() };
  const next = [...contas];
  next[index] = updated;
  save(next);
  return toAccount(updated);
}

export async function changePassword(id, currentPassword, newPassword) {
  const contas = await load();
  await simulateLatency(360);
  const index = contas.findIndex((conta) => conta.id === id);
  if (index < 0) throw new AccountError(ACCOUNT_ERRORS.NOT_FOUND);
  if (!(await verifyPassword(currentPassword, contas[index].senha))) {
    throw new AccountError(ACCOUNT_ERRORS.WRONG_PASSWORD);
  }
  const next = [...contas];
  next[index] = { ...contas[index], senha: await hashPassword(newPassword), atualizada_em: nowIso() };
  save(next);
}

/** Exclui a conta e tudo o que é dela neste navegador (anúncios, conexões, preferências, rascunho). */
export async function deleteAccount(id, password) {
  const contas = await load();
  await simulateLatency(420);
  const conta = contas.find((item) => item.id === id);
  if (!conta) throw new AccountError(ACCOUNT_ERRORS.NOT_FOUND);
  if (!(await verifyPassword(password, conta.senha))) throw new AccountError(ACCOUNT_ERRORS.WRONG_PASSWORD);
  save(contas.filter((item) => item.id !== id));
  clearUser(id);
}
