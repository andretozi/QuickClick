import Button from '@/presentation/components/Button/Button.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import Modal from '@/presentation/components/Modal/Modal.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import SettingsSection from '../SettingsSection/SettingsSection.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { PLANS } from '@/domain/content/landingContent.js';
import { PLAN_SECTION } from '@/domain/content/settingsContent.js';
import './PlanSection.css';

/**
 * Plano: o atual em destaque e a comparação dos quatro. Nos outros, "Mudar para este plano"
 * abre a confirmação (no MVP a troca é na hora e sem pagamento); com a troca livre desligada,
 * o botão vira "Em breve".
 */
export default function PlanSection({ planId, plan }) {
  const { modal } = PLAN_SECTION;
  const target = PLANS.items.find((item) => item.id === plan.target);

  return (
    <SettingsSection id="plano" title={PLAN_SECTION.title} lead={PLAN_SECTION.lead}>
      <ul className="plan-section__grid">
        {PLANS.items.map((item) => {
          const current = item.id === planId;
          return (
            <li
              key={item.id}
              className={cx('plan-section__card', current && 'plan-section__card--current', item.featured && 'plan-section__card--featured')}
              aria-current={current ? 'true' : undefined}
            >
              <div className="plan-section__top">
                <h3 className="plan-section__name">{item.name}</h3>
                {current && (
                  <StatusPill tone="coral" size="sm">
                    {PLAN_SECTION.current}
                  </StatusPill>
                )}
                {!current && item.featured && (
                  <StatusPill tone="honey" size="sm">
                    {PLAN_SECTION.recommended}
                  </StatusPill>
                )}
              </div>
              <p className="plan-section__price">
                {item.price} <span className="plan-section__period">{item.period}</span>
              </p>
              <p className="plan-section__tagline">{item.tagline}</p>
              <ul className="plan-section__features">
                {item.features.map((feature) => (
                  <li key={feature} className="plan-section__feature">
                    <Icon name="check" size={15} className="plan-section__check" />
                    {feature}
                  </li>
                ))}
              </ul>
              {!current && (
                <Button
                  variant={item.featured ? 'primary' : 'outline'}
                  size="sm"
                  icon={plan.free ? 'arrow-right' : 'clock'}
                  iconSize={15}
                  disabled={!plan.free}
                  aria-label={plan.free ? PLAN_SECTION.changeLabel(item.name) : undefined}
                  onClick={() => plan.open(item.id)}
                  className="plan-section__change"
                >
                  {plan.free ? PLAN_SECTION.change : PLAN_SECTION.soon}
                </Button>
              )}
            </li>
          );
        })}
      </ul>
      {!plan.free && (
        <p className="plan-section__soon">
          <Icon name="clock" size={16} />
          {PLAN_SECTION.soonReason}
        </p>
      )}

      <Modal
        open={plan.confirming}
        onClose={plan.cancel}
        dismissible={!plan.changing}
        size="sm"
        icon="star"
        iconTone="honey"
        title={modal.title}
        description={modal.text}
        actions={
          <>
            <Button variant="outline" onClick={plan.cancel} disabled={plan.changing}>
              {modal.cancel}
            </Button>
            <Button
              onClick={plan.confirm}
              loading={plan.changing}
              loadingText={modal.confirming}
              disabled={plan.changing}
              data-autofocus
            >
              {target ? modal.confirm(target.name) : ''}
            </Button>
          </>
        }
      />
    </SettingsSection>
  );
}
