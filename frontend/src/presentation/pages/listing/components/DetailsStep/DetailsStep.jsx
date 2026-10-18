import AiProgress from '@/presentation/components/AiProgress/AiProgress.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import SegmentedControl from '@/presentation/components/SegmentedControl/SegmentedControl.jsx';
import SelectField from '@/presentation/components/Field/SelectField.jsx';
import TextAreaField from '@/presentation/components/Field/TextAreaField.jsx';
import TextField from '@/presentation/components/Field/TextField.jsx';
import UpgradeInvite from '@/presentation/components/UpgradeInvite/UpgradeInvite.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { LISTING_LIMITS } from '@/domain/listings/listingRules.js';
import { WRITING_STAGES, stagesProgress } from '@/domain/listings/aiAnalysis.js';
import { LISTING_CATEGORIES, LISTING_CONDITIONS, LISTING_WIZARD } from '@/domain/content/listingContent.js';
import { FIELD_ERRORS } from '@/domain/content/commonContent.js';
import './DetailsStep.css';

/** Só o nome do site (a fonte pode vir num formato estranho). */
function siteOf(address) {
  try {
    return new URL(address).hostname.replace(/^www\./, '');
  } catch {
    return address;
  }
}

/** Passo 4: título (com contador) e descrição escritos pela IA, editáveis, mais categoria, condição e estoque. */
export default function DetailsStep({ editor }) {
  const { draft, errors, setField, update, ai, quota, resume, editing } = editor;
  const { title, lead, fields, why } = LISTING_WIZARD.details;
  const texts = LISTING_WIZARD.details;
  const { analysis, phase } = ai;
  const writing = !editing && phase === 'running' && Boolean(analysis?.confirmed);
  const failed = !editing && phase === 'failed' && Boolean(analysis?.confirmed);
  const research = analysis?.research;
  const titleLength = draft.title.length;

  return (
    <div className="details-step">
      <header className="details-step__head">
        <div>
          <h2 className="heading details-step__title">{title}</h2>
          <p className="details-step__lead">{lead}</p>
        </div>
      </header>

      {writing && (
        <AiProgress
          title={texts.writing}
          stages={stagesProgress(WRITING_STAGES, analysis).map((stage) => ({
            ...stage,
            label: LISTING_WIZARD.analysis.stages[stage.id]
          }))}
        />
      )}
      {failed && (
        <div className="details-step__notice details-step__notice--row" role="alert">
          <span>{analysis.error?.message || texts.failed}</span>
          <Button size="sm" variant="dark" icon="sync" iconPosition="start" iconSize={15} loading={ai.sending} onClick={resume}>
            {texts.retry}
          </Button>
        </div>
      )}
      {phase === 'ready' && analysis?.text?.corrected && <p className="details-step__hint">{texts.corrected}</p>}

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
          className={cx('details-step__wide', draft.aiFilled?.title && 'details-step__filled')}
        />
        <TextAreaField
          id="anuncio-descricao"
          name="description"
          label={fields.description.label}
          placeholder={fields.description.placeholder}
          value={draft.description}
          onChange={setField}
          maxLength={LISTING_LIMITS.DESCRIPTION_MAX}
          rows={8}
          aside={
            <span className="details-step__counter">
              {fields.title.counter(draft.description.length, LISTING_LIMITS.DESCRIPTION_MAX)}
            </span>
          }
          error={FIELD_ERRORS[errors.description]}
          className={cx('details-step__wide', draft.aiFilled?.description && 'details-step__filled')}
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

      {research && (
        <details className="details-step__why">
          <summary className="details-step__why-summary">
            <Icon name="info" size={16} />
            {why.title}
          </summary>
          <dl className="details-step__why-list">
            {research.buyerProfile && (
              <>
                <dt>{why.profile}</dt>
                <dd>{research.buyerProfile}</dd>
              </>
            )}
            {research.values.length > 0 && (
              <>
                <dt>{why.values}</dt>
                <dd>{research.values.join(', ')}</dd>
              </>
            )}
            {research.objections.length > 0 && (
              <>
                <dt>{why.objections}</dt>
                <dd>{research.objections.join(', ')}</dd>
              </>
            )}
            {research.terms.length > 0 && (
              <>
                <dt>{why.terms}</dt>
                <dd>{research.terms.join(', ')}</dd>
              </>
            )}
            {research.sources.length > 0 && (
              <>
                <dt>{why.sources}</dt>
                <dd className="details-step__sources">
                  {research.sources.map((source) => (
                    <a key={source} href={source} target="_blank" rel="noopener noreferrer">
                      {siteOf(source)}
                    </a>
                  ))}
                </dd>
              </>
            )}
          </dl>
        </details>
      )}

      {!editing && quota?.plan === 'gratis' && (
        <UpgradeInvite {...LISTING_WIZARD.invites.research} action={LISTING_WIZARD.invites.action} />
      )}
    </div>
  );
}
