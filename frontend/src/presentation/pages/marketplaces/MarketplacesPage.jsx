import BrandBackdrop from '@/presentation/components/BrandBackdrop/BrandBackdrop.jsx';
import Eyebrow from '@/presentation/components/Eyebrow/Eyebrow.jsx';
import MarketplaceBoard from '@/presentation/components/MarketplaceBoard/MarketplaceBoard.jsx';
import MarketplaceLogo from '@/presentation/components/MarketplaceLogo/MarketplaceLogo.jsx';
import useMarketplaces from '@/application/marketplaces/useMarketplaces.js';
import { MARKETPLACES_PAGE, getMarketplacePalette } from '@/domain/content/marketplacesContent.js';
import './MarketplacesPage.css';

/**
 * Marketplaces (#/marketplaces): topo cinematográfico no amarelo do Mercado Livre
 * (o único que já conecta) e o quadro com as placas de cada marketplace.
 */
export default function MarketplacesPage() {
  const marketplaces = useMarketplaces();
  const { eyebrow, title, lead } = MARKETPLACES_PAGE;

  return (
    <div className="marketplaces-page">
      <header className="marketplaces-page__hero">
        <BrandBackdrop
          slug="mercado-livre"
          palette={getMarketplacePalette('mercado-livre')}
          spotlight={false}
          className="marketplaces-page__backdrop"
        />
        <div className="marketplaces-page__hero-text">
          <Eyebrow data-enter="1" tone="inherit" className="marketplaces-page__eyebrow">
            {eyebrow}
          </Eyebrow>
          <h1 data-enter="1" data-page-focus tabIndex={-1} className="heading marketplaces-page__title">
            {title}
          </h1>
          <p data-enter="1" className="marketplaces-page__lead">
            {lead}
          </p>
        </div>
        <span data-enter="2" className="marketplaces-page__hero-logo" aria-hidden="true">
          <MarketplaceLogo slug="mercado-livre" size="hero" decorative />
        </span>
      </header>

      <MarketplaceBoard marketplaces={marketplaces} />
    </div>
  );
}
