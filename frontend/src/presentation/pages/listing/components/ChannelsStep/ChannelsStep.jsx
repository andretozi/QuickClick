import Button from '@/presentation/components/Button/Button.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import ListingPreview from '@/presentation/components/ListingPreview/ListingPreview.jsx';
import MarketplaceLogo from '@/presentation/components/MarketplaceLogo/MarketplaceLogo.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import Toggle from '@/presentation/components/Toggle/Toggle.jsx';
import UpgradeInvite from '@/presentation/components/UpgradeInvite/UpgradeInvite.jsx';
import { formatMoney } from '@/domain/format/format.js';
import { PRIMARY_CHANNEL, QUICKSTORE_CHANNEL, coverPhoto } from '@/domain/listings/listingRules.js';
import { MARKETPLACE_CATALOG, getMarketplaceInfo } from '@/domain/content/marketplacesContent.js';
import { CHANNEL_REASONS, CHANNEL_SIGNUP, LISTING_WIZARD } from '@/domain/content/listingContent.js';
import './ChannelsStep.css';

/**
 * Passo 6: "Suas contas" (as conectadas, na ordem em que o vendedor conectou) e "Vale abrir conta"
 * (os marketplaces que combinam com o produto, com o motivo e o link de cadastro).
 * Mercado Livre e QuickStore publicam direto pela Quick Click.
 */
export default function ChannelsStep({ editor }) {
  const {
    draft,
    update,
    connection,
    qsConnection,
    canPublishMl,
    canPublishQs,
    channelScope,
    priceCents,
    ai,
    editing,
    quota
  } = editor;
  const texts = LISTING_WIZARD.channels;
  const market = ai.analysis?.price?.market;
  const stock = Number(draft.stock) || 0;
  const fromAnalysis = ai.analysis?.channels;
  const showMl = !channelScope || channelScope === PRIMARY_CHANNEL;
  const showQs = !channelScope || channelScope === QUICKSTORE_CHANNEL;
  const others = channelScope
    ? []
    : (fromAnalysis ?? MARKETPLACE_CATALOG.map((m) => ({ slug: m.slug, connected: false, reason: null }))).filter(
        (channel) => channel.slug !== PRIMARY_CHANNEL && channel.slug !== QUICKSTORE_CHANNEL
      );
  const yours = others.filter((channel) => channel.connected);
  const worth = others.filter((channel) => !channel.connected);
  const noneSelected = (!showMl || !canPublishMl || !draft.publishMl) && (!showQs || !canPublishQs || !draft.publishQs);

  const previewQuickStore =
    channelScope === QUICKSTORE_CHANNEL ||
    (!editor.willPublishMl && (editor.willPublishQs || (canPublishQs && !canPublishMl)));
  const previewChannel = previewQuickStore ? QUICKSTORE_CHANNEL : PRIMARY_CHANNEL;
  const previewLabel = previewQuickStore
    ? (texts.previewQs ?? (texts.previewFor ? texts.previewFor('QuickStore') : 'Prévia na QuickStore'))
    : texts.preview;

  return (
    <div className="channels-step">
      <header>
        <h2 className="heading channels-step__title">{texts.title}</h2>
        <p className="channels-step__lead">{texts.lead}</p>
      </header>

      {!editing && quota && !quota.features.marketAnalysis && (
        <UpgradeInvite title={texts.market.title} text={texts.market.locked} action={texts.market.upgrade} />
      )}
      {!editing && quota?.features.marketAnalysis && (
        <section className="channels-step__market" aria-labelledby="analise-mercado">
          <h3 id="analise-mercado" className="channels-step__group">
            {texts.market.title}
          </h3>
          <p className="channels-step__market-text">
            {market?.count ? texts.market.found(market.count, formatMoney(market.min), formatMoney(market.max)) : texts.market.noData}
          </p>
          <p className="channels-step__market-note">{texts.market.onlyMl}</p>
        </section>
      )}

      <div className="channels-step__layout">
        <div className="channels-step__list">
          {/* Sem nenhuma conta conectada, o Mercado Livre e a QuickStore aparecem como onde publicar */}
          <h3 className="channels-step__group">{canPublishMl || canPublishQs || yours.length ? texts.yours : texts.publishHere}</h3>
          {showMl && (
            <section className="channels-step__main" aria-labelledby="canal-ml">
              <div className="channels-step__main-head">
                <span className="channels-step__logo">
                  <MarketplaceLogo slug={PRIMARY_CHANNEL} size="lg" />
                </span>
                <StatusPill tone={canPublishMl ? 'green' : 'honey'} size="sm">
                  {canPublishMl ? texts.connected(connection.nickname) : texts.available}
                </StatusPill>
                {editing && editor.linkedIds?.mlItemId && (
                  <StatusPill tone="neutral" size="sm">
                    {texts.linkedCode(editor.linkedIds.mlItemId)}
                  </StatusPill>
                )}
              </div>
              <h4 id="canal-ml" className="visually-hidden">
                {texts.toggleLabel}
              </h4>
              {canPublishMl ? (
                <Toggle
                  checked={Boolean(draft.publishMl)}
                  onChange={(checked) => update({ publishMl: checked })}
                  label={texts.toggleLabel}
                  description={noneSelected ? texts.noneSelected : null}
                />
              ) : (
                <div className="channels-step__connect">
                  <p className="channels-step__connect-text">{texts.notConnected}</p>
                  <Button href={texts.connect.href} size="sm" icon="link" iconPosition="start" iconSize={16}>
                    {texts.connect.label}
                  </Button>
                </div>
              )}
            </section>
          )}

          {showQs && (
            <section className="channels-step__main" aria-labelledby="canal-qs">
              <div className="channels-step__main-head">
                <span className="channels-step__logo">
                  <MarketplaceLogo slug={QUICKSTORE_CHANNEL} size="lg" />
                </span>
                <StatusPill tone={canPublishQs ? 'green' : 'honey'} size="sm">
                  {canPublishQs ? texts.connected(qsConnection?.nickname) : texts.available}
                </StatusPill>
                {editing && editor.linkedIds?.qsItemId && (
                  <StatusPill tone="neutral" size="sm">
                    {texts.linkedCode(editor.linkedIds.qsItemId)}
                  </StatusPill>
                )}
              </div>
              <h4 id="canal-qs" className="visually-hidden">
                {texts.toggleLabelQs}
              </h4>
              {canPublishQs ? (
                <Toggle
                  checked={Boolean(draft.publishQs)}
                  onChange={(checked) => update({ publishQs: checked })}
                  label={texts.toggleLabelQs}
                  description={noneSelected ? texts.noneSelected : null}
                />
              ) : (
                <div className="channels-step__connect">
                  <p className="channels-step__connect-text">{texts.notConnectedQs}</p>
                  <Button href={texts.connectQs.href} size="sm" icon="link" iconPosition="start" iconSize={16}>
                    {texts.connectQs.label}
                  </Button>
                </div>
              )}
            </section>
          )}

          {yours.map((channel) => (
            <div key={channel.slug} className="channels-step__account" data-enter="3">
              <MarketplaceLogo slug={channel.slug} size="sm" />
              <span className="channels-step__account-text">{texts.publishesSoon}</span>
            </div>
          ))}

          {worth.length > 0 && (
            <>
              <h3 className="channels-step__group">{texts.worthOpening}</h3>
              <ul className="channels-step__worth">
                {worth.map((channel) => (
                  <li key={channel.slug} className="channels-step__worth-item" data-enter="3">
                    <span data-shimmer className="channels-step__shine" aria-hidden="true" />
                    <MarketplaceLogo slug={channel.slug} size="sm" />
                    <p className="channels-step__reason">
                      <strong>{getMarketplaceInfo(channel.slug).name}</strong>
                      <span>{channel.reason ?? CHANNEL_REASONS[channel.slug]}</span>
                    </p>
                    {CHANNEL_SIGNUP[channel.slug] && (
                      <a
                        className="channels-step__open"
                        href={CHANNEL_SIGNUP[channel.slug]}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {texts.openAccount}
                        <Icon name="external" size={14} />
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <ListingPreview
          channel={previewChannel}
          className="channels-step__preview"
          photo={coverPhoto(draft)}
          title={draft.title}
          price={priceCents !== null ? formatMoney(priceCents) : ''}
          condition={draft.condition === 'used' ? texts.previewUsed : texts.previewNew}
          stock={texts.previewStock(stock)}
          texts={{ label: previewLabel, shipping: texts.previewFree, buy: texts.previewBuy }}
        />
      </div>
    </div>
  );
}
