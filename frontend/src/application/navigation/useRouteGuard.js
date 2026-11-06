import { useEffect } from 'react';
import { replaceHash } from '@/infrastructure/browser/location.js';
import { acknowledgeSignOut, SESSION_STATUS } from '@/application/session/sessionStore.js';
import {
  ROUTES,
  ROUTE_HASH,
  isAdminOnlyRoute,
  isGuestOnlyRoute,
  isPrivateRoute,
  loginHrefFor,
  returnHrefFrom
} from './routes.js';

/** O que a tela pode mostrar agora. */
export const ACCESS = { ALLOWED: 'allowed', WAITING: 'waiting' };

/**
 * Aplicação · Guarda das rotas
 *
 * - Rota de administrador (adminOnly): se não for admin, NUNCA redireciona para login
 *   (para não vazar que a rota existe). Deixa seguir para o App renderizar 404 idêntico a rotas inexistentes.
 * - Página privada sem conta logada: vai para o login, lembrando o destino ("?volta=").
 *   Se o vendedor acabou de sair, vai para a landing.
 * - Login ou cadastro com conta logada: vai para o destino lembrado ou para o painel.
 * Os redirecionamentos trocam o endereço sem criar histórico (o "voltar" não fica preso).
 * Enquanto a sessão é conferida ou o redirecionamento acontece, devolve "waiting".
 */
export default function useRouteGuard(location, session) {
  const { route, path, query } = location;
  const privateRoute = isPrivateRoute(route);
  const guestOnly = isGuestOnlyRoute(route);
  const adminOnly = isAdminOnlyRoute(route);
  const { status, signedOut } = session;

  useEffect(() => {
    if (status === SESSION_STATUS.CHECKING) return;

    if (adminOnly) {
      // Rotas restritas de admin nunca redirecionam para login (anti-reconhecimento)
      return;
    }

    if (privateRoute && status === SESSION_STATUS.GUEST) {
      if (signedOut) {
        // o aviso de "acabou de sair" só é zerado depois que o endereço muda (efeito abaixo)
        replaceHash(ROUTE_HASH[ROUTES.LANDING]);
      } else {
        const search = new URLSearchParams(query).toString();
        replaceHash(loginHrefFor(search ? `${path}?${search}` : path));
      }
      return;
    }
    if (guestOnly && status === SESSION_STATUS.SIGNED_IN) {
      replaceHash(returnHrefFrom(query));
    }
  }, [adminOnly, privateRoute, guestOnly, status, signedOut, path, query]);

  useEffect(() => {
    if (signedOut && !privateRoute) acknowledgeSignOut();
  }, [signedOut, privateRoute]);

  if (adminOnly && status === SESSION_STATUS.CHECKING) return ACCESS.WAITING;
  if (privateRoute && !adminOnly && status !== SESSION_STATUS.SIGNED_IN) return ACCESS.WAITING;
  if (guestOnly && status !== SESSION_STATUS.GUEST) return ACCESS.WAITING;
  return ACCESS.ALLOWED;
}
