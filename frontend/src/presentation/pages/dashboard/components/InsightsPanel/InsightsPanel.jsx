import Button from '@/presentation/components/Button/Button.jsx';
import EmptyState from '@/presentation/components/EmptyState/EmptyState.jsx';
import Panel from '@/presentation/components/Panel/Panel.jsx';
import StatusPanel from '@/presentation/components/StatusPanel/StatusPanel.jsx';
import useInsights from '@/application/insights/useInsights.js';
import { INSIGHTS } from '@/domain/content/insightsContent.js';
import RevenueCard from './RevenueCard.jsx';
import CategoriesCard from './CategoriesCard.jsx';
import StockCard from './StockCard.jsx';
import PricesCard from './PricesCard.jsx';
import StalledCard from './StalledCard.jsx';
import './InsightsPanel.css';

/**
 * Aba "Insights" do painel: faturamento, vendas por categoria, estoque, preço x sugerido
 * e itens parados, um cartão por arquivo nesta pasta. As vendas são simuladas a partir
 * dos anúncios da conta (selo "Simulação").
 */
export default function InsightsPanel({ active }) {
  const insights = useInsights(active);

  if (insights.status === 'loading' || insights.status === 'idle') return <StatusPanel text={INSIGHTS.loading} />;

  if (insights.status === 'error') {
    return (
      <StatusPanel status="error" text={INSIGHTS.loadError.title} retryLabel={INSIGHTS.loadError.retry} onRetry={insights.retry} />
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

  return (
    <div className="insights-panel">
      <RevenueCard data={data} />
      <CategoriesCard data={data} />
      <StockCard data={data} />
      <PricesCard data={data} />
      <StalledCard data={data} />
    </div>
  );
}
