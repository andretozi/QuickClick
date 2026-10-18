import Button from '@/presentation/components/Button/Button.jsx';
import EmptyState from '@/presentation/components/EmptyState/EmptyState.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import Modal from '@/presentation/components/Modal/Modal.jsx';
import PageHeader from '@/presentation/components/PageHeader/PageHeader.jsx';
import Panel from '@/presentation/components/Panel/Panel.jsx';
import StatusPanel from '@/presentation/components/StatusPanel/StatusPanel.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import useListingDetail from '@/application/listings/useListingDetail.js';
import { hrefForListingEdit } from '@/application/navigation/routes.js';
import { cx } from '@/presentation/utils/cx.js';
import { LISTING_STATUS, listingStatus } from '@/domain/listings/listingRules.js';
import { formatMoney, formatRelative } from '@/domain/format/format.js';
import {
  LISTING_DETAIL,
  LISTING_EDITOR,
  LISTING_STATUS_LABELS,
  LISTING_WIZARD,
  attributeLabel,
  categoryLabel,
  conditionLabel
} from '@/domain/content/listingContent.js';
import { LISTINGS_PANEL } from '@/domain/content/dashboardContent.js';
import './ListingDetailPage.css';

function safeExternalUrl(url) {
  const value = String(url ?? '').trim();
  return value.startsWith('https://') ? value : null;
}

/**
 * Visão geral das macroinformações de um produto (#/anuncios/:id):
 * galeria de fotos, preço, estoque, vendas, pontuação de qualidade no Mercado Livre,
 * ficha técnica completa, descrição e ações diretas (editar, sincronizar, pausar e excluir).
 */
export default function ListingDetailPage({ params }) {
  const detail = useListingDetail(params?.id);
  const {
    status,
    listing,
    mlConnected,
    syncing,
    busy,
    selectedPhoto,
    setSelectedPhoto,
    syncNow,
    toggleStatus,
    duplicate,
    confirmingDelete,
    removing,
    requestRemoval,
    cancelRemoval,
    confirmRemoval
  } = detail;

  if (status === 'loading') {
    return (
      <div className="listing-detail">
        <StatusPanel text={LISTING_DETAIL.loading} />
      </div>
    );
  }

  if (status === 'not-found' || !listing) {
    return (
      <div className="listing-detail">
        <Panel tone="glass" data-enter="1">
          <EmptyState icon="search" tone="glass" title={LISTING_EDITOR.notFound.title} text={LISTING_EDITOR.notFound.text}>
            <Button href={LISTING_EDITOR.notFound.action.href}>{LISTING_EDITOR.notFound.action.label}</Button>
          </EmptyState>
        </Panel>
      </div>
    );
  }

  const channelStatus = listingStatus(listing);
  const statusBadge = LISTING_STATUS_LABELS[channelStatus] ?? LISTING_STATUS_LABELS.unpublished;
  const photos = listing.photos ?? [];
  const activePhoto = photos[selectedPhoto] ?? photos[0] ?? null;
  const safePermalink = safeExternalUrl(listing.permalink);
  const healthPct =
    typeof listing.health === 'number' && listing.health > 0
      ? Math.round(listing.health <= 1 ? listing.health * 100 : listing.health)
      : null;

  const toggleButton =
    channelStatus === LISTING_STATUS.PUBLISHED
      ? { icon: 'pause', label: LISTING_DETAIL.actions.pause }
      : channelStatus === LISTING_STATUS.PAUSED
        ? { icon: 'play', label: LISTING_DETAIL.actions.resume }
        : { icon: 'upload', label: LISTING_DETAIL.actions.publish };

  return (
    <div className="listing-detail">
      <PageHeader
        eyebrow={LISTING_DETAIL.eyebrow}
        title={listing.title}
        lead={LISTINGS_PANEL.updated(formatRelative(listing.updatedAt))}
        actions={
          <div className="listing-detail__header-actions">
            <Button
              href={LISTING_DETAIL.back.href}
              variant="light"
              size="sm"
              icon="arrow-left"
              iconPosition="start"
              iconSize={16}
            >
              {LISTING_DETAIL.back.label}
            </Button>
            {listing.mlItemId && mlConnected && (
              <Button
                variant="outline"
                size="sm"
                icon="sync"
                iconPosition="start"
                iconSize={15}
                onClick={syncNow}
                loading={syncing}
                loadingText={LISTING_DETAIL.syncing}
                disabled={syncing}
              >
                {LISTING_DETAIL.actions.sync}
              </Button>
            )}
            <Button
              href={hrefForListingEdit(listing.id)}
              size="sm"
              icon="edit"
              iconPosition="start"
              iconSize={16}
            >
              {LISTING_DETAIL.actions.edit}
            </Button>
          </div>
        }
      >
        <StatusPill tone={statusBadge.tone} size="sm">
          {statusBadge.label}
        </StatusPill>
        {listing.mlItemId && (
          <StatusPill tone="cream" size="sm">
            {listing.mlItemId}
          </StatusPill>
        )}
        {healthPct !== null && (
          <StatusPill tone={healthPct >= 75 ? 'green' : 'honey'} size="sm">
            {LISTING_DETAIL.metrics.qualityScore(healthPct)}
          </StatusPill>
        )}
      </PageHeader>

      <section className="listing-detail__metrics" data-enter="1" aria-label={LISTING_DETAIL.eyebrow}>
        <Panel tone="paper" className="listing-detail__metric-card">
          <span className="listing-detail__metric-label">{LISTING_DETAIL.metrics.price}</span>
          <strong className="heading listing-detail__metric-value">{formatMoney(listing.priceCents)}</strong>
          {listing.suggestedPriceCents ? (
            <span className="listing-detail__metric-foot">
              {LISTING_DETAIL.metrics.suggested(formatMoney(listing.suggestedPriceCents))}
            </span>
          ) : (
            <span className="listing-detail__metric-foot">{conditionLabel(listing.condition)}</span>
          )}
        </Panel>

        <Panel tone="paper" className="listing-detail__metric-card">
          <span className="listing-detail__metric-label">{LISTING_DETAIL.metrics.stock}</span>
          <strong className="heading listing-detail__metric-value">
            {LISTING_DETAIL.metrics.units(listing.stock)}
          </strong>
          <span className="listing-detail__metric-foot">
            {LISTING_DETAIL.metrics.sold}: {LISTING_DETAIL.metrics.soldUnits(listing.soldQuantity ?? 0)}
          </span>
        </Panel>

        <Panel tone="paper" className="listing-detail__metric-card">
          <span className="listing-detail__metric-label">{LISTING_DETAIL.metrics.condition}</span>
          <strong className="heading listing-detail__metric-value">{conditionLabel(listing.condition)}</strong>
          <span className="listing-detail__metric-foot">{categoryLabel(listing.category)}</span>
        </Panel>

        <Panel tone="paper" className="listing-detail__metric-card">
          <span className="listing-detail__metric-label">{LISTING_DETAIL.metrics.quality}</span>
          <strong className="heading listing-detail__metric-value">
            {healthPct !== null ? `${healthPct}%` : LISTING_DETAIL.metrics.qualityEmpty}
          </strong>
          <span className="listing-detail__metric-foot">
            {LISTING_DETAIL.gallery.count(photos.length)}
          </span>
        </Panel>
      </section>

      <div className="listing-detail__grid" data-enter="2">
        <Panel tone="paper" className="listing-detail__gallery">
          <div className="listing-detail__section-head">
            <h2 className="heading listing-detail__section-title">{LISTING_DETAIL.gallery.title}</h2>
            <span className="listing-detail__section-meta">{LISTING_DETAIL.gallery.count(photos.length)}</span>
          </div>

          {activePhoto ? (
            <>
              <div className="listing-detail__stage">
                <img
                  src={activePhoto}
                  alt={LISTING_WIZARD.photos.photoAlt(selectedPhoto + 1)}
                  className="listing-detail__stage-image"
                />
                {selectedPhoto === (listing.coverIndex ?? 0) && (
                  <span className="listing-detail__cover-badge">
                    <Icon name="star-filled" size={13} />
                    {LISTING_WIZARD.photos.cover}
                  </span>
                )}
              </div>

              {photos.length > 1 && (
                <ul className="listing-detail__thumbs">
                  {photos.map((photo, index) => (
                    <li key={`${photo.slice(-32)}-${index}`}>
                      <button
                        type="button"
                        onClick={() => setSelectedPhoto(index)}
                        aria-label={LISTING_DETAIL.gallery.thumbLabel(index + 1)}
                        className={cx(
                          'listing-detail__thumb-btn',
                          index === selectedPhoto && 'listing-detail__thumb-btn--active'
                        )}
                      >
                        <img
                          src={photo}
                          alt={LISTING_WIZARD.photos.photoAlt(index + 1)}
                          className="listing-detail__thumb-image"
                        />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <p className="listing-detail__empty-text">{LISTING_DETAIL.gallery.empty}</p>
          )}
        </Panel>

        <div className="listing-detail__aside">
          <Panel tone="paper" className="listing-detail__actions-panel">
            <div className="listing-detail__action-buttons">
              <Button
                variant="outline"
                icon={toggleButton.icon}
                iconPosition="start"
                iconSize={16}
                onClick={toggleStatus}
                disabled={busy || !mlConnected}
              >
                {toggleButton.label}
              </Button>

              {safePermalink && (
                <Button
                  href={safePermalink}
                  target="_blank"
                  rel="noopener noreferrer"
                  variant="outline"
                  icon="external"
                  iconPosition="start"
                  iconSize={16}
                >
                  {LISTING_DETAIL.actions.viewOnMl}
                </Button>
              )}

              <Button
                variant="outline"
                icon="copy"
                iconPosition="start"
                iconSize={16}
                onClick={duplicate}
                disabled={busy}
              >
                {LISTING_DETAIL.actions.duplicate}
              </Button>

              <Button
                variant="outline"
                icon="trash"
                iconPosition="start"
                iconSize={16}
                onClick={requestRemoval}
                disabled={busy}
                className="listing-detail__delete-btn"
              >
                {LISTING_DETAIL.actions.remove}
              </Button>
            </div>
          </Panel>

          <Panel tone="paper" className="listing-detail__specs">
            <div className="listing-detail__section-head">
              <h2 className="heading listing-detail__section-title">{LISTING_DETAIL.specs.title}</h2>
            </div>

            <dl className="listing-detail__specs-list">
              {listing.mlItemId && (
                <div className="listing-detail__spec-row">
                  <dt className="listing-detail__spec-term">{LISTING_DETAIL.specs.mlCode}</dt>
                  <dd className="listing-detail__spec-value">{listing.mlItemId}</dd>
                </div>
              )}
              {listing.mlCategoryId && (
                <div className="listing-detail__spec-row">
                  <dt className="listing-detail__spec-term">{LISTING_DETAIL.specs.mlCategory}</dt>
                  <dd className="listing-detail__spec-value">{listing.mlCategoryId}</dd>
                </div>
              )}
              {(listing.attributes ?? []).map((attr, index) => (
                <div key={`${attr.id ?? attr.name}-${index}`} className="listing-detail__spec-row">
                  <dt className="listing-detail__spec-term">{attributeLabel(attr.name)}</dt>
                  <dd className="listing-detail__spec-value">{attr.value}</dd>
                </div>
              ))}
            </dl>

            {(!listing.attributes || listing.attributes.length === 0) && !listing.mlItemId && (
              <p className="listing-detail__empty-text">{LISTING_DETAIL.specs.empty}</p>
            )}
          </Panel>
        </div>
      </div>

      <Panel tone="paper" data-enter="3" className="listing-detail__description">
        <div className="listing-detail__section-head">
          <h2 className="heading listing-detail__section-title">{LISTING_DETAIL.description.title}</h2>
        </div>
        {listing.description ? (
          <p className="listing-detail__description-body">{listing.description}</p>
        ) : (
          <p className="listing-detail__empty-text">{LISTING_DETAIL.description.empty}</p>
        )}
      </Panel>

      <Modal
        open={confirmingDelete}
        onClose={cancelRemoval}
        dismissible={!removing}
        icon="trash"
        iconTone="danger"
        size="sm"
        title={LISTINGS_PANEL.confirmDelete.title}
        description={LISTINGS_PANEL.confirmDelete.text(listing.title)}
        actions={
          <>
            <Button variant="outline" onClick={cancelRemoval} disabled={removing} data-autofocus>
              {LISTINGS_PANEL.confirmDelete.cancel}
            </Button>
            <Button
              onClick={confirmRemoval}
              loading={removing}
              loadingText={LISTINGS_PANEL.confirmDelete.deleting}
              disabled={removing}
            >
              {LISTINGS_PANEL.confirmDelete.confirm}
            </Button>
          </>
        }
      />
    </div>
  );
}
