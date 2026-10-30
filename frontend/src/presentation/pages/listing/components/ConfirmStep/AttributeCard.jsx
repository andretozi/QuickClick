import { useRef } from 'react';
import Button from '@/presentation/components/Button/Button.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import TextField from '@/presentation/components/Field/TextField.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { CARD } from '@/domain/listings/aiAnalysis.js';
import './AttributeCard.css';

/**
 * Um atributo lido pela IA, montado pela resposta do back:
 * - "A IA viu" (foto ou etiqueta, confiança alta): preenchido e editável;
 * - "Confere?" (dedução ou confiança média): o valor em destaque, com sim e não;
 * - pergunta (sem saber): campo vazio com a pergunta e o botão de mandar a foto que ajuda.
 * Com children (exigência dos canais), o corpo do cartão é o campo que vem nele; o topo continua igual.
 */
export default function AttributeCard({ card, label, texts, onChange, onAnswer, onPhoto, busy, children }) {
  const fileRef = useRef(null);
  const id = `atributo-${card.key}`;
  const checking = card.card === CARD.CHECK && !card.edited;
  const confirmed = checking && card.answer === 'yes';
  const asking = card.card === CARD.ASK;
  const photoLabel = texts.sendPhoto[card.suggestPhoto];

  return (
    <li
      className={cx(
        'attribute-card',
        card.card === CARD.SEEN && 'attribute-card--seen',
        checking && 'attribute-card--check',
        confirmed && 'attribute-card--confirmed',
        asking && 'attribute-card--ask'
      )}
      data-enter="3"
    >
      <div className="attribute-card__head">
        <span className="attribute-card__label" id={`${id}-nome`}>
          {label}
        </span>
        {card.card === CARD.SEEN && (
          <StatusPill tone="green" size="sm">
            {texts.seen}
          </StatusPill>
        )}
        {checking && (
          <StatusPill tone={confirmed ? 'green' : 'honey'} size="sm">
            {confirmed ? texts.confirmed : texts.check}
          </StatusPill>
        )}
      </div>

      {children ?? (checking ? (
        <div className="attribute-card__check">
          <p className="attribute-card__value">{card.value}</p>
          <div className="attribute-card__answers" role="group" aria-labelledby={`${id}-nome`}>
            <button
              type="button"
              className={cx('attribute-card__answer', card.answer === 'yes' && 'attribute-card__answer--on')}
              aria-pressed={card.answer === 'yes'}
              onClick={() => onAnswer('yes')}
            >
              {texts.yes}
            </button>
            <button type="button" className="attribute-card__answer" onClick={() => onAnswer('no')}>
              {texts.no}
            </button>
          </div>
        </div>
      ) : (
        <TextField
          id={id}
          label={asking ? card.question || texts.wrongValue : label}
          value={card.value}
          placeholder={texts.answerPlaceholder}
          onChange={(event) => onChange(event.target.value)}
          className={cx('attribute-card__field', !asking && 'attribute-card__field--quiet')}
        />
      ))}

      {asking && photoLabel && (
        <>
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture="environment"
            className="visually-hidden"
            tabIndex={-1}
            aria-hidden="true"
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = '';
              if (file) onPhoto(file, card.suggestPhoto);
            }}
          />
          <Button
            variant="outline"
            size="sm"
            icon="camera"
            iconPosition="start"
            iconSize={15}
            loading={busy}
            loadingText={texts.readingPhoto}
            disabled={busy}
            onClick={() => fileRef.current?.click()}
            className="attribute-card__photo"
          >
            {photoLabel}
          </Button>
        </>
      )}

      {card.evidence && !asking && <p className="attribute-card__evidence">{texts.evidence(card.evidence)}</p>}
    </li>
  );
}
