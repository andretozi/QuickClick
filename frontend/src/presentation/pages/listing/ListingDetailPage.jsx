import { useEffect, useState } from 'react';
import Button from '@/presentation/components/Button/Button.jsx';
import EmptyState from '@/presentation/components/EmptyState/EmptyState.jsx';
import FormAlert from '@/presentation/components/FormAlert/FormAlert.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import MarketplaceLogo from '@/presentation/components/MarketplaceLogo/MarketplaceLogo.jsx';
import Modal from '@/presentation/components/Modal/Modal.jsx';
import PageHeader from '@/presentation/components/PageHeader/PageHeader.jsx';
import Panel from '@/presentation/components/Panel/Panel.jsx';
import StatusPanel from '@/presentation/components/StatusPanel/StatusPanel.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import useListingDetail from '@/application/listings/useListingDetail.js';
import { ROUTE_HASH, ROUTES, hrefForListingEdit } from '@/application/navigation/routes.js';
import { cx } from '@/presentation/utils/cx.js';
import {
  LISTING_LIMITS,
  LISTING_STATUS,
  PRIMARY_CHANNEL,
  QUICKSTORE_CHANNEL,
  channelStatus,
  listingStatus
} from '@/domain/listings/listingRules.js';
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
 * galeria de fotos, preço, estoque, vendas, pontuação de qualidade,
 * ficha técnica completa, descrição e ações diretas nos canais (Mercado Livre e QuickStore).
 */
export default function ListingDetailPage({ params }) {
  const detail = useListingDetail(params?.id);
  const {
    status,
    listing,
    mlConnected,
    qsConnected,
    syncing,
    busy,
    selectedPhoto,
    setSelectedPhoto,
    syncNow,
    updateStock,
    toggleChannelStatus,
    toggleAllChannels,
    pendingChannelRemoval,
    removingChannel,
    requestChannelRemoval,
    cancelChannelRemoval,
    confirmChannelRemoval,
    duplicate,
    confirmingDelete,
    removing,
    requestRemoval,
    cancelRemoval,
    confirmRemoval
  } = detail;

  const [stockDraft, setStockDraft] = useState('');
  const [savingStock, setSavingStock] = useState(false);

  useEffect(() => {
    if (listing?.stock !== undefined && listing?.stock !== null) {
      setStockDraft(String(listing.stock));
    }
  }, [listing?.stock]);

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

  const overallStatus = listingStatus(listing);
  const mlStatus = channelStatus(listing, PRIMARY_CHANNEL);
  const qsStatus = channelStatus(listing, QUICKSTORE_CHANNEL);
  const statusBadge = LISTING_STATUS_LABELS[overallStatus] ?? LISTING_STATUS_LABELS.unpublished;
  const mlBadge = LISTING_STATUS_LABELS[mlStatus] ?? LISTING_STATUS_LABELS.unpublished;
  const qsBadge = LISTING_STATUS_LABELS[qsStatus] ?? LISTING_STATUS_LABELS.unpublished;
  const photos = listing.photos ?? [];
  const activePhoto = photos[selectedPhoto] ?? photos[0] ?? null;
  const safePermalink = safeExternalUrl(listing.permalink);
  const safeQsPermalink = safeExternalUrl(listing.qsPermalink);
  const rawHealth = listing.health ?? listing.qsHealth;
  const healthPct =
    typeof rawHealth === 'number' && rawHealth > 0
      ? Math.round(rawHealth <= 1 ? rawHealth * 100 : rawHealth)
      : null;

  const canSyncAny = (listing.mlItemId && mlConnected) || (listing.qsItemId && qsConnected);
  const mlPriceCents = listing.mlPriceCents ?? listing.priceCents;
  const qsPriceCents = listing.qsPriceCents ?? listing.priceCents;
  const hasDistinctChannelPrices =
    listing.mlPriceCents != null &&
    listing.qsPriceCents != null &&
    listing.mlPriceCents !== listing.qsPriceCents;

  const parsedStockDraft = Number(stockDraft);
  const stockChanged =
    stockDraft !== '' &&
    Number.isInteger(parsedStockDraft) &&
    parsedStockDraft >= 0 &&
    parsedStockDraft <= LISTING_LIMITS.STOCK_MAX &&
    parsedStockDraft !== listing.stock;

  const handleStockSubmit = async (event) => {
    event.preventDefault();
    if (!stockChanged || busy || savingStock) return;
    setSavingStock(true);
    try {
      await updateStock(parsedStockDraft);
    } finally {
      setSavingStock(false);
    }
  };

  const channelCards = [
    {
      slug: PRIMARY_CHANNEL,
      name: 'Mercado Livre',
      connected: mlConnected,
      status: mlStatus,
      badge: mlBadge,
      itemId: listing.mlItemId,
      permalink: safePermalink,
      priceCents: mlPriceCents
    },
    {
      slug: QUICKSTORE_CHANNEL,
      name: 'QuickStore',
      connected: qsConnected,
      status: qsStatus,
      badge: qsBadge,
      itemId: listing.qsItemId,
      permalink: safeQsPermalink,
      priceCents: qsPriceCents
    }
  ];

  const globalToggle =
    overallStatus === LISTING_STATUS.PUBLISHED
      ? { icon: 'pause', label: LISTING_DETAIL.globalActions.pauseAll }
      : overallStatus === LISTING_STATUS.PAUSED
        ? { icon: 'play', label: LISTING_DETAIL.globalActions.resumeAll }
        : { icon: 'upload', label: LISTING_DETAIL.globalActions.publishAll };

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
            {canSyncAny && (
              <Button
                variant="light"
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
        <StatusPill tone={mlBadge.tone} size="sm">
          {`Mercado Livre: ${mlBadge.label}`}
        </StatusPill>
        <StatusPill tone={qsBadge.tone} size="sm">
          {`QuickStore: ${qsBadge.label}`}
        </StatusPill>
        {listing.mlItemId && (
          <StatusPill tone="cream" size="sm">
            {`ML ${listing.mlItemId}`}
          </StatusPill>
        )}
        {listing.qsItemId && (
          <StatusPill tone="cream" size="sm">
            {`QS ${listing.qsItemId}`}
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
          <strong className="heading listing-detail__metric-value">
            {hasDistinctChannelPrices
              ? `${formatMoney(Math.min(mlPriceCents, qsPriceCents))} – ${formatMoney(Math.max(mlPriceCents, qsPriceCents))}`
              : formatMoney(listing.priceCents)}
          </strong>
          {hasDistinctChannelPrices ? (
            <span className="listing-detail__metric-foot">
              {LISTING_DETAIL.metrics.channelPrices(formatMoney(mlPriceCents), formatMoney(qsPriceCents))}
            </span>
          ) : listing.suggestedPriceCents ? (
            <span className="listing-detail__metric-foot">
              {LISTING_DETAIL.metrics.suggested(formatMoney(listing.suggestedPriceCents))}
            </span>
          ) : (
            <span className="listing-detail__metric-foot">{conditionLabel(listing.condition)}</span>
          )}
        </Panel>

        <Panel tone="paper" className="listing-detail__metric-card listing-detail__metric-card--stock">
          <span className="listing-detail__metric-label">{LISTING_DETAIL.metrics.stock}</span>
          <strong className="heading listing-detail__metric-value">
            {LISTING_DETAIL.metrics.units(listing.stock)}
          </strong>
          <form className="listing-detail__stock-form" onSubmit={handleStockSubmit}>
            <div className="listing-detail__stock-controls">
              <button
                type="button"
                className="listing-detail__stock-step"
                aria-label="Diminuir estoque"
                disabled={busy || savingStock || (Number(stockDraft) || 0) <= 0}
                onClick={() => setStockDraft(String(Math.max(0, (Number(stockDraft) || 0) - 1)))}
              >
                −
              </button>
              <input
                type="number"
                min={0}
                max={LISTING_LIMITS.STOCK_MAX}
                step={1}
                aria-label={LISTING_DETAIL.metrics.stockInputLabel}
                className="listing-detail__stock-input"
                value={stockDraft}
                disabled={busy || savingStock}
                onChange={(e) => setStockDraft(e.target.value)}
              />
              <button
                type="button"
                className="listing-detail__stock-step"
                aria-label="Aumentar estoque"
                disabled={busy || savingStock || (Number(stockDraft) || 0) >= LISTING_LIMITS.STOCK_MAX}
                onClick={() =>
                  setStockDraft(String(Math.min(LISTING_LIMITS.STOCK_MAX, (Number(stockDraft) || 0) + 1)))
                }
              >
                +
              </button>
              <Button
                type="submit"
                size="sm"
                variant={stockChanged ? 'primary' : 'outline'}
                loading={savingStock}
                loadingText={LISTING_DETAIL.metrics.stockSaving}
                disabled={!stockChanged || busy || savingStock}
              >
                {LISTING_DETAIL.metrics.stockSave}
              </Button>
            </div>
          </form>
          <span className="listing-detail__metric-foot">
            {LISTING_DETAIL.metrics.sold}: {LISTING_DETAIL.metrics.soldUnits(listing.soldQuantity ?? 0)}
            {canSyncAny ? ` · ${LISTING_DETAIL.metrics.stockSyncHint}` : ''}
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
          <Panel tone="paper" className="listing-detail__channels-panel">
            <div className="listing-detail__section-head">
              <div>
                <h2 className="heading listing-detail__section-title">{LISTING_DETAIL.channels.title}</h2>
                <p className="listing-detail__section-subtitle">{LISTING_DETAIL.channels.subtitle}</p>
              </div>
            </div>

            <div className="listing-detail__channel-cards">
              {channelCards.map((channel) => {
                const toggleBtn =
                  channel.status === LISTING_STATUS.PUBLISHED
                    ? { icon: 'pause', label: LISTING_DETAIL.channels.pauseChannel(channel.name) }
                    : channel.status === LISTING_STATUS.PAUSED
                      ? { icon: 'play', label: LISTING_DETAIL.channels.resumeChannel(channel.name) }
                      : { icon: 'upload', label: LISTING_DETAIL.channels.publishChannel(channel.name) };

                return (
                  <section
                    key={channel.slug}
                    className={cx(
                      'listing-detail__channel-card',
                      !channel.connected && 'listing-detail__channel-card--disconnected'
                    )}
                    aria-label={channel.name}
                  >
                    <div className="listing-detail__channel-head">
                      <div className="listing-detail__channel-identity">
                        <span className="listing-detail__channel-logo">
                          <MarketplaceLogo slug={channel.slug} size="md" decorative />
                        </span>
                        <div className="listing-detail__channel-titles">
                          <h3 className="heading listing-detail__channel-name">{channel.name}</h3>
                          <span className="listing-detail__channel-connection">
                            {channel.connected
                              ? LISTING_DETAIL.channels.connected
                              : LISTING_DETAIL.channels.disconnected}
                            {` · ${formatMoney(channel.priceCents)}`}
                          </span>
                        </div>
                      </div>
                      <div className="listing-detail__channel-badges">
                        <StatusPill tone={channel.badge.tone} size="sm">
                          {channel.badge.label}
                        </StatusPill>
                        {channel.itemId && (
                          <StatusPill tone="neutral" size="sm">
                            {LISTING_DETAIL.channels.itemCode(channel.itemId)}
                          </StatusPill>
                        )}
                      </div>
                    </div>

                    {!channel.connected && (
                      <div className="listing-detail__channel-alert">
                        <FormAlert title={LISTING_DETAIL.channels.disconnectedAlertTitle(channel.name)}>
                          {LISTING_DETAIL.channels.disconnectedAlertText(channel.name)}
                        </FormAlert>
                        <Button
                          href={ROUTE_HASH[ROUTES.MARKETPLACES]}
                          size="sm"
                          icon="link"
                          iconPosition="start"
                          iconSize={15}
                        >
                          {LISTING_DETAIL.channels.connectCta}
                        </Button>
                      </div>
                    )}

                    <div className="listing-detail__channel-actions">
                      <Button
                        variant={channel.status === LISTING_STATUS.UNPUBLISHED ? 'primary' : 'outline'}
                        size="sm"
                        icon={toggleBtn.icon}
                        iconPosition="start"
                        iconSize={15}
                        onClick={() => toggleChannelStatus(channel.slug)}
                        disabled={busy}
                      >
                        {toggleBtn.label}
                      </Button>

                      <Button
                        href={hrefForListingEdit(listing.id, channel.slug)}
                        variant="outline"
                        size="sm"
                        icon="edit"
                        iconPosition="start"
                        iconSize={15}
                      >
                        {LISTING_DETAIL.channels.editChannel(channel.name)}
                      </Button>

                      {(channel.status !== LISTING_STATUS.UNPUBLISHED || Boolean(channel.itemId)) && (
                        <Button
                          variant="outline"
                          size="sm"
                          icon="trash"
                          iconPosition="start"
                          iconSize={15}
                          onClick={() => requestChannelRemoval(channel.slug)}
                          disabled={busy || removingChannel}
                          className="listing-detail__channel-delete-btn"
                        >
                          {LISTING_DETAIL.channels.deleteChannel(channel.name)}
                        </Button>
                      )}

                      {channel.permalink && (
                        <Button
                          href={channel.permalink}
                          target="_blank"
                          rel="noopener noreferrer"
                          variant="outline"
                          size="sm"
                          icon="external"
                          iconPosition="start"
                          iconSize={15}
                        >
                          {LISTING_DETAIL.channels.openChannel(channel.name)}
                        </Button>
                      )}
                    </div>
                  </section>
                );
              })}
            </div>
          </Panel>

          <Panel tone="paper" className="listing-detail__actions-panel">
            <div className="listing-detail__section-head">
              <div>
                <h2 className="heading listing-detail__section-title">{LISTING_DETAIL.globalActions.title}</h2>
                <p className="listing-detail__section-subtitle">{LISTING_DETAIL.globalActions.subtitle}</p>
              </div>
            </div>

            <div className="listing-detail__action-buttons">
              <Button
                variant={overallStatus === LISTING_STATUS.UNPUBLISHED ? 'primary' : 'outline'}
                icon={globalToggle.icon}
                iconPosition="start"
                iconSize={16}
                onClick={toggleAllChannels}
                disabled={busy}
              >
                {globalToggle.label}
              </Button>

              <Button
                href={hrefForListingEdit(listing.id)}
                variant="outline"
                icon="edit"
                iconPosition="start"
                iconSize={16}
              >
                {LISTING_DETAIL.globalActions.editAll}
              </Button>

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
              {listing.qsItemId && (
                <div className="listing-detail__spec-row">
                  <dt className="listing-detail__spec-term">{LISTING_DETAIL.specs.qsCode}</dt>
                  <dd className="listing-detail__spec-value">{listing.qsItemId}</dd>
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

            {(!listing.attributes || listing.attributes.length === 0) && !listing.mlItemId && !listing.qsItemId && (
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

      {(() => {
        const targetChannel = channelCards.find((ch) => ch.slug === pendingChannelRemoval) ?? null;
        const targetName = targetChannel?.name ?? '';
        return (
          <Modal
            open={Boolean(pendingChannelRemoval)}
            onClose={cancelChannelRemoval}
            dismissible={!removingChannel}
            icon="trash"
            iconTone="danger"
            size="sm"
            title={targetName ? LISTING_DETAIL.channels.confirmDeleteChannel.title(targetName) : ''}
            description={
              targetName ? LISTING_DETAIL.channels.confirmDeleteChannel.text(listing.title, targetName) : ''
            }
            actions={
              <>
                <Button
                  variant="outline"
                  onClick={cancelChannelRemoval}
                  disabled={removingChannel}
                  data-autofocus
                >
                  {LISTING_DETAIL.channels.confirmDeleteChannel.cancel}
                </Button>
                <Button
                  onClick={() => confirmChannelRemoval(pendingChannelRemoval)}
                  loading={removingChannel}
                  loadingText={LISTING_DETAIL.channels.confirmDeleteChannel.deleting}
                  disabled={removingChannel}
                >
                  {targetName ? LISTING_DETAIL.channels.confirmDeleteChannel.confirm(targetName) : ''}
                </Button>
              </>
            }
          />
        );
      })()}

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
