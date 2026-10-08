import Button from '@/presentation/components/Button/Button.jsx';
import Eyebrow from '@/presentation/components/Eyebrow/Eyebrow.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { PLAN_PANEL } from '@/domain/content/marketplacesContent.js';
import './PlanPanel.css';

/**
 * Plano atual do vendedor: quantos marketplaces usa, o aviso do limite e,
 * quando o limite é atingido, o caminho para conhecer os planos.
 */
export default function PlanPanel({ seller, ...rest }) {
  const { plan, connectedCount, canConnectMore, upgradePlan } = seller;
  const limited = plan.limit !== null;
  const reached = !canConnectMore;
  const notice =
    limited && upgradePlan
      ? PLAN_PANEL.limitNotice({ planName: plan.name, limit: plan.limit, upgradePlanName: upgradePlan.name })
      : PLAN_PANEL.unlimitedNotice({ planName: plan.name });

  return (
    <section className={cx('plan-panel', reached && 'plan-panel--reached')} aria-label={PLAN_PANEL.label} {...rest}>
      <div className="plan-panel__summary">
        <Eyebrow className="plan-panel__eyebrow">{PLAN_PANEL.eyebrow}</Eyebrow>
        <p className="heading plan-panel__name">{PLAN_PANEL.planName(plan.name)}</p>
        <p className="plan-panel__usage">{PLAN_PANEL.usage({ used: connectedCount, limit: plan.limit })}</p>
        {limited && (
          <span className="plan-panel__meter" aria-hidden="true">
            <span
              className="plan-panel__meter-fill"
              style={{ '--fill': `${Math.min(connectedCount / plan.limit, 1) * 100}%` }}
            />
          </span>
        )}
      </div>

      <div className="plan-panel__notice">
        <p className="plan-panel__text">{notice}</p>
        {reached && (
          <Button href={PLAN_PANEL.plansLink.href} size="sm" icon="arrow-right" iconSize={16}>
            {PLAN_PANEL.plansLink.label}
          </Button>
        )}
      </div>
    </section>
  );
}
