import AreaChart from '@/presentation/components/charts/AreaChart/AreaChart.jsx';
import CountUp from '@/presentation/components/CountUp/CountUp.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import SimulationBadge from '@/presentation/components/SimulationBadge/SimulationBadge.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { formatMoney, formatShortDate } from '@/domain/format/format.js';
import { INSIGHTS } from '@/domain/content/insightsContent.js';
import InsightCard from './InsightCard.jsx';

/** Índices dos rótulos do eixo de datas: começo, meio e fim. */
const ticksFor = (count) => (count > 2 ? [0, Math.floor((count - 1) / 2), count - 1] : [0]);

/** Faturamento dos últimos 30 dias: total, variação, pedidos, ticket e o gráfico (com tabela para leitor de tela). */
export default function RevenueCard({ data }) {
  const { revenue } = INSIGHTS;
  const { totals } = data;
  const points = data.revenue.map((day) => ({
    label: formatShortDate(day.date),
    value: day.cents,
    lines: [formatMoney(day.cents), revenue.orders(day.orders)]
  }));

  return (
    <InsightCard id="ins-faturamento" title={revenue.title} badge={<SimulationBadge />} wide enter="2">
      <div className="insights-panel__totals">
        <p className="insights-panel__big">
          <CountUp value={totals.revenueCents} format="money" />
        </p>
        <p className={cx('insights-panel__change', totals.changePercent < 0 && 'insights-panel__change--down')}>
          <Icon name={totals.changePercent < 0 ? 'trend-down' : 'trend-up'} size={16} />
          {revenue.change(totals.changePercent)}
        </p>
        <p className="insights-panel__sub">
          {revenue.summary(revenue.orders(totals.orders), revenue.ticket(formatMoney(totals.ticketCents)))}
        </p>
      </div>
      <AreaChart data={points} ticks={ticksFor(points.length)} label={revenue.chartLabel}>
        <table className="visually-hidden">
          <caption>{revenue.tableCaption}</caption>
          <thead>
            <tr>
              <th scope="col">{revenue.columns.day}</th>
              <th scope="col">{revenue.columns.revenue}</th>
              <th scope="col">{revenue.columns.orders}</th>
            </tr>
          </thead>
          <tbody>
            {data.revenue.map((day) => (
              <tr key={day.date}>
                <td>{formatShortDate(day.date)}</td>
                <td>{formatMoney(day.cents)}</td>
                <td>{day.orders}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </AreaChart>
    </InsightCard>
  );
}
