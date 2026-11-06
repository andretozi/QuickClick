import { GoogleOAuthProvider } from '@react-oauth/google';
import LandingPage from '@/presentation/pages/landing/LandingPage.jsx';
import LoginPage from '@/presentation/pages/login/LoginPage.jsx';
import SignupPage from '@/presentation/pages/signup/SignupPage.jsx';
import DashboardPage from '@/presentation/pages/dashboard/DashboardPage.jsx';
import ListingDetailPage from '@/presentation/pages/listing/ListingDetailPage.jsx';
import ListingEditorPage from '@/presentation/pages/listing/ListingEditorPage.jsx';
import MarketplacesPage from '@/presentation/pages/marketplaces/MarketplacesPage.jsx';
import SettingsPage from '@/presentation/pages/settings/SettingsPage.jsx';
import AdminPage from '@/presentation/pages/admin/AdminPage.jsx';
import NotFoundPage from '@/presentation/pages/not-found/NotFoundPage.jsx';
import AppShell from '@/presentation/components/AppShell/AppShell.jsx';
import SplashScreen from '@/presentation/components/SplashScreen/SplashScreen.jsx';
import ToastViewport from '@/presentation/components/Toast/ToastViewport.jsx';
import useGoogleClientId from '@/application/auth/useGoogleClientId.js';
import useHashRoute from '@/application/navigation/useHashRoute.js';
import useRouteGuard, { ACCESS } from '@/application/navigation/useRouteGuard.js';
import useSession from '@/application/session/useSession.js';
import { ROUTES, isAdminOnlyRoute, isPrivateRoute } from '@/application/navigation/routes.js';

/** Páginas soltas, cada uma com o seu próprio fundo. */
const PAGES = {
  [ROUTES.LANDING]: LandingPage,
  [ROUTES.LOGIN]: LoginPage,
  [ROUTES.SIGNUP]: SignupPage,
  [ROUTES.NOT_FOUND]: NotFoundPage
};

/** Páginas da área logada: moram dentro do AppShell, que fica montado entre uma e outra. */
const APP_PAGES = {
  [ROUTES.DASHBOARD]: DashboardPage,
  [ROUTES.NEW_LISTING]: ListingEditorPage,
  [ROUTES.LISTING]: ListingDetailPage,
  [ROUTES.EDIT_LISTING]: ListingEditorPage,
  [ROUTES.MARKETPLACES]: MarketplacesPage,
  [ROUTES.SETTINGS]: SettingsPage,
  [ROUTES.ADMIN]: AdminPage
};

/**
 * Raiz da aplicação: liga as camadas.
 * Pergunta à camada de aplicação qual é a rota e se o vendedor pode vê-la (guarda das
 * rotas privadas e de administração) e entrega a página da camada de apresentação.
 */
export default function App() {
  const location = useHashRoute();
  const session = useSession();
  const access = useRouteGuard(location, session);
  const googleClientId = useGoogleClientId();

  let content = <SplashScreen />;
  const isAdminRoute = isAdminOnlyRoute(location.route);
  const isAuthorizedAdmin = session.account?.role === 'admin';

  if (access === ACCESS.ALLOWED && isAdminRoute && !isAuthorizedAdmin) {
    // Camuflagem total: não-administradores recebem a página 404 pura, sem pistas de existência
    content = <NotFoundPage key={location.path} params={location.params} />;
  } else if (access === ACCESS.ALLOWED && isPrivateRoute(location.route)) {
    const Page = APP_PAGES[location.route];
    content = (
      <AppShell current={location.route}>
        <Page key={location.path} params={location.params} />
      </AppShell>
    );
  } else if (access === ACCESS.ALLOWED) {
    const Page = PAGES[location.route] ?? NotFoundPage;
    content = <Page key={location.path} params={location.params} />;
  }

  const tree = (
    <>
      {content}
      <ToastViewport />
    </>
  );

  if (!googleClientId) return tree;

  return (
    <GoogleOAuthProvider clientId={googleClientId} locale="pt-BR">
      {tree}
    </GoogleOAuthProvider>
  );
}
