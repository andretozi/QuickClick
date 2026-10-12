import { useRef } from 'react';
import ChartLegend from '../ChartLegend/ChartLegend.jsx';
import ChartTooltip from '../ChartTooltip/ChartTooltip.jsx';
import useChartAnimation from '@/application/animation/useChartAnimation.js';
import useChartHover from '@/application/ui/useChartHover.js';
import { cx } from '@/presentation/utils/cx.js';
import './DonutChart.css';

const RADIUS = 70;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const GAP = 3; // respiro entre as fatias
const TONES = 6;

/**
 * Rosca em SVG próprio: cada fatia é um círculo com stroke-dasharray, girando até o lugar.
 * Passar o mouse numa fatia (ou na legenda) destaca a fatia e mostra o balão.
 * - items: [{ id, label, value, display }] (display: texto do balão e da legenda)
 * - total: número do centro; centerLabel: a palavra embaixo dele
 */
export default function DonutChart({ items, total, centerLabel, label, legendLabel, className }) {
  const ref = useRef(null);
  useChartAnimation(ref);
  const hover = useChartHover(items.length);
  const sum = Math.max(1, items.reduce((acc, item) => acc + item.value, 0));

  let offset = 0;
  const segments = items.map((item, index) => {
    const length = Math.max(0.5, (item.value / sum) * CIRCUMFERENCE - (items.length > 1 ? GAP : 0));
    const segment = { ...item, length, offset, tone: (index % TONES) + 1 };
    offset += (item.value / sum) * CIRCUMFERENCE;
    return segment;
  });

  const active = hover.active;

  return (
    <div ref={ref} className={cx('donut-chart', className)}>
      <div className="donut-chart__figure">
        <svg className="donut-chart__svg" viewBox="0 0 180 180" role="img" aria-label={label}>
          <circle className="donut-chart__track" cx="90" cy="90" r={RADIUS} />
          <g transform="rotate(-90 90 90)">
            {segments.map((segment, index) => (
              <circle
                key={segment.id}
                data-chart-arc
                data-length={segment.length}
                data-delay={index * 120}
                className={cx(
                  'donut-chart__segment',
                  `donut-chart__segment--${segment.tone}`,
                  active === index && 'donut-chart__segment--active',
                  active !== null && active !== index && 'donut-chart__segment--dim'
                )}
                cx="90"
                cy="90"
                r={RADIUS}
                strokeDasharray={`${segment.length} ${CIRCUMFERENCE - segment.length}`}
                strokeDashoffset={-segment.offset}
                onPointerEnter={() => hover.setActive(index)}
                onPointerLeave={hover.onPointerLeave}
              />
            ))}
          </g>
        </svg>
        <p className="donut-chart__center" aria-hidden="true">
          <span className="donut-chart__total">{total}</span>
          <span className="donut-chart__caption">{centerLabel}</span>
        </p>
        {active !== null && <ChartTooltip x={50} title={items[active].label} lines={[items[active].display]} />}
      </div>
      <ChartLegend
        label={legendLabel}
        active={active}
        onFocusItem={hover.setActive}
        className="donut-chart__legend"
        items={segments.map((segment) => ({ id: segment.id, label: segment.label, value: segment.display, tone: segment.tone }))}
      />
    </div>
  );
}
