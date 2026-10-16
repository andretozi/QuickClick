/**
 * Infraestrutura · Autenticação via API com Token JWT
 *
 * Emite e valida tokens JWT nas rotas de login (/api/auth/login) e cadastro (/api/auth/register).
 * O token recebido é persistido na sessão e utilizado para proteger todas as requisições
 * autenticadas e navegação do usuário.
 */
import { ApiError, requestJson } from '../http/httpClient.js';
import {
  ACCOUNT_ERRORS,
  AccountError,
  authenticate,
  createAccount,
  getAccount,
  upsertAccount
} from '../storage/accountsRepository.js';
import { endSession, getSession, startSession } from '../storage/sessionRepository.js';
import { StorageFullError } from '../storage/localStore.js';

export { ACCOUNT_ERRORS } from '../storage/accountsRepository.js';

/** Qualquer falha vira um código estável que a tela sabe explicar. */
export function describeAuthError(error) {
  if (error instanceof AccountError) return error.code;
  if (error instanceof StorageFullError) return error.code;
  if (error instanceof ApiError) {
    if (error.code === 'email_em_uso') return ACCOUNT_ERRORS.EMAIL_TAKEN;
    if (error.code === 'credenciais_invalidas') return ACCOUNT_ERRORS.INVALID_CREDENTIALS;
    return error.code;
  }
  return 'desconhecido';
}

/** @param {{ email: string, password: string }} credentials */
export async function signIn({ email, password }) {
  try {
    const data = await requestJson('/auth/login', {
      method: 'POST',
      body: { email, senha: password }
    });
    const token = data.token;
    const usuario = data.usuario;
    const account = upsertAccount({
      id: usuario.id,
      name: usuario.nome,
      email: usuario.email,
      store: usuario.loja,
      plan: usuario.plano
    });
    await startSession(usuario.id, token);
    return account;
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.code === 'credenciais_invalidas' || error.status === 401) {
        throw new AccountError(ACCOUNT_ERRORS.INVALID_CREDENTIALS);
      }
      if (error.code === 'sem_conexao') {
        const account = await authenticate(email, password);
        await startSession(account.id);
        return account;
      }
    }
    throw error;
  }
}

/** @param {{ name: string, email: string, store: string, password: string }} data */
export async function signUp(data) {
  try {
    const res = await requestJson('/auth/register', {
      method: 'POST',
      body: {
        nome: data.name,
        email: data.email,
        loja: data.store,
        senha: data.password
      }
    });
    const token = res.token;
    const usuario = res.usuario;
    const account = upsertAccount({
      id: usuario.id,
      name: usuario.nome,
      email: usuario.email,
      store: usuario.loja,
      plan: usuario.plano
    });
    await startSession(usuario.id, token);
    return account;
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.code === 'email_em_uso' || error.status === 409) {
        throw new AccountError(ACCOUNT_ERRORS.EMAIL_TAKEN);
      }
      if (error.code === 'sem_conexao') {
        const account = await createAccount(data);
        await startSession(account.id);
        return account;
      }
    }
    throw error;
  }
}

export async function signOut() {
  await endSession();
}

/** Conta logada neste navegador, validando com o token JWT ou null se expirado/inválido. */
export async function restoreSession() {
  const session = await getSession();
  if (!session) return null;

  if (session.token) {
    try {
      const data = await requestJson('/auth/me');
      const account = upsertAccount({
        id: data.id,
        name: data.nome,
        email: data.email,
        store: data.loja,
        plan: data.plano
      });
      return account;
    } catch (error) {
      if (
        error instanceof ApiError &&
        (error.status === 401 || error.code === 'token_invalido' || error.code === 'nao_autenticado')
      ) {
        await endSession();
        return null;
      }
      const account = await getAccount(session.accountId);
      return account;
    }
  }

  const account = await getAccount(session.accountId);
  if (!account) {
    await endSession();
    return null;
  }
  return account;
}
