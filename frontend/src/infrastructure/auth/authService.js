/**
 * Infraestrutura · Autenticação e Gestão de Conta via API (Token JWT e Google OAuth)
 *
 * Centraliza todas as operações de sessão e autoatendimento de conta com o back-end:
 * login, cadastro, Google OAuth, leitura/edição de perfil, troca de senha e exclusão.
 */
import { ApiError, requestJson } from '../http/httpClient.js';
import {
  ACCOUNT_ERRORS,
  AccountError,
  getAccount,
  purgeLocalAccount,
  upsertAccount
} from '../storage/accountsRepository.js';
import { endSession, getSession, startSession } from '../storage/sessionRepository.js';
import { StorageFullError } from '../storage/localStore.js';

export { ACCOUNT_ERRORS, AccountError } from '../storage/accountsRepository.js';

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
    if (error.code === 'senha_atual_incorreta') return ACCOUNT_ERRORS.WRONG_PASSWORD;
    if (error.code === 'confirmacao_incorreta') return ACCOUNT_ERRORS.CONFIRMATION_MISMATCH;
    return error.code;
  }
  return 'desconhecido';
}

async function persistJwtSession(accessToken, usuarioData = null, { provider = null, accountPatch = null } = {}) {
  const usuario =
    usuarioData ??
    (await requestJson('/auth/me', {
      headers: { Authorization: `Bearer ${accessToken}` }
    }));
  const account = upsertAccount(accountPatch ? { ...usuario, ...accountPatch } : usuario);
  await startSession(usuario.id, accessToken, provider);
  return account;
}

/** @param {{ email: string, password: string }} credentials */
export async function signIn({ email, password }) {
  try {
    const data = await requestJson('/auth/login', {
      method: 'POST',
      body: { email, senha: password }
    });
    return await persistJwtSession(data.token, data.usuario, { provider: 'password' });
  } catch (error) {
    if (error instanceof ApiError && (error.code === 'credenciais_invalidas' || error.status === 401)) {
      throw new AccountError(ACCOUNT_ERRORS.INVALID_CREDENTIALS);
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
    const account = await persistJwtSession(data.access_token, null, {
      provider: 'google',
      accountPatch: { hasPassword: false }
    });
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
    return await persistJwtSession(res.access_token, res.usuario, {
      provider: 'google',
      accountPatch: { hasPassword: false }
    });
  } catch (error) {
    if (error instanceof ApiError && (error.code === 'email_em_uso' || error.status === 409)) {
      throw new AccountError(ACCOUNT_ERRORS.EMAIL_TAKEN);
    }
    throw error;
  }
}

/** @param {{ name: string, email: string, store: string, password: string, adult?: boolean }} data */
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
    return await persistJwtSession(res.token, res.usuario, { provider: 'password' });
  } catch (error) {
    if (error instanceof ApiError && (error.code === 'email_em_uso' || error.status === 409)) {
      throw new AccountError(ACCOUNT_ERRORS.EMAIL_TAKEN);
    }
    throw error;
  }
}

/**
 * Persiste nome, email e loja no servidor (/api/auth/me) e sincroniza telefone/avatar localmente.
 * @param {{ name: string, email: string, phone?: string, store: string, avatarColor?: string }} patch
 */
export async function updateProfile(patch) {
  try {
    const session = await getSession();
    const usuario = await requestJson('/auth/me', {
      method: 'PUT',
      body: {
        nome: patch.name,
        email: patch.email,
        loja: patch.store
      }
    });
    return upsertAccount({
      ...usuario,
      ...(session?.provider === 'google' ? { hasPassword: false } : {}),
      phone: patch.phone,
      avatarColor: patch.avatarColor
    });
  } catch (error) {
    if (error instanceof ApiError && (error.code === 'email_em_uso' || error.status === 409)) {
      throw new AccountError(ACCOUNT_ERRORS.EMAIL_TAKEN);
    }
    throw error;
  }
}

/** Altera a senha local da conta autenticada (/api/auth/me/senha). */
export async function changeAccountPassword(currentPassword, newPassword) {
  try {
    await requestJson('/auth/me/senha', {
      method: 'PUT',
      body: {
        senha_atual: currentPassword,
        nova_senha: newPassword
      }
    });
  } catch (error) {
    if (error instanceof ApiError && error.code === 'senha_atual_incorreta') {
      throw new AccountError(ACCOUNT_ERRORS.WRONG_PASSWORD);
    }
    throw error;
  }
}

/** Exclui definitivamente a conta autenticada mediante confirmação do nome da loja. */
export async function removeCurrentAccount(accountId, confirmation) {
  try {
    await requestJson('/auth/me', {
      method: 'DELETE',
      body: { confirmacao: confirmation }
    });
    if (accountId !== undefined && accountId !== null) {
      purgeLocalAccount(accountId);
    }
    await endSession();
  } catch (error) {
    if (error instanceof ApiError && error.code === 'confirmacao_incorreta') {
      throw new AccountError(ACCOUNT_ERRORS.CONFIRMATION_MISMATCH);
    }
    throw error;
  }
}

export async function signOut() {
  await endSession();
}

/** Conta logada neste navegador, validando o token JWT contra /api/auth/me. */
export async function restoreSession() {
  const session = await getSession();
  if (!session?.token) {
    if (session) await endSession();
    return null;
  }

  const isGoogleSession = session.provider === 'google';
  try {
    const data = await requestJson('/auth/me');
    return upsertAccount(isGoogleSession ? { ...data, hasPassword: false } : data);
  } catch (error) {
    if (
      error instanceof ApiError &&
      (error.status === 401 || error.status === 404 || error.code === 'token_invalido' || error.code === 'nao_autenticado')
    ) {
      await endSession();
      return null;
    }
    const cached = await getAccount(session.accountId);
    return cached && isGoogleSession ? { ...cached, hasPassword: false } : cached;
  }
}
