import AiProgress from '@/presentation/components/AiProgress/AiProgress.jsx';
import FormAlert from '@/presentation/components/FormAlert/FormAlert.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import SegmentedControl from '@/presentation/components/SegmentedControl/SegmentedControl.jsx';
import SelectField from '@/presentation/components/Field/SelectField.jsx';
import TextField from '@/presentation/components/Field/TextField.jsx';
import AttributeCard from './AttributeCard.jsx';
import RequirementCard from './RequirementCard.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { READING_STAGES, isPendingCheck, stagesProgress } from '@/domain/listings/aiAnalysis.js';
import { coveredCardKeys, missingRequirements, requirementGroups } from '@/domain/listings/exigencias.js';
import {
  LISTING_CATEGORIES,
  LISTING_CONDITIONS,
  LISTING_WIZARD,
  aiErrorText,
  attributeLabel
} from '@/domain/content/listingContent.js';
import './ConfirmStep.css';

/**
 * Passo 3: o vendedor confirma ou corrige o que a IA viu. Só o que ele confirmar entra no anúncio.
 * Com exigências dos canais na leitura, elas vêm antes dos cartões, que mostram só o que elas não cobrem.
 */
export default function ConfirmStep({ editor }) {
  const { draft, update, setField, setCard, setDefect, ai, errors, requirementFields, setRequirement } = editor;
  const texts = LISTING_WIZARD.confirm;
  const fields = LISTING_WIZARD.details.fields;
  const reading = ai.analysis?.reading;
  const rereading = ai.phase === 'running';
  const covered = coveredCardKeys(requirementFields);
  const cards = draft.cards.filter((card) => !covered.has(card.key));
  const missing = missingRequirements(requirementFields, draft.requirementAnswers);
  const blocked = Boolean(errors.requirements) && missing.length > 0;
  const pending = cards.filter(isPendingCheck).length + missing.length;

  return (
    <div className="confirm-step">
      <header>
        <h2 className="heading confirm-step__title">{texts.title}</h2>
        <p className="confirm-step__lead">{texts.lead}</p>
      </header>

      {reading && !reading.recognized && <FormAlert title={texts.notRecognized.title} text={texts.notRecognized.text} />}
      {ai.error && <FormAlert {...aiErrorText(ai.error.code, ai.error.message)} />}
      {rereading && (
        <AiProgress
          stages={stagesProgress(READING_STAGES, ai.analysis).map((stage) => ({
            ...stage,
            label: LISTING_WIZARD.analysis.stages[stage.id]
          }))}
          title={texts.readingPhoto}
        />
      )}

      <div className="confirm-step__basics">
        <TextField
          id="confirmar-produto"
          name="product"
          label={texts.product.label}
          placeholder={texts.product.placeholder}
          value={draft.product}
          onChange={setField}
          className="confirm-step__wide"
        />
        <SelectField
          id="confirmar-categoria"
          name="category"
          label={fields.category.label}
          value={draft.category}
          onChange={setField}
          placeholder={fields.category.placeholder}
          options={LISTING_CATEGORIES.map((category) => ({ value: category.id, label: category.label }))}
        />
        <div>
          <p className="confirm-step__label">{fields.condition.label}</p>
          <SegmentedControl
            mode="radio"
            tone="paper"
            label={fields.condition.label}
            idPrefix="confirmar-condicao"
            value={draft.condition}
            onChange={(value) => update({ condition: value })}
            options={LISTING_CONDITIONS}
          />
        </div>
      </div>

      {requirementGroups(requirementFields).map((group) => (
        <fieldset key={group.id} className="confirm-step__group">
          <legend className="confirm-step__legend">{group.name || texts.requirements.common}</legend>
          {!group.name && <p className="confirm-step__group-lead">{texts.requirements.lead}</p>}
          <ul className="confirm-step__cards">
            {group.fields.map((field) => (
              <RequirementCard
                key={field.id}
                field={field}
                answer={draft.requirementAnswers?.[field.id]}
                texts={texts}
                error={blocked && missing.includes(field.id) ? texts.requirements.confirmToContinue : undefined}
                onChange={(patch) => setRequirement(field.id, patch)}
              />
            ))}
          </ul>
        </fieldset>
      ))}

      {cards.length > 0 && (
        <ul className="confirm-step__cards">
          {cards.map((card) => (
            <AttributeCard
              key={card.key}
              card={card}
              label={attributeLabel(card.key)}
              texts={texts}
              busy={ai.sending || rereading}
              onChange={(value) => setCard(card.key, { value, edited: true })}
              onAnswer={(answer) => setCard(card.key, { answer })}
              onPhoto={(file, kind) => ai.extraPhoto(file, kind)}
            />
          ))}
        </ul>
      )}

      {draft.defects.length > 0 && (
        <section className="confirm-step__defects" aria-labelledby="confirmar-defeitos">
          <h3 id="confirmar-defeitos" className="confirm-step__defects-title">
            <Icon name="alert" size={18} />
            {texts.defects.title}
          </h3>
          <ul className="confirm-step__defect-list">
            {draft.defects.map((defect, index) => (
              <li
                key={defect.text}
                className={cx('confirm-step__defect', !defect.keep && 'confirm-step__defect--removed')}
                data-enter="3"
              >
                <span className="confirm-step__defect-text">{defect.text}</span>
                <span className="confirm-step__defect-answer" role="group" aria-label={texts.defects.question}>
                  <span className="confirm-step__defect-question">
                    {defect.keep ? texts.defects.question : texts.defects.removed}
                  </span>
                  <button
                    type="button"
                    className={cx('confirm-step__defect-button', defect.keep && 'confirm-step__defect-button--on')}
                    aria-pressed={defect.keep}
                    onClick={() => setDefect(index, true)}
                  >
                    {texts.yes}
                  </button>
                  <button
                    type="button"
                    className={cx('confirm-step__defect-button', !defect.keep && 'confirm-step__defect-button--off')}
                    aria-pressed={!defect.keep}
                    onClick={() => setDefect(index, false)}
                  >
                    {texts.no}
                  </button>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {blocked && <FormAlert {...texts.requirements.blocked} />}

      {pending > 0 && (
        <p className="confirm-step__pending" aria-live="polite">
          {texts.pending(pending)}
        </p>
      )}
    </div>
  );
}
