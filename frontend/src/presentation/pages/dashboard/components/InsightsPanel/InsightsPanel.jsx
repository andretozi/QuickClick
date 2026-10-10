import AreaChart from '@/presentation/components/charts/AreaChart/AreaChart.jsx';
import BarChart from '@/presentation/components/charts/BarChart/BarChart.jsx';
import DonutChart from '@/presentation/components/charts/DonutChart/DonutChart.jsx';
import DumbbellChart from '@/presentation/components/charts/DumbbellChart/DumbbellChart.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import EmptyState from '@/presentation/components/EmptyState/EmptyState.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import Panel from '@/presentation/components/Panel/Panel.jsx';
import SimulationBadge from '@/presentation/components/SimulationBadge/SimulationBadge.jsx';
import CountUp from '@/presentation/components/CountUp/CountUp.jsx';
import { cx } from '@/presentation/utils/cx.js';
import useInsights from '@/application/insights/useInsights.js';
import { formatMoney, formatNumber, formatShortDate } from '@/domain/format/format.js';
import { categoryLabel } from '@/domain/content/listingContent.js';
import { INSIGHTS } from '@/domain/content/insightsContent.js';
import { hrefForListing } from '@/application/navigation/routes.js';
import './InsightsPanel.css';

/** Índices dos rótulos do eixo de datas: começo, meio e fim. */
const ticksFor = (count) => (count > 2 ? [0, Math.floor((count - 1) / 2), count - 1] : [0]);

/**
 * Aba "Insights" do painel: faturamento, vendas por categoria, estoque, preço x sugerido
 * e itens parados. As vendas são simuladas a partir dos anúncios da conta (selo "Simulação").
 */
export default function InsightsPanel({ active }) {
  const insights = useInsights(active);
  const { revenue, categories, stock, prices, stalled } = INSIGHTS;

  if (insights.status === 'loading' || insights.status === 'idle') {
    return (
      <Panel tone="glass" className="insights-panel__status" role="status">
        <span data-spin className="insights-panel__spinner" aria-hidden="true" />
        {INSIGHTS.loading}
      </Panel>
    );
  }

  if (insights.status === 'error') {
    return (
      <Panel tone="glass" className="insights-panel__status" role="alert">
        <p className="insights-panel__status-title">{INSIGHTS.loadError.title}</p>
        <Button size="sm" variant="light" onClick={insights.retry}>
          {INSIGHTS.loadError.retry}
        </Button>
      </Panel>
    );
  }

  const data = insights.data;
  if (!data) {
    return (
      <Panel tone="glass" data-enter="2">
        <EmptyState icon="chart" tone="glass" title={INSIGHTS.emptyAll.title} text={INSIGHTS.emptyAll.text}>
          <Button href={INSIGHTS.emptyAll.cta.href} icon="plus" iconPosition="start" iconSize={18}>
            {INSIGHTS.emptyAll.cta.label}
          </Button>
        </EmptyState>
      </Panel>
    );
  }

  const { totals } = data;
  const revenuePoints = data.revenue.map((day) => ({
    label: formatShortDate(day.date),
    value: day.cents,
    lines: [formatMoney(day.cents), revenue.orders(day.orders)]
  }));
  const stockTotal = data.stockByCategory.reduce((sum, item) => sum + item.units, 0);

  return (
    <div className="insights-panel">
      {/* Faturamento */}
      <Panel tone="glass" data-enter="2" className="insights-panel__card insights-panel__card--wide" aria-labelledby="ins-faturamento">
        <header className="insights-panel__head">
          <h2 id="ins-faturamento" className="heading insights-panel__title">
            {revenue.title}
          </h2>
          <SimulationBadge />
        </header>
        <div className="insights-panel__totals">
          <p className="insights-panel__big">
            <CountUp value={totals.revenueCents} format="money" />
          </p>
          <p className={cx('insights-panel__change', totals.changePercent < 0 && 'insights-panel__change--down')}>
            <Icon name={totals.changePercent < 0 ? 'trend-down' : 'trend-up'} size={16} />
            {revenue.change(totals.changePercent)}
          </p>
          <p className="insights-panel__sub">
            {revenue.orders(totals.orders)} · {revenue.ticket(formatMoney(totals.ticketCents))}
          </p>
        </div>
        <AreaChart data={revenuePoints} ticks={ticksFor(revenuePoints.length)} label={revenue.chartLabel}>
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
      </Panel>

      {/* Vendas por categoria */}
      <Panel tone="glass" data-enter="3" className="insights-panel__card" aria-labelledby="ins-categorias">
        <header className="insights-panel__head">
          <div>
            <h2 id="ins-categorias" className="heading insights-panel__title">
              {categories.title}
            </h2>
            <p className="insights-panel__subtitle">{categories.subtitle}</p>
          </div>
        </header>
        <BarChart
          label={categories.chartLabel}
          items={data.salesByCategory.map((item) => ({
            id: item.category,
            label: categoryLabel(item.category),
            value: item.units,
            display: categories.value(item.units)
          }))}
        />
      </Panel>

      {/* Estoque em rosca */}
      <Panel tone="glass" data-enter="3" className="insights-panel__card" aria-labelledby="ins-estoque">
        <header className="insights-panel__head">
          <div>
            <h2 id="ins-estoque" className="heading insights-panel__title">
              {stock.title}
            </h2>
            <p className="insights-panel__subtitle">{stock.subtitle}</p>
          </div>
        </header>
        {stockTotal > 0 ? (
          <DonutChart
            label={stock.chartLabel}
            legendLabel={INSIGHTS.legend}
            total={formatNumber(stockTotal)}
            centerLabel={stock.centerLabel}
            items={data.stockByCategory.map((item) => ({
              id: item.category,
              label: categoryLabel(item.category),
              value: item.units,
              display: stock.value(item.units, Math.round((item.units / stockTotal) * 100))
            }))}
          />
        ) : (
          <p className="insights-panel__empty">{INSIGHTS.empty}</p>
        )}
      </Panel>

      {/* Preço x sugerido */}
      <Panel tone="glass" data-enter="3" className="insights-panel__card" aria-labelledby="ins-precos">
        <header className="insights-panel__head">
          <div>
            <h2 id="ins-precos" className="heading insights-panel__title">
              {prices.title}
            </h2>
            <p className="insights-panel__subtitle">{prices.subtitle}</p>
          </div>
        </header>
        {data.priceComparison.length > 0 ? (
          <DumbbellChart
            label={prices.chartLabel}
            legendLabel={INSIGHTS.legend}
            legend={{ current: prices.current, suggested: prices.suggested }}
            rows={data.priceComparison.map((item) => {
              const diff = item.priceCents - item.suggestedCents;
              const note =
                diff === 0 ? prices.equal : diff > 0 ? prices.above(formatMoney(diff)) : prices.below(formatMoney(-diff));
              return {
                id: item.id,
                title: item.title,
                current: item.priceCents,
                suggested: item.suggestedCents,
                note,
                description: `${prices.current}: ${formatMoney(item.priceCents)}. ${prices.suggested}: ${formatMoney(item.suggestedCents)}. ${note}.`
              };
            })}
          />
        ) : (
          <p className="insights-panel__empty">{INSIGHTS.empty}</p>
        )}
      </Panel>

      {/* Itens parados */}
      <Panel tone="glass" data-enter="3" className="insights-panel__card" aria-labelledby="ins-parados">
        <header className="insights-panel__head">
          <div>
            <h2 id="ins-parados" className="heading insights-panel__title">
              {stalled.title}
            </h2>
            <p className="insights-panel__subtitle">{stalled.subtitle}</p>
          </div>
        </header>
        {data.stalled.length > 0 ? (
          <>
            <BarChart
              tone="honey"
              label={stalled.title}
              items={data.stalled.map((item) => ({
                id: item.id,
                label: item.title,
                value: item.days,
                display: stalled.days(item.days)
              }))}
            />
            <ul className="insights-panel__actions">
              {data.stalled.slice(0, 2).map((item) => (
                <li key={item.id}>
                  <a
                    href={hrefForListing(item.id)}
                    className="insights-panel__action"
                    aria-label={stalled.actionLabel(item.title)}
                  >
                    {stalled.action}
                    <span className="insights-panel__action-meta">{stalled.stock(item.stock)}</span>
                    <Icon name="arrow-right" size={15} />
                  </a>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="insights-panel__empty">{INSIGHTS.empty}</p>
        )}
      </Panel>
    </div>
  );
}
