import Button from '@/presentation/components/Button/Button.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import ListingPreview from '@/presentation/components/ListingPreview/ListingPreview.jsx';
import MarketplaceLogo from '@/presentation/components/MarketplaceLogo/MarketplaceLogo.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import Toggle from '@/presentation/components/Toggle/Toggle.jsx';
import { formatMoney } from '@/domain/format/format.js';
import { PRIMARY_CHANNEL, coverPhoto } from '@/domain/listings/listingRules.js';
import { MARKETPLACE_CATALOG, getMarketplaceInfo } from '@/domain/content/marketplacesContent.js';
import { CHANNEL_REASONS, CHANNEL_SIGNUP, LISTING_WIZARD } from '@/domain/content/listingContent.js';
import './ChannelsStep.css';

/**
 * Passo 6: "Suas contas" (as conectadas, na ordem em que o vendedor conectou) e "Vale abrir conta"
 * (os marketplaces que combinam com o produto, com o motivo e o link de cadastro).
 * Só o Mercado Livre publica por enquanto.
 */
export default function ChannelsStep({ editor }) {
  const { draft, update, connection, canPublishMl, priceCents, ai } = editor;
  const texts = LISTING_WIZARD.channels;
  const stock = Number(draft.stock) || 0;
  const fromAnalysis = ai.analysis?.channels;
  const others = (fromAnalysis ?? MARKETPLACE_CATALOG.map((m) => ({ slug: m.slug, connected: false, reason: null })))
    .filter((channel) => channel.slug !== PRIMARY_CHANNEL);
  const yours = others.filter((channel) => channel.connected);
  const worth = others.filter((channel) => !channel.connected);

  return (
    <div className="channels-step">
      <header>
        <h2 className="heading channels-step__title">{texts.title}</h2>
        <p className="channels-step__lead">{texts.lead}</p>
      </header>

      <div className="channels-step__layout">
        <div className="channels-step__list">
          {/* Sem nenhuma conta conectada, o Mercado Livre aparece como onde publicar (e não como conta sua) */}
          <h3 className="channels-step__group">{canPublishMl || yours.length ? texts.yours : texts.publishHere}</h3>
          <section className="channels-step__main" aria-labelledby="canal-ml">
            <div className="channels-step__main-head">
              <span className="channels-step__logo">
                <MarketplaceLogo slug={PRIMARY_CHANNEL} size="lg" />
              </span>
              <StatusPill tone={canPublishMl ? 'green' : 'honey'} size="sm">
                {canPublishMl ? texts.connected(connection.nickname) : texts.available}
              </StatusPill>
            </div>
            <h4 id="canal-ml" className="visually-hidden">
              {texts.toggleLabel}
            </h4>
            {canPublishMl ? (
              <Toggle
                checked={draft.publishMl}
                onChange={(checked) => update({ publishMl: checked })}
                label={texts.toggleLabel}
                description={draft.publishMl ? null : texts.noneSelected}
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
          className="channels-step__preview"
          photo={coverPhoto(draft)}
          title={draft.title}
          price={priceCents !== null ? formatMoney(priceCents) : ''}
          condition={draft.condition === 'used' ? texts.previewUsed : texts.previewNew}
          stock={texts.previewStock(stock)}
          texts={{ label: texts.preview, shipping: texts.previewFree, buy: texts.previewBuy }}
        />
      </div>
    </div>
  );
}
