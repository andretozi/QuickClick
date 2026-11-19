import Eyebrow from '@/presentation/components/Eyebrow/Eyebrow.jsx';
import MarketplaceBoard from '@/presentation/components/MarketplaceBoard/MarketplaceBoard.jsx';
import MarketplaceLogo from '@/presentation/components/MarketplaceLogo/MarketplaceLogo.jsx';
import useMarketplaces from '@/application/marketplaces/useMarketplaces.js';
import { MARKETPLACES_PAGE, getMarketplaceInfo } from '@/domain/content/marketplacesContent.js';
import './MarketplacesPage.css';

/**
 * Marketplaces (#/marketplaces): cabeçalho neutro da Quick Click que mostra apenas
 * as lojas efetivamente conectadas e o quadro com as placas de cada marketplace.
 */
export default function MarketplacesPage() {
  const marketplaces = useMarketplaces();
  const { eyebrow, title, lead } = MARKETPLACES_PAGE;
  const connections = marketplaces.connections ?? [];

  return (
    <div className="marketplaces-page">
      <header className="marketplaces-page__hero">
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
        {connections.length > 0 && (
          <div data-enter="2" className="marketplaces-page__hero-connected">
            {connections.map((conn) => {
              const info = getMarketplaceInfo(conn.slug);
              return (
                <div key={conn.slug} className="marketplaces-page__hero-chip">
                  <span className="marketplaces-page__hero-chip-logo">
                    <MarketplaceLogo slug={conn.slug} size="md" decorative />
                  </span>
                  <div className="marketplaces-page__hero-chip-meta">
                    <strong className="marketplaces-page__hero-chip-name">{info?.name ?? conn.slug}</strong>
                    {conn.nickname && (
                      <span className="marketplaces-page__hero-chip-account">{conn.nickname}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </header>

      <MarketplaceBoard marketplaces={marketplaces} />
    </div>
  );
}
