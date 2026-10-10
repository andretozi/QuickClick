/**
 * Aplicação · Sessão do vendedor (compartilhada por todas as telas)
 *
 * Uma store pequena lida com useSyncExternalStore: o navbar, a guarda de rotas e as
 * páginas enxergam a mesma conta sem precisar de Context. Quem fala com o "servidor"
 * é o authService (infraestrutura); aqui só guardamos o resultado e avisamos as telas.
 */
import {
  restoreSession,
  signIn as signInRequest,
  signOut as signOutRequest,
  signUp as signUpRequest
} from '@/infrastructure/auth/authService.js';

export const SESSION_STATUS = { CHECKING: 'checking', GUEST: 'guest', SIGNED_IN: 'signed-in' };

let state = {
  status: SESSION_STATUS.CHECKING,
  account: null,
  /** true logo depois de criar a conta: o painel mostra as boas vindas uma vez */
  welcome: false,
  /** true logo depois de sair: a guarda leva para a landing, não para o login */
  signedOut: false
};

const listeners = new Set();
let restoring = null;

function setState(patch) {
  state = { ...state, ...patch };
  listeners.forEach((listener) => listener());
}

/** Na primeira vez que alguém olha a sessão, descobre se já existe uma conta logada. */
function restoreOnce() {
  if (!restoring) {
    restoring = restoreSession()
      .then((account) => {
        if (state.status === SESSION_STATUS.CHECKING) {
          setState({ status: account ? SESSION_STATUS.SIGNED_IN : SESSION_STATUS.GUEST, account });
        }
      })
      .catch(() => {
        if (state.status === SESSION_STATUS.CHECKING) setState({ status: SESSION_STATUS.GUEST, account: null });
      });
  }
  return restoring;
}

export function subscribeToSession(listener) {
  listeners.add(listener);
  restoreOnce();
  return () => listeners.delete(listener);
}

export function getSessionSnapshot() {
  return state;
}

export async function signIn(credentials) {
  const account = await signInRequest(credentials);
  setState({ status: SESSION_STATUS.SIGNED_IN, account, welcome: false, signedOut: false });
  return account;
}

export async function signUp(data) {
  const account = await signUpRequest(data);
  setState({ status: SESSION_STATUS.SIGNED_IN, account, welcome: true, signedOut: false });
  return account;
}

export async function signOut() {
  await signOutRequest();
  setState({ status: SESSION_STATUS.GUEST, account: null, welcome: false, signedOut: true });
}

/** Depois de excluir a conta: a sessão some junto, sem chamar o servidor. */
export function forgetSession() {
  setState({ status: SESSION_STATUS.GUEST, account: null, welcome: false, signedOut: true });
}

/** Atualiza a conta mostrada (depois de editar o perfil). */
export function setSessionAccount(account) {
  setState({ account });
}

export function dismissWelcome() {
  if (state.welcome) setState({ welcome: false });
}

/** A guarda de rotas já levou o vendedor para a landing depois de sair. */
export function acknowledgeSignOut() {
  if (state.signedOut) setState({ signedOut: false });
}
