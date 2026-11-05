/**
 * Infraestrutura · Autenticação via API com Token JWT e Google OAuth
 *
 * Emite e valida tokens JWT nas rotas de login (/api/auth/login), cadastro (/api/auth/register)
 * e Google OAuth (/api/auth/google e /api/auth/google/complete-registration).
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

/** Lê o Client ID público do Google exposto no build do Vite ou servido em runtime pelo Azure. */
export function getBuildGoogleClientId() {
  return String(import.meta.env.VITE_GOOGLE_CLIENT_ID || import.meta.env.GOOGLE_CLIENT_ID || '').trim();
}

export async function fetchGoogleClientId() {
  const fromBuild = getBuildGoogleClientId();
  if (fromBuild) return fromBuild;
  try {
    const data = await requestJson('/auth/google/config');
    return String(data?.client_id ?? '').trim();
  } catch {
    return '';
  }
}

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

async function persistJwtSession(accessToken, usuarioData = null) {
  const usuario =
    usuarioData ??
    (await requestJson('/auth/me', {
      headers: { Authorization: `Bearer ${accessToken}` }
    }));
  const account = upsertAccount({
    id: usuario.id,
    name: usuario.nome || usuario.loja || usuario.email,
    email: usuario.email,
    store: usuario.loja,
    plan: usuario.plano
  });
  await startSession(usuario.id, accessToken);
  return account;
}

/** @param {{ email: string, password: string }} credentials */
export async function signIn({ email, password }) {
  try {
    const data = await requestJson('/auth/login', {
      method: 'POST',
      body: { email, senha: password }
    });
    return await persistJwtSession(data.token, data.usuario);
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

/**
 * Envia o ID Token do Google para /api/auth/google.
 * @param {string} token
 * @returns {Promise<{ status: 'login', account: object } | { status: 'needs_store_name', email: string, googleId: string }>}
 */
export async function authenticateWithGoogle(token) {
  const data = await requestJson('/auth/google', {
    method: 'POST',
    body: { token }
  });
  if (data.status === 'login') {
    const accessToken = data.access_token ?? data.token;
    const account = await persistJwtSession(accessToken, data.usuario ?? null);
    return { status: 'login', account };
  }
  return {
    status: 'needs_store_name',
    email: data.email,
    googleId: data.google_id
  };
}

/**
 * Conclui o cadastro via Google informando o nome da loja e inicia a sessão com o JWT recebido.
 * @param {{ email: string, googleId: string, storeName: string }} payload
 */
export async function completeGoogleRegistration({ email, googleId, storeName }) {
  try {
    const res = await requestJson('/auth/google/complete-registration', {
      method: 'POST',
      body: {
        email,
        google_id: googleId,
        store_name: storeName
      }
    });
    const accessToken = res.access_token ?? res.token;
    return await persistJwtSession(accessToken, res.usuario ?? null);
  } catch (error) {
    if (error instanceof ApiError && (error.code === 'email_em_uso' || error.status === 409)) {
      throw new AccountError(ACCOUNT_ERRORS.EMAIL_TAKEN);
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
        senha: data.password,
        maior_de_idade: Boolean(data.adult)
      }
    });
    return await persistJwtSession(res.token, res.usuario);
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
        name: data.nome || data.loja || data.email,
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
