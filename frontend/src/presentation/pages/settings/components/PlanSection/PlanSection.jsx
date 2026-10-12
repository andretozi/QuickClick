import Icon from '@/presentation/components/Icon/Icon.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import SettingsSection from '../SettingsSection/SettingsSection.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { PLANS } from '@/domain/content/landingContent.js';
import { PLAN_SECTION } from '@/domain/content/settingsContent.js';
import './PlanSection.css';

/** Plano: o atual em destaque e a comparação dos quatro (sem pagamento; troca em breve). */
export default function PlanSection({ planId }) {
  return (
    <SettingsSection id="plano" title={PLAN_SECTION.title} lead={PLAN_SECTION.lead}>
      <ul className="plan-section__grid">
        {PLANS.items.map((plan) => {
          const current = plan.id === planId;
          return (
            <li
              key={plan.id}
              className={cx('plan-section__card', current && 'plan-section__card--current', plan.featured && 'plan-section__card--featured')}
              aria-current={current ? 'true' : undefined}
            >
              <div className="plan-section__top">
                <h3 className="plan-section__name">{plan.name}</h3>
                {current && (
                  <StatusPill tone="coral" size="sm">
                    {PLAN_SECTION.current}
                  </StatusPill>
                )}
                {!current && plan.featured && (
                  <StatusPill tone="honey" size="sm">
                    {PLAN_SECTION.recommended}
                  </StatusPill>
                )}
              </div>
              <p className="plan-section__price">
                {plan.price} <span className="plan-section__period">{plan.period}</span>
              </p>
              <p className="plan-section__tagline">{plan.tagline}</p>
              <ul className="plan-section__features">
                {plan.features.map((feature) => (
                  <li key={feature} className="plan-section__feature">
                    <Icon name="check" size={15} className="plan-section__check" />
                    {feature}
                  </li>
                ))}
              </ul>
            </li>
          );
        })}
      </ul>
      <p className="plan-section__soon">
        <Icon name="clock" size={16} />
        {PLAN_SECTION.soon}
      </p>
    </SettingsSection>
  );
}
