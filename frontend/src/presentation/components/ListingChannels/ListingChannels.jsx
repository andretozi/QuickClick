import Icon from '@/presentation/components/Icon/Icon.jsx';
import MarketplaceLogo from '@/presentation/components/MarketplaceLogo/MarketplaceLogo.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { LISTING_STATUS } from '@/domain/listings/listingRules.js';
import { MARKETPLACE_CATALOG } from '@/domain/content/marketplacesContent.js';
import { LISTING_STATUS_LABELS } from '@/domain/content/listingContent.js';
import { LISTINGS_PANEL } from '@/domain/content/dashboardContent.js';
import './ListingChannels.css';

const AVAILABLE = MARKETPLACE_CATALOG.filter((marketplace) => marketplace.available);
const SOON = MARKETPLACE_CATALOG.filter((marketplace) => !marketplace.available);
const SOON_SHOWN = 3;

/**
 * Onde o anúncio está: o logo de cada canal integrado (Mercado Livre e QuickStore) com a
 * situação real dele (publicado, pausado ou não publicado) e um botão rápido "+ Adicionar"
 * para publicar no outro e-commerce ou voltar do standby com um clique.
 */
export default function ListingChannels({
  status,
  channels,
  itemIds = {},
  connectedByChannel = {},
  onPublishChannel,
  disabled = false,
  className
}) {
  const hidden = SOON.slice(SOON_SHOWN);

  return (
    <div className={cx('listing-channels', className)}>
      {AVAILABLE.map((marketplace) => {
        const chStatus = channels?.[marketplace.slug] ?? LISTING_STATUS.UNPUBLISHED;
        const hasItemId = Boolean(itemIds?.[marketplace.slug]);
        const statusInfo = LISTING_STATUS_LABELS[chStatus] ?? LISTING_STATUS_LABELS.unpublished;
        const isConnected = Boolean(connectedByChannel[marketplace.slug]);
        const isDisconnectedWithListing = chStatus !== LISTING_STATUS.UNPUBLISHED && !isConnected;
        const canQuickAdd =
          Boolean(onPublishChannel) &&
          isConnected &&
          chStatus === LISTING_STATUS.UNPUBLISHED &&
          !hasItemId;

        return (
          <span key={marketplace.slug} className="listing-channels__main">
            <span className="listing-channels__logo">
              <MarketplaceLogo slug={marketplace.slug} size="sm" decorative />
            </span>
            {canQuickAdd ? (
              <button
                type="button"
                className="listing-channels__add-btn"
                onClick={() => onPublishChannel(marketplace.slug)}
                disabled={disabled}
                title={LISTINGS_PANEL.actions.addToChannel(marketplace.name)}
                aria-label={LISTINGS_PANEL.actions.addToChannel(marketplace.name)}
              >
                {`+ ${marketplace.name}`}
              </button>
            ) : (
              <>
                <StatusPill tone={statusInfo.tone} size="sm">
                  <span className="visually-hidden">{`${marketplace.name}: `}</span>
                  {statusInfo.label}
                </StatusPill>
                {isDisconnectedWithListing && (
                  <span
                    className="listing-channels__disconnected"
                    title={LISTINGS_PANEL.channels.disconnectedHint(marketplace.name)}
                    aria-label={LISTINGS_PANEL.channels.disconnectedHint(marketplace.name)}
                  >
                    <Icon name="alert" size={12} />
                    {LISTINGS_PANEL.channels.disconnectedBadge}
                  </span>
                )}
              </>
            )}
          </span>
        );
      })}
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
