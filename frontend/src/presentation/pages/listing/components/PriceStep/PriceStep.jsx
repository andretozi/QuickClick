import Button from '@/presentation/components/Button/Button.jsx';
import FormAlert from '@/presentation/components/FormAlert/FormAlert.jsx';
import PriceRuler from '@/presentation/components/PriceRuler/PriceRuler.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import TextField from '@/presentation/components/Field/TextField.jsx';
import UpgradeInvite from '@/presentation/components/UpgradeInvite/UpgradeInvite.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { formatMoney } from '@/domain/format/format.js';
import { LISTING_WIZARD } from '@/domain/content/listingContent.js';
import { FIELD_ERRORS } from '@/domain/content/commonContent.js';
import './PriceStep.css';

/** Passo 5: a régua com a faixa real de anúncios parecidos, o que sobra depois da tarifa e o preço do vendedor. */
export default function PriceStep({ editor }) {
  const { draft, errors, setField, range, priceCents, pricePosition, acceptSuggestedPrice, ai, quota, editing } = editor;
  const texts = LISTING_WIZARD.price;
  const price = ai.analysis?.price;
  const ready = range.status === 'ready';
  const usingSuggested = ready && priceCents === range.suggestedCents;
  const noData = range.status === 'none' && price?.noData ? texts.noData[price.reason] ?? texts.noData.sem_resultados : null;

  return (
    <div className="price-step">
      <header>
        <h2 className="heading price-step__title">{texts.title}</h2>
        <p className="price-step__lead">{texts.lead}</p>
      </header>

      {range.status === 'loading' && (
        <p className="price-step__loading" role="status">
          <span data-spin className="price-step__spinner" aria-hidden="true" />
          {texts.loading}
        </p>
      )}

      {ready && (
        <div className="price-step__ruler">
          <PriceRuler
            minCents={range.minCents}
            suggestedCents={range.suggestedCents}
            maxCents={range.maxCents}
            valueCents={priceCents}
            position={pricePosition}
            format={formatMoney}
            texts={texts.ruler}
          />
          <ul className="price-step__facts">
            <li>{texts.market(price.market.count)}</li>
            <li>{texts.median(formatMoney(price.market.median))}</li>
            <li>{texts.freeShipping(price.market.freeShipping)}</li>
            {price.feeCents !== null && (
              <li>
                {texts.fee}: <strong>{formatMoney(price.feeCents)}</strong>
              </li>
            )}
            {price.netCents !== null && (
              <li className="price-step__net">
                {texts.net}: <strong>{formatMoney(price.netCents)}</strong>
              </li>
            )}
          </ul>
          {price.source === 'web' && <p className="price-step__note">{texts.fromWeb}</p>}
        </div>
      )}

      {ready && price.byAi && (
        <div className="price-step__advice" data-enter="3">
          {price.strategy && (
            <StatusPill tone="mint" size="md">
              {texts.strategy.title}: {texts.strategy[price.strategy]}
            </StatusPill>
          )}
          {price.justification && <p className="price-step__justification">{price.justification}</p>}
          {price.alerts.length > 0 && (
            <ul className="price-step__alerts">
              {price.alerts.map((alert) => (
                <li key={alert}>{alert}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {noData && (
        <div className="price-step__nodata">
          <FormAlert title={noData.title} text={noData.text} />
          {price.reason === 'mercado_livre_desconectado' && (
            <Button href={texts.connect.href} size="sm" variant="outline" icon="link" iconPosition="start" iconSize={15}>
              {texts.connect.label}
            </Button>
          )}
        </div>
      )}
      {range.status === 'none' && !noData && !editing && <p className="price-step__note">{texts.manual}</p>}

      <div className="price-step__row">
        <TextField
          id="anuncio-preco"
          name="priceInput"
          inputMode="decimal"
          label={texts.field.label}
          hint={texts.field.hint}
          placeholder={texts.field.placeholder}
          value={draft.priceInput}
          onChange={setField}
          leading={<span className="price-step__currency">{texts.field.currency}</span>}
          error={FIELD_ERRORS[errors.price]}
          className="price-step__field"
        />
        {ready && (
          <Button
            variant={usingSuggested ? 'light' : 'primary'}
            icon={usingSuggested ? 'check' : 'sparkles'}
            iconPosition="start"
            iconSize={17}
            onClick={acceptSuggestedPrice}
            disabled={usingSuggested}
            className="price-step__accept"
          >
            {usingSuggested ? texts.accepted : texts.accept(formatMoney(range.suggestedCents))}
          </Button>
        )}
      </div>

      {pricePosition && (
        <p className={cx('price-step__position', `price-step__position--${pricePosition}`)} aria-live="polite">
          {texts.position[pricePosition]}
        </p>
      )}

      {!editing && quota?.plan === 'gratis' && (
        <UpgradeInvite {...LISTING_WIZARD.invites.pricing} action={LISTING_WIZARD.invites.action} />
      )}
    </div>
  );
}
