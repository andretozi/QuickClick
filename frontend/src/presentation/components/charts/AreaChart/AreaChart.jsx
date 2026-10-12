import { useId, useMemo, useRef } from 'react';
import ChartTooltip from '../ChartTooltip/ChartTooltip.jsx';
import useChartAnimation from '@/application/animation/useChartAnimation.js';
import useChartHover from '@/application/ui/useChartHover.js';
import { cx } from '@/presentation/utils/cx.js';
import './AreaChart.css';

const WIDTH = 640;
const HEIGHT = 220;
const PAD_TOP = 18;
const PAD_BOTTOM = 8;

/** Curva suave (Catmull Rom convertida em Bézier) passando por todos os pontos. */
function smoothPath(points) {
  return points.reduce((path, point, i) => {
    if (i === 0) return `M${point.x},${point.y}`;
    const p0 = points[i - 2] ?? points[i - 1];
    const p1 = points[i - 1];
    const p2 = point;
    const p3 = points[i + 1] ?? point;
    const c1 = { x: p1.x + (p2.x - p0.x) / 6, y: p1.y + (p2.y - p0.y) / 6 };
    const c2 = { x: p2.x - (p3.x - p1.x) / 6, y: p2.y - (p3.y - p1.y) / 6 };
    return `${path} C${c1.x.toFixed(1)},${c1.y.toFixed(1)} ${c2.x.toFixed(1)},${c2.y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
  }, '');
}

/**
 * Gráfico de área em SVG próprio, com a linha se desenhando, linhas de grade, eixo
 * de datas e o balão no ponto em foco (mouse, toque ou setas do teclado).
 * - data: [{ label, value, lines: [texto do balão] }]
 * - ticks: rótulos do eixo de baixo (índices de data)
 * - label: descrição para o leitor de tela (a tabela de dados vem em `children`)
 */
export default function AreaChart({ data, ticks = [], label, className, children }) {
  const ref = useRef(null);
  useChartAnimation(ref);
  const id = useId();
  const hover = useChartHover(data.length);

  const { points, line, area } = useMemo(() => {
    const top = Math.max(1, ...data.map((item) => item.value));
    const span = HEIGHT - PAD_TOP - PAD_BOTTOM;
    const pts = data.map((item, i) => ({
      x: data.length > 1 ? (i / (data.length - 1)) * WIDTH : WIDTH / 2,
      y: PAD_TOP + span - (item.value / top) * span
    }));
    const path = smoothPath(pts);
    return { points: pts, line: path, area: `${path} L${WIDTH},${HEIGHT} L0,${HEIGHT} Z` };
  }, [data]);

  const active = hover.active;
  const focus = active !== null ? points[active] : null;

  return (
    <div ref={ref} className={cx('area-chart', className)}>
      <div className="area-chart__plot">
        <svg
          className="area-chart__svg"
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          role="img"
          aria-label={label}
          tabIndex={0}
          onPointerMove={hover.onPointerMove}
          onPointerLeave={hover.onPointerLeave}
          onKeyDown={hover.onKeyDown}
          onBlur={hover.onBlur}
        >
          <defs>
            <linearGradient id={`${id}-area`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" className="area-chart__stop area-chart__stop--top" />
              <stop offset="100%" className="area-chart__stop area-chart__stop--bottom" />
            </linearGradient>
            <linearGradient id={`${id}-line`} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" className="area-chart__stop area-chart__stop--honey" />
              <stop offset="100%" className="area-chart__stop area-chart__stop--coral" />
            </linearGradient>
          </defs>
          {[0.25, 0.5, 0.75].map((fraction) => (
            <line
              key={fraction}
              className="area-chart__grid"
              x1="0"
              x2={WIDTH}
              y1={PAD_TOP + (HEIGHT - PAD_TOP - PAD_BOTTOM) * fraction}
              y2={PAD_TOP + (HEIGHT - PAD_TOP - PAD_BOTTOM) * fraction}
            />
          ))}
          <path data-chart-rise className="area-chart__area" d={area} fill={`url(#${id}-area)`} />
          <path data-chart-draw className="area-chart__line" d={line} stroke={`url(#${id}-line)`} />
          {focus && (
            <g className="area-chart__focus">
              <line className="area-chart__rule" x1={focus.x} x2={focus.x} y1="0" y2={HEIGHT} />
            </g>
          )}
        </svg>
        {/* O ponto fica fora do SVG esticado, para continuar redondo */}
        {focus && (
          <span
            className="area-chart__dot"
            style={{ left: `${(focus.x / WIDTH) * 100}%`, top: `${(focus.y / HEIGHT) * 100}%` }}
            aria-hidden="true"
          />
        )}
        {active !== null && (
          <ChartTooltip x={(focus.x / WIDTH) * 100} title={data[active].label} lines={data[active].lines} />
        )}
      </div>
      <div className="area-chart__axis" aria-hidden="true">
        {ticks.map((index) => (
          <span key={index} className="area-chart__tick" style={{ left: `${(index / Math.max(1, data.length - 1)) * 100}%` }}>
            {data[index]?.label}
          </span>
        ))}
      </div>
      {children}
    </div>
  );
}
