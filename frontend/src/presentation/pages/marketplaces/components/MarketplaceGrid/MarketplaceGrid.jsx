import { useRef } from 'react';
import PlanPanel from '../PlanPanel/PlanPanel.jsx';
import MarketplaceCard from '../MarketplaceCard/MarketplaceCard.jsx';
import useCardsEntrance from '@/application/animation/useCardsEntrance.js';
import { MARKETPLACES_PAGE } from '@/domain/content/marketplacesContent.js';
import './MarketplaceGrid.css';

/** O plano do vendedor e a grade com todos os marketplaces do catálogo, entrando em sequência. */
export default function MarketplaceGrid({
  seller,
  marketplaces,
  busySlug,
  failedSlug,
  celebratedSlug,
  onConnect,
  onDisconnect
}) {
  const gridRef = useRef(null);
  useCardsEntrance(gridRef);

  return (
    <div ref={gridRef} className="marketplace-grid">
      <PlanPanel seller={seller} data-enter />
      <ul className="marketplace-grid__list" aria-label={MARKETPLACES_PAGE.listLabel}>
        {marketplaces.map((marketplace) => (
          <MarketplaceCard
            key={marketplace.slug}
            marketplace={marketplace}
            busy={busySlug === marketplace.slug}
            failed={failedSlug === marketplace.slug}
            celebrate={celebratedSlug === marketplace.slug}
            onConnect={onConnect}
            onDisconnect={onDisconnect}
            data-enter
          />
        ))}
      </ul>
    </div>
  );
}
