import LandingPage from '@/presentation/pages/landing/LandingPage.jsx';
import LoginPage from '@/presentation/pages/login/LoginPage.jsx';
import MarketplacesPage from '@/presentation/pages/marketplaces/MarketplacesPage.jsx';
import useHashRoute from '@/application/navigation/useHashRoute.js';
import { ROUTES } from '@/application/navigation/routes.js';

/** Qual página desenhar para cada rota. */
const PAGES = {
  [ROUTES.LANDING]: LandingPage,
  [ROUTES.LOGIN]: LoginPage,
  [ROUTES.MARKETPLACES]: MarketplacesPage
};

/**
 * Raiz da aplicação: liga as camadas.
 * Pergunta à camada de aplicação qual é a rota e entrega a página da camada de apresentação.
 */
export default function App() {
  const route = useHashRoute();
  const Page = PAGES[route] ?? LandingPage;
  return <Page />;
}
