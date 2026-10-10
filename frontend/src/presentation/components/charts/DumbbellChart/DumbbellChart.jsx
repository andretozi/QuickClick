import { useRef } from 'react';
import ChartLegend from '../ChartLegend/ChartLegend.jsx';
import useChartAnimation from '@/application/animation/useChartAnimation.js';
import { cx } from '@/presentation/utils/cx.js';
import './DumbbellChart.css';

/**
 * Halteres: o preço atual e o sugerido de cada anúncio, ligados por uma barra, numa
 * escala comum a todos.
 * - rows: [{ id, title, current, suggested, note, description }]
 *   (description é o texto completo para o leitor de tela)
 * - legend: { current, suggested } (os nomes das duas pontas)
 */
export default function DumbbellChart({ rows, legend, label, legendLabel, className }) {
  const ref = useRef(null);
  useChartAnimation(ref);
  const values = rows.flatMap((row) => [row.current, row.suggested]);
  const min = Math.min(...values) * 0.9;
  const max = Math.max(...values) * 1.05;
  const position = (value) => 4 + ((value - min) / Math.max(1, max - min)) * 92;

  return (
    <div ref={ref} className={cx('dumbbell-chart', className)}>
      <ChartLegend
        label={legendLabel}
        className="dumbbell-chart__legend"
        items={[
          { id: 'current', label: legend.current, tone: 'coral' },
          { id: 'suggested', label: legend.suggested, tone: 'honey' }
        ]}
      />
      <ul className="dumbbell-chart__list" aria-label={label}>
        {rows.map((row, index) => {
          const a = position(row.current);
          const b = position(row.suggested);
          return (
            <li key={row.id} className="dumbbell-chart__row">
              <p className="dumbbell-chart__title">{row.title}</p>
              <div className="dumbbell-chart__track" aria-hidden="true">
                <svg className="dumbbell-chart__svg" viewBox="0 0 100 20" preserveAspectRatio="none">
                  <line className="dumbbell-chart__axis" x1="0" x2="100" y1="10" y2="10" />
                  <line
                    data-chart-grow
                    data-delay={index * 110}
                    className="dumbbell-chart__bar"
                    x1={Math.min(a, b)}
                    x2={Math.max(a, b)}
                    y1="10"
                    y2="10"
                  />
                </svg>
                <span
                  data-chart-pop
                  data-delay={index * 110}
                  className="dumbbell-chart__dot dumbbell-chart__dot--suggested"
                  style={{ left: `${b}%` }}
                />
                <span
                  data-chart-pop
                  data-delay={index * 110 + 80}
                  className="dumbbell-chart__dot dumbbell-chart__dot--current"
                  style={{ left: `${a}%` }}
                />
              </div>
              <p className="dumbbell-chart__note">
                <span className="visually-hidden">{row.description}</span>
                <span aria-hidden="true">{row.note}</span>
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
