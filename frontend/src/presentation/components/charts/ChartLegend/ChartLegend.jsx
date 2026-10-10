import { cx } from '@/presentation/utils/cx.js';
import './ChartLegend.css';

/**
 * Legenda de um gráfico. items: [{ id, label, value?, tone }] (tone de 1 a 6, ou
 * 'coral' e 'honey'). Com onFocusItem, cada item destaca a parte dele no gráfico.
 */
export default function ChartLegend({ label, items, active, onFocusItem, className }) {
  return (
    <ul className={cx('chart-legend', className)} aria-label={label}>
      {items.map((item, index) => (
        <li
          key={item.id}
          className={cx('chart-legend__item', active === index && 'chart-legend__item--active')}
          onPointerEnter={onFocusItem ? () => onFocusItem(index) : undefined}
          onPointerLeave={onFocusItem ? () => onFocusItem(null) : undefined}
        >
          <span className={cx('chart-legend__swatch', `chart-legend__swatch--${item.tone}`)} aria-hidden="true" />
          <span className="chart-legend__label">{item.label}</span>
          {item.value && <span className="chart-legend__value">{item.value}</span>}
        </li>
      ))}
    </ul>
  );
}
