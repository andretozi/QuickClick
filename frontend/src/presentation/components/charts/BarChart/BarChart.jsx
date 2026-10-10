import { useRef } from 'react';
import useChartAnimation from '@/application/animation/useChartAnimation.js';
import { cx } from '@/presentation/utils/cx.js';
import './BarChart.css';

/**
 * Barras horizontais em SVG próprio, crescendo uma depois da outra.
 * - items: [{ id, label, value, display }] (display é o texto ao lado da barra)
 * - tone: 'coral' | 'honey'
 * - label: descrição do gráfico para o leitor de tela
 */
export default function BarChart({ items, label, tone = 'coral', className }) {
  const ref = useRef(null);
  useChartAnimation(ref);
  const max = Math.max(1, ...items.map((item) => item.value));

  return (
    <div ref={ref} className={cx('bar-chart', `bar-chart--${tone}`, className)}>
      <ul className="bar-chart__list" aria-label={label}>
        {items.map((item, index) => (
          <li key={item.id} className="bar-chart__row">
            <span className="bar-chart__label">{item.label}</span>
            <svg className="bar-chart__svg" viewBox="0 0 100 10" preserveAspectRatio="none" aria-hidden="true">
              <rect className="bar-chart__track" x="0" y="0" width="100" height="10" rx="5" />
              <rect
                data-chart-grow
                data-delay={index * 90}
                className="bar-chart__bar"
                x="0"
                y="0"
                width={Math.max(2, (item.value / max) * 100)}
                height="10"
                rx="5"
              />
            </svg>
            <span className="bar-chart__value">{item.display}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
