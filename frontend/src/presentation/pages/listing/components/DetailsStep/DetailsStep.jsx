import Button from '@/presentation/components/Button/Button.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import SegmentedControl from '@/presentation/components/SegmentedControl/SegmentedControl.jsx';
import SelectField from '@/presentation/components/Field/SelectField.jsx';
import TextAreaField from '@/presentation/components/Field/TextAreaField.jsx';
import TextField from '@/presentation/components/Field/TextField.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { LISTING_LIMITS } from '@/domain/listings/listingRules.js';
import { LISTING_CATEGORIES, LISTING_CONDITIONS, LISTING_WIZARD } from '@/domain/content/listingContent.js';
import { FIELD_ERRORS } from '@/domain/content/commonContent.js';
import './DetailsStep.css';

/** Passo 2: título (com contador), descrição, categoria, condição e estoque, ou a sugestão da IA. */
export default function DetailsStep({ editor }) {
  const { draft, errors, setField, update, ai, suggest } = editor;
  const { title, lead, ai: aiTexts, fields } = LISTING_WIZARD.details;
  const working = ai.status === 'working';
  const titleLength = draft.title.length;

  return (
    <div className="details-step">
      <header className="details-step__head">
        <div>
          <h2 className="heading details-step__title">{title}</h2>
          <p className="details-step__lead">{lead}</p>
        </div>
        <Button
          variant="dark"
          icon="sparkles"
          iconPosition="start"
          iconSize={18}
          onClick={suggest}
          loading={working}
          loadingText={aiTexts.working}
          disabled={working}
          className="details-step__ai"
        >
          {aiTexts.button}
        </Button>
      </header>

      {/* "Analisando a foto": a capa com um feixe de luz passando e os passos da IA */}
      {working && (
        <div className="details-step__scan" role="status" aria-live="polite">
          <span className="details-step__scan-photo" aria-hidden="true">
            {draft.photos[draft.coverIndex] && <img src={draft.photos[draft.coverIndex]} alt="" />}
            <span data-shimmer className="details-step__scan-beam" />
          </span>
          <ol className="details-step__scan-steps">
            {aiTexts.steps.map((text, index) => (
              <li
                key={text}
                className={cx(
                  'details-step__scan-step',
                  index < ai.step && 'details-step__scan-step--done',
                  index === ai.step && 'details-step__scan-step--active'
                )}
              >
                <Icon name={index < ai.step ? 'check' : 'sparkle'} size={15} />
                {text}
              </li>
            ))}
          </ol>
        </div>
      )}
      {ai.status === 'needs-photo' && (
        <p className="details-step__notice" role="alert">
          {aiTexts.needsPhoto}
        </p>
      )}

      <div className="details-step__grid">
        <TextField
          id="anuncio-titulo"
          name="title"
          label={fields.title.label}
          placeholder={fields.title.placeholder}
          value={draft.title}
          onChange={setField}
          maxLength={LISTING_LIMITS.TITLE_MAX}
          aside={
            <span className={cx('details-step__counter', titleLength > LISTING_LIMITS.TITLE_MAX - 8 && 'details-step__counter--near')}>
              {fields.title.counter(titleLength, LISTING_LIMITS.TITLE_MAX)}
            </span>
          }
          error={FIELD_ERRORS[errors.title]}
          className="details-step__wide"
        />
        <TextAreaField
          id="anuncio-descricao"
          name="description"
          label={fields.description.label}
          placeholder={fields.description.placeholder}
          value={draft.description}
          onChange={setField}
          maxLength={LISTING_LIMITS.DESCRIPTION_MAX}
          error={FIELD_ERRORS[errors.description]}
          className="details-step__wide"
        />
        <SelectField
          id="anuncio-categoria"
          name="category"
          label={fields.category.label}
          value={draft.category}
          onChange={setField}
          placeholder={fields.category.placeholder}
          options={LISTING_CATEGORIES.map((category) => ({ value: category.id, label: category.label }))}
          error={FIELD_ERRORS[errors.category]}
        />
        <TextField
          id="anuncio-estoque"
          name="stock"
          type="number"
          inputMode="numeric"
          min="0"
          max={LISTING_LIMITS.STOCK_MAX}
          label={fields.stock.label}
          hint={fields.stock.hint}
          value={draft.stock}
          onChange={setField}
          error={FIELD_ERRORS[errors.stock]}
        />
        <div className="details-step__wide">
          <p className="details-step__label" id="anuncio-condicao">
            {fields.condition.label}
          </p>
          <SegmentedControl
            mode="radio"
            tone="paper"
            label={fields.condition.label}
            value={draft.condition}
            onChange={(value) => update({ condition: value })}
            options={LISTING_CONDITIONS}
          />
        </div>
      </div>
    </div>
  );
}
