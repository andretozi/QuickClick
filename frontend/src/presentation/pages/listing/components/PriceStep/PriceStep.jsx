import Button from '@/presentation/components/Button/Button.jsx';
import PriceRuler from '@/presentation/components/PriceRuler/PriceRuler.jsx';
import TextField from '@/presentation/components/Field/TextField.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { formatMoney } from '@/domain/format/format.js';
import { LISTING_WIZARD } from '@/domain/content/listingContent.js';
import { FIELD_ERRORS } from '@/domain/content/commonContent.js';
import './PriceStep.css';

/** Passo 3: a régua com a faixa de preço (simulada) e o preço do vendedor. */
export default function PriceStep({ editor }) {
  const { draft, errors, setField, range, priceCents, pricePosition, acceptSuggestedPrice } = editor;
  const texts = LISTING_WIZARD.price;
  const ready = range.status === 'ready';
  const usingSuggested = ready && priceCents === range.suggestedCents;

  return (
    <div className="price-step">
      <header>
        <h2 className="heading price-step__title">{texts.title}</h2>
        <p className="price-step__lead">{texts.lead}</p>
      </header>

      <div className="price-step__ruler">
        {ready ? (
          <PriceRuler
            minCents={range.minCents}
            suggestedCents={range.suggestedCents}
            maxCents={range.maxCents}
            valueCents={priceCents}
            position={pricePosition}
            format={formatMoney}
            texts={texts.ruler}
          />
        ) : (
          <p className="price-step__loading" role="status">
            <span data-spin className="price-step__spinner" aria-hidden="true" />
            {texts.loading}
          </p>
        )}
      </div>

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
      <p className="price-step__note">{texts.simulated}</p>
    </div>
  );
}
