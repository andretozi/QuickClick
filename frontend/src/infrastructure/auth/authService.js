/**
 * Infraestrutura · Autenticação (SIMULADA no navegador)
 *
 * Mesmo formato que a API de login terá: entrar, criar conta, sair e recuperar a
 * sessão ao abrir o site. Hoje tudo mora no localStorage (repositórios desta pasta
 * vizinha, storage/). Quando o back tiver login, troque só o corpo destas funções
 * por chamadas ao httpClient (POST /api/sessao, POST /api/contas, DELETE /api/sessao,
 * GET /api/me): os hooks e as telas não mudam.
 */
import { AccountError, authenticate, createAccount, getAccount } from '../storage/accountsRepository.js';
import { endSession, getSession, startSession } from '../storage/sessionRepository.js';
import { StorageFullError } from '../storage/localStore.js';

export { ACCOUNT_ERRORS } from '../storage/accountsRepository.js';

/** Qualquer falha vira um código estável que a tela sabe explicar. */
export function describeAuthError(error) {
  if (error instanceof AccountError) return error.code;
  if (error instanceof StorageFullError) return error.code;
  return 'desconhecido';
}

/** @param {{ email: string, password: string }} credentials */
export async function signIn({ email, password }) {
  const account = await authenticate(email, password);
  await startSession(account.id);
  return account;
}

/** @param {{ name: string, email: string, store: string, password: string }} data */
export async function signUp(data) {
  const account = await createAccount(data);
  await startSession(account.id);
  return account;
}

export async function signOut() {
  await endSession();
}

/** Conta logada neste navegador, ou null. */
export async function restoreSession() {
  const session = await getSession();
  if (!session) return null;
  const account = await getAccount(session.accountId);
  if (!account) {
    await endSession();
    return null;
  }
  return account;
}
