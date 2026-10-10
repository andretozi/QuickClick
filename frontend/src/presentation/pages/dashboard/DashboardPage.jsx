import Button from '@/presentation/components/Button/Button.jsx';
import Modal from '@/presentation/components/Modal/Modal.jsx';
import PageHeader from '@/presentation/components/PageHeader/PageHeader.jsx';
import SegmentedControl from '@/presentation/components/SegmentedControl/SegmentedControl.jsx';
import StatCard from '@/presentation/components/StatCard/StatCard.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import WelcomeBanner from './components/WelcomeBanner/WelcomeBanner.jsx';
import ListingsPanel from './components/ListingsPanel/ListingsPanel.jsx';
import InsightsPanel from './components/InsightsPanel/InsightsPanel.jsx';
import useDashboard, { DASHBOARD_TABS } from '@/application/listings/useDashboard.js';
import { firstName } from '@/domain/format/format.js';
import { DASHBOARD, LISTINGS_PANEL } from '@/domain/content/dashboardContent.js';
import { MARKETPLACE_CATALOG } from '@/domain/content/marketplacesContent.js';
import { planName } from '@/domain/content/appContent.js';
import './DashboardPage.css';

/**
 * Painel (#/painel): saudação, números da loja que contam ao aparecer e as abas
 * "Anúncios" e "Insights". Uma conta nova vê as boas vindas e o estado vazio.
 */
export default function DashboardPage() {
  const dashboard = useDashboard();
  const { account, hour, summary, connections, tab, setTab, welcome, pendingRemoval, removing } = dashboard;
  const { stats, tabs } = DASHBOARD;
  const connectedNames = connections
    .map((connection) => MARKETPLACE_CATALOG.find((item) => item.slug === connection.slug)?.name)
    .filter(Boolean);
  const name = firstName(account.name);

  return (
    <div className="dashboard">
      {welcome && <WelcomeBanner firstName={name} onClose={dashboard.dismissWelcome} />}

      <PageHeader
        eyebrow={account.store}
        title={DASHBOARD.greeting(hour, name)}
        lead={DASHBOARD.lead}
        actions={
          <Button href={DASHBOARD.newListing.href} icon="plus" iconPosition="start" iconSize={18}>
            {DASHBOARD.newListing.label}
          </Button>
        }
      >
        <StatusPill tone="cream" size="sm">
          {DASHBOARD.plan(planName(account.plan))}
        </StatusPill>
        <StatusPill tone={connections.length ? 'mint' : 'cream'} size="sm">
          {DASHBOARD.connected(connections.length)}
        </StatusPill>
      </PageHeader>

      <ul className="dashboard__stats" aria-label={stats.label}>
        <StatCard
          icon="trend-up"
          tone="coral"
          label={stats.active.label}
          value={summary.active}
          foot={stats.active.foot(summary.total)}
        />
        <StatCard
          icon="link"
          tone="green"
          label={stats.connected.label}
          value={connections.length}
          foot={stats.connected.foot(connectedNames)}
          delay={80}
        />
        <StatCard
          icon="package"
          tone="honey"
          label={stats.units.label}
          value={summary.units}
          foot={stats.units.foot(summary.withStock)}
          delay={160}
        />
        <StatCard
          icon="dollar"
          tone="cream"
          label={stats.value.label}
          value={summary.stockValueCents}
          format="money"
          foot={stats.value.foot}
          delay={240}
        />
      </ul>

      <SegmentedControl
        mode="tabs"
        idPrefix={tabs.idPrefix}
        label={tabs.label}
        value={tab}
        onChange={setTab}
        options={[
          { value: DASHBOARD_TABS.LISTINGS, label: tabs.listings, icon: 'grid' },
          { value: DASHBOARD_TABS.INSIGHTS, label: tabs.insights, icon: 'chart' }
        ]}
        className="dashboard__tabs"
      />

      <div
        role="tabpanel"
        id={`${tabs.idPrefix}-painel-${tab}`}
        aria-labelledby={`${tabs.idPrefix}-aba-${tab}`}
        className="dashboard__panel"
      >
        {tab === DASHBOARD_TABS.LISTINGS ? <ListingsPanel dashboard={dashboard} /> : <InsightsPanel active />}
      </div>

      <Modal
        open={Boolean(pendingRemoval)}
        onClose={dashboard.cancelRemoval}
        dismissible={!removing}
        icon="trash"
        iconTone="danger"
        size="sm"
        title={LISTINGS_PANEL.confirmDelete.title}
        description={pendingRemoval ? LISTINGS_PANEL.confirmDelete.text(pendingRemoval.title) : ''}
        actions={
          <>
            <Button variant="outline" onClick={dashboard.cancelRemoval} disabled={removing} data-autofocus>
              {LISTINGS_PANEL.confirmDelete.cancel}
            </Button>
            <Button
              onClick={dashboard.confirmRemoval}
              loading={removing}
              loadingText={LISTINGS_PANEL.confirmDelete.deleting}
              disabled={removing}
            >
              {LISTINGS_PANEL.confirmDelete.confirm}
            </Button>
          </>
        }
      />
    </div>
  );
}
