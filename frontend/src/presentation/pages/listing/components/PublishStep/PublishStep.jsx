import { formatMoney } from '@/domain/format/format.js';
import { categoryLabel, conditionLabel, LISTING_WIZARD } from '@/domain/content/listingContent.js';
import './PublishStep.css';

/** Passo 5: o resumo, com atalho para alterar cada parte. O botão de publicar fica no rodapé. */
export default function PublishStep({ editor }) {
  const { draft, priceCents, willPublish, goTo, steps } = editor;
  const { title, lead, summary, channelsNone, channelsMl } = LISTING_WIZARD.publish;
  const stepOf = (name) => steps.indexOf(name);
  // a capa vem primeiro (e ocupa o dobro)
  const photos = [draft.photos[draft.coverIndex], ...draft.photos.filter((_, i) => i !== draft.coverIndex)].filter(Boolean);

  const rows = [
    { id: 'title', label: summary.title, value: draft.title, step: 'details' },
    { id: 'category', label: summary.category, value: categoryLabel(draft.category), step: 'details' },
    { id: 'condition', label: summary.condition, value: conditionLabel(draft.condition), step: 'details' },
    { id: 'stock', label: summary.stock, value: draft.stock, step: 'details' },
    { id: 'price', label: summary.price, value: priceCents !== null ? formatMoney(priceCents) : '', step: 'price' },
    { id: 'channels', label: summary.channels, value: willPublish ? channelsMl : channelsNone, step: 'channels' }
  ];

  return (
    <div className="publish-step">
      <header>
        <h2 className="heading publish-step__title">{title}</h2>
        <p className="publish-step__lead">{lead}</p>
      </header>

      <div className="publish-step__layout">
        <div className="publish-step__photos">
          <p className="publish-step__label">{summary.photos}</p>
          <ul className="publish-step__thumbs">
            {photos.map((photo, index) => (
              <li key={`${index}-${photo.length}`} className="publish-step__thumb">
                <img src={photo} alt="" />
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="publish-step__edit"
            onClick={() => goTo(stepOf('photos'))}
            aria-label={summary.editLabel(summary.photos)}
          >
            {summary.edit}
          </button>
        </div>

        <dl className="publish-step__list">
          {rows.map((row) => (
            <div key={row.id} className="publish-step__row">
              <dt className="publish-step__label">{row.label}</dt>
              <dd className="publish-step__value">{row.value}</dd>
              <dd className="publish-step__action">
                <button
                  type="button"
                  className="publish-step__edit"
                  onClick={() => goTo(stepOf(row.step))}
                  aria-label={summary.editLabel(row.label)}
                >
                  {summary.edit}
                </button>
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
