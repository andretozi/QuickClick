import LandingPage from '@/presentation/pages/landing/LandingPage.jsx';
import LoginPage from '@/presentation/pages/login/LoginPage.jsx';
import SignupPage from '@/presentation/pages/signup/SignupPage.jsx';
import DashboardPage from '@/presentation/pages/dashboard/DashboardPage.jsx';
import ListingEditorPage from '@/presentation/pages/listing/ListingEditorPage.jsx';
import MarketplacesPage from '@/presentation/pages/marketplaces/MarketplacesPage.jsx';
import SettingsPage from '@/presentation/pages/settings/SettingsPage.jsx';
import NotFoundPage from '@/presentation/pages/not-found/NotFoundPage.jsx';
import AppShell from '@/presentation/components/AppShell/AppShell.jsx';
import SplashScreen from '@/presentation/components/SplashScreen/SplashScreen.jsx';
import ToastViewport from '@/presentation/components/Toast/ToastViewport.jsx';
import useHashRoute from '@/application/navigation/useHashRoute.js';
import useRouteGuard, { ACCESS } from '@/application/navigation/useRouteGuard.js';
import useSession from '@/application/session/useSession.js';
import { ROUTES, isPrivateRoute } from '@/application/navigation/routes.js';

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
  [ROUTES.LISTING]: ListingEditorPage,
  [ROUTES.MARKETPLACES]: MarketplacesPage,
  [ROUTES.SETTINGS]: SettingsPage
};

/**
 * Raiz da aplicação: liga as camadas.
 * Pergunta à camada de aplicação qual é a rota e se o vendedor pode vê-la (guarda das
 * rotas privadas) e entrega a página da camada de apresentação.
 */
export default function App() {
  const location = useHashRoute();
  const session = useSession();
  const access = useRouteGuard(location, session);

  let content = <SplashScreen />;
  if (access === ACCESS.ALLOWED && isPrivateRoute(location.route)) {
    const Page = APP_PAGES[location.route];
    content = (
      <AppShell current={location.route}>
        <Page key={location.path} params={location.params} query={location.query} />
      </AppShell>
    );
  } else if (access === ACCESS.ALLOWED) {
    const Page = PAGES[location.route] ?? NotFoundPage;
    content = <Page key={location.path} params={location.params} query={location.query} />;
  }

  return (
    <>
      {content}
      <ToastViewport />
    </>
  );
}
