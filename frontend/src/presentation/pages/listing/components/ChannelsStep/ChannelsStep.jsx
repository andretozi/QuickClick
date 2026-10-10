import Button from '@/presentation/components/Button/Button.jsx';
import ListingPreview from '@/presentation/components/ListingPreview/ListingPreview.jsx';
import MarketplaceLogo from '@/presentation/components/MarketplaceLogo/MarketplaceLogo.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import Toggle from '@/presentation/components/Toggle/Toggle.jsx';
import { formatMoney } from '@/domain/format/format.js';
import { MARKETPLACE_CATALOG } from '@/domain/content/marketplacesContent.js';
import { LISTING_WIZARD } from '@/domain/content/listingContent.js';
import './ChannelsStep.css';

const SOON = MARKETPLACE_CATALOG.filter((marketplace) => !marketplace.available);

/** Passo 4: só o Mercado Livre pode ser escolhido (e só conectado); os outros vêm "em breve". */
export default function ChannelsStep({ editor }) {
  const { draft, update, connection, canPublishMl, priceCents } = editor;
  const texts = LISTING_WIZARD.channels;
  const stock = Number(draft.stock) || 0;

  return (
    <div className="channels-step">
      <header>
        <h2 className="heading channels-step__title">{texts.title}</h2>
        <p className="channels-step__lead">{texts.lead}</p>
      </header>

      <div className="channels-step__layout">
        <div className="channels-step__list">
          <section className="channels-step__main" aria-labelledby="canal-ml">
            <div className="channels-step__main-head">
              <span className="channels-step__logo">
                <MarketplaceLogo slug="mercado-livre" size="lg" />
              </span>
              <StatusPill tone={canPublishMl ? 'green' : 'honey'} size="sm">
                {canPublishMl ? texts.connected(connection.nickname) : texts.available}
              </StatusPill>
            </div>
            <h3 id="canal-ml" className="visually-hidden">
              {texts.toggleLabel}
            </h3>
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

          <ul className="channels-step__soon">
            {SOON.map((marketplace) => (
              <li key={marketplace.slug} className="channels-step__soon-item">
                <span data-shimmer className="channels-step__shine" aria-hidden="true" />
                <MarketplaceLogo slug={marketplace.slug} size="sm" muted />
                <span className="channels-step__soon-label">{texts.soon}</span>
              </li>
            ))}
          </ul>
        </div>

        <ListingPreview
          className="channels-step__preview"
          photo={draft.photos[draft.coverIndex]}
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
