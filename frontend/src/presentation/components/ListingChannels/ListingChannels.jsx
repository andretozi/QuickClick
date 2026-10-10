import MarketplaceLogo from '@/presentation/components/MarketplaceLogo/MarketplaceLogo.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { MARKETPLACE_CATALOG } from '@/domain/content/marketplacesContent.js';
import { LISTING_STATUS_LABELS } from '@/domain/content/listingContent.js';
import { LISTINGS_PANEL } from '@/domain/content/dashboardContent.js';
import './ListingChannels.css';

const AVAILABLE = MARKETPLACE_CATALOG.filter((marketplace) => marketplace.available);
const SOON = MARKETPLACE_CATALOG.filter((marketplace) => !marketplace.available);
const SOON_SHOWN = 3;

/**
 * Onde o anúncio está: o logo do Mercado Livre com a situação (publicado, pausado ou
 * não publicado) e, apagados, os marketplaces que ainda vão chegar.
 * - status: situação no canal principal ('published' | 'paused' | 'unpublished')
 */
export default function ListingChannels({ status, compact = false, className }) {
  const statusInfo = LISTING_STATUS_LABELS[status] ?? LISTING_STATUS_LABELS.unpublished;
  const hidden = SOON.slice(SOON_SHOWN);

  return (
    <div className={cx('listing-channels', compact && 'listing-channels--compact', className)}>
      {AVAILABLE.map((marketplace) => (
        <span key={marketplace.slug} className="listing-channels__main">
          <span className="listing-channels__logo">
            <MarketplaceLogo slug={marketplace.slug} size="sm" decorative />
          </span>
          <StatusPill tone={statusInfo.tone} size="sm">
            <span className="visually-hidden">{`${marketplace.name}: `}</span>
            {statusInfo.label}
          </StatusPill>
        </span>
      ))}
      <span className="listing-channels__soon" title={LISTINGS_PANEL.soon.label(SOON.map((item) => item.name).join(', '))}>
        <span data-shimmer className="listing-channels__shine" aria-hidden="true" />
        {SOON.slice(0, SOON_SHOWN).map((marketplace) => (
          <span key={marketplace.slug} className="listing-channels__soon-logo">
            <MarketplaceLogo slug={marketplace.slug} size="xs" muted decorative />
          </span>
        ))}
        {hidden.length > 0 && (
          <span className="listing-channels__more" aria-hidden="true">
            {LISTINGS_PANEL.soon.more(hidden.length)}
          </span>
        )}
        <span className="visually-hidden">{LISTINGS_PANEL.soon.label(SOON.map((item) => item.name).join(', '))}</span>
      </span>
    </div>
  );
}
