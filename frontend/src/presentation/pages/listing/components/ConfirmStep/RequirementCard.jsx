import { useRef } from 'react';
import SegmentedControl from '@/presentation/components/SegmentedControl/SegmentedControl.jsx';
import SelectField from '@/presentation/components/Field/SelectField.jsx';
import TextField from '@/presentation/components/Field/TextField.jsx';
import { describedBy } from '@/presentation/components/Field/Field.jsx';
import AttributeCard from './AttributeCard.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { CARD } from '@/domain/listings/aiAnalysis.js';
import { FIELD_TYPE } from '@/domain/listings/exigencias.js';

const TEXT_MAX = 300; // limite do valor na confirmação (back)

/**
 * Uma exigência dos canais no cartão de atributo: o campo pelo tipo (lista, número com a unidade,
 * Sim e Não, texto), a sugestão da IA pré-preenchida e o "Está certo?". Escolher ou digitar o
 * valor também confirma; a sugestão sozinha não conta.
 */
export default function RequirementCard({ field, answer, texts, error, onChange }) {
  const controlRef = useRef(null);
  const words = texts.requirements;
  const id = `exigencia-${field.id}`;
  const value = answer?.value ?? '';
  const confirmed = Boolean(answer?.confirmed);
  const suggested = Boolean(field.suggestion) && value === field.suggestion.value;
  const card = {
    key: id,
    value,
    card: confirmed ? CARD.CHECK : suggested ? field.suggestion.card : CARD.ASK,
    answer: confirmed ? 'yes' : null,
    edited: false,
    evidence: '',
    suggestPhoto: 'nenhuma'
  };
  const write = (next) => onChange({ value: next, confirmed: Boolean(String(next).trim()) });
  const quiet = 'attribute-card__field attribute-card__field--quiet';

  const refuse = () => {
    onChange({ value: '', confirmed: false });
    // o "Está certo?" some: o foco vai para o campo, para o vendedor escrever o certo
    window.requestAnimationFrame(() => controlRef.current?.querySelector('input, select')?.focus());
  };

  let control;
  if (field.type === FIELD_TYPE.BOOLEAN) {
    control = (
      <SegmentedControl
        mode="radio"
        tone="paper"
        label={field.label}
        value={value}
        onChange={(next) => onChange({ value: next, confirmed: true })}
        options={field.options.map((option, index) => ({ value: option, label: [texts.yes, texts.no][index] }))}
      />
    );
  } else if (field.type === FIELD_TYPE.LIST) {
    control = (
      <SelectField
        id={id}
        label={field.label}
        value={value}
        error={error}
        placeholder={words.choose}
        options={field.options.map((option) => ({ value: option, label: option }))}
        onChange={(event) => write(event.target.value)}
        className={quiet}
      />
    );
  } else if (field.type === FIELD_TYPE.NUMBER) {
    const unitId = `${id}-unidade`;
    control = (
      <div className="attribute-card__number">
        <TextField
          id={id}
          type="number"
          inputMode="decimal"
          step="any"
          min="0"
          label={field.label}
          value={value}
          error={error}
          placeholder={texts.answerPlaceholder}
          onChange={(event) => write(event.target.value)}
          aria-describedby={[describedBy(id, { error }), field.unit && unitId].filter(Boolean).join(' ') || undefined}
          className={quiet}
        />
        {field.unit && (
          <span id={unitId} className="attribute-card__unit">
            {field.unit}
          </span>
        )}
      </div>
    );
  } else {
    control = (
      <TextField
        id={id}
        label={field.label}
        value={value}
        error={error}
        maxLength={TEXT_MAX}
        placeholder={texts.answerPlaceholder}
        onChange={(event) => write(event.target.value)}
        className={quiet}
      />
    );
  }

  return (
    <AttributeCard card={card} label={field.label} texts={texts}>
      <div ref={controlRef}>{control}</div>

      {suggested && field.type !== FIELD_TYPE.BOOLEAN && (
        <div className="attribute-card__check">
          <span id={`${id}-pergunta`} className="attribute-card__question">
            {words.question}
          </span>
          <div className="attribute-card__answers" role="group" aria-labelledby={`atributo-${id}-nome ${id}-pergunta`}>
            <button
              type="button"
              className={cx('attribute-card__answer', confirmed && 'attribute-card__answer--on')}
              aria-pressed={confirmed}
              onClick={() => onChange({ confirmed: true })}
            >
              {texts.yes}
            </button>
            <button type="button" className="attribute-card__answer" onClick={refuse}>
              {texts.no}
            </button>
          </div>
        </div>
      )}

      {suggested && field.type === FIELD_TYPE.BOOLEAN && !confirmed && (
        <p className="attribute-card__evidence">{words.tapToConfirm}</p>
      )}
      {field.type === FIELD_TYPE.BOOLEAN && error && <p className="attribute-card__error">{error}</p>}
      {suggested && words.origin[field.suggestion.origin] && (
        <p className="attribute-card__evidence">{words.origin[field.suggestion.origin]}</p>
      )}
      <p className="attribute-card__evidence">{words.askedBy(field.channels)}</p>
    </AttributeCard>
  );
}
