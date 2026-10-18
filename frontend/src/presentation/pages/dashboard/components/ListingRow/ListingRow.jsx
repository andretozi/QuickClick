import IconButton from '@/presentation/components/IconButton/IconButton.jsx';
import ListingChannels from '@/presentation/components/ListingChannels/ListingChannels.jsx';
import ListingThumb from '@/presentation/components/ListingThumb/ListingThumb.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { LISTING_STATUS, listingStatus } from '@/domain/listings/listingRules.js';
import { formatMoney, formatRelative } from '@/domain/format/format.js';
import { LISTINGS_PANEL } from '@/domain/content/dashboardContent.js';
import { hrefForListing, hrefForListingEdit } from '@/application/navigation/routes.js';
import './ListingRow.css';

/**
 * Uma linha da lista de anúncios: foto, título, preço, estoque, atualização, canais e ações.
 * Clicar na linha abre a visão geral das macroinformações (#/anuncios/:id); o botão de editar
 * leva direto ao editor (#/anuncios/:id/editar).
 */
export default function ListingRow({ listing, busy, canPublish, onToggle, onDuplicate, onRemove }) {
  const status = listingStatus(listing);
  const { actions, actionLabel } = LISTINGS_PANEL;
  const toggle =
    status === LISTING_STATUS.PUBLISHED
      ? { icon: 'pause', label: actions.pause }
      : status === LISTING_STATUS.PAUSED
        ? { icon: 'play', label: canPublish ? actions.resume : actions.resumeBlocked }
        : { icon: 'upload', label: canPublish ? actions.publish : actions.publishBlocked };
  const blocked = !canPublish;

  return (
    <li data-enter="3" className={cx('listing-row', busy && 'listing-row--busy')}>
      <a href={hrefForListing(listing.id)} className="listing-row__main">
        <ListingThumb listing={listing} className="listing-row__thumb" />
        <span className="listing-row__text">
          <span className="listing-row__title">{listing.title}</span>
          <span className="listing-row__meta">{LISTINGS_PANEL.updated(formatRelative(listing.updatedAt))}</span>
        </span>
      </a>

      <p className="listing-row__price">{formatMoney(listing.priceCents)}</p>
      <p className={cx('listing-row__stock', listing.stock === 0 && 'listing-row__stock--empty')}>
        {LISTINGS_PANEL.stock(listing.stock)}
      </p>

      <ListingChannels status={status} className="listing-row__channels" />

      <div className="listing-row__actions">
        <IconButton
          icon="eye"
          size="sm"
          href={hrefForListing(listing.id)}
          label={actionLabel(actions.view, listing.title)}
        />
        <IconButton
          icon="edit"
          size="sm"
          href={hrefForListingEdit(listing.id)}
          label={actionLabel(actions.edit, listing.title)}
        />
        <IconButton
          icon={toggle.icon}
          size="sm"
          label={actionLabel(toggle.label, listing.title)}
          disabled={busy || blocked}
          onClick={() => onToggle(listing)}
        />
        <IconButton
          icon="copy"
          size="sm"
          label={actionLabel(actions.duplicate, listing.title)}
          disabled={busy}
          onClick={() => onDuplicate(listing)}
        />
        <IconButton
          icon="trash"
          size="sm"
          tone="danger"
          label={actionLabel(actions.remove, listing.title)}
          disabled={busy}
          onClick={() => onRemove(listing)}
        />
      </div>
    </li>
  );
}
