import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './ComparisonCard.css';

/** Check que se "desenha" (o traço é animado pelo JS via data-part="check"). */
function DrawnCheck() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className="comparison-card__check" aria-hidden="true">
      <path data-part="check" d="M5 12.5l4 4L19 7" pathLength="1" className="comparison-card__check-path" />
    </svg>
  );
}

/**
 * Coluna do comparativo. O mesmo componente desenha os dois lados:
 * `highlight` ativa o visual escuro da Quick Click com checks animados.
 */
export default function ComparisonCard({ highlight = false, label, ribbon, title, items, ...rest }) {
  return (
    <div className={cx('comparison-card', highlight && 'comparison-card--highlight')} {...rest}>
      {ribbon && <span className="comparison-card__ribbon">{ribbon}</span>}
      {label && <p className="comparison-card__label">{label}</p>}
      {title && <p className="comparison-card__title">{title}</p>}
      <ul className="comparison-card__list">
        {items.map((text) => (
          <li key={text} className="comparison-card__item">
            {highlight ? <DrawnCheck /> : <Icon name="x" size={18} className="comparison-card__cross" />}
            {text}
          </li>
        ))}
      </ul>
    </div>
  );
}
