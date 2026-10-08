import Button from '@/presentation/components/Button/Button.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './PlanCard.css';

/**
 * Cartão de um plano. `featured` é o plano em destaque: fundo coral, fita de
 * recomendado e a faixa de brilho da cena "pricing" (data-scene + data-part="shine").
 */
export default function PlanCard({
  name,
  price,
  period,
  tagline,
  features,
  cta,
  featured = false,
  recommendedLabel,
  ...rest
}) {
  return (
    <article
      className={cx('plan-card', featured && 'plan-card--featured')}
      data-scene={featured ? 'pricing' : undefined}
      {...rest}
    >
      {featured && <span data-part="shine" className="plan-card__shine" aria-hidden="true" />}
      {featured && <span className="plan-card__ribbon">{recommendedLabel}</span>}

      <h3 className="heading plan-card__name">{name}</h3>
      <p className="plan-card__tagline">{tagline}</p>

      <p className="plan-card__price">
        <span className="plan-card__amount">{price}</span>
        <span className="plan-card__period">{period}</span>
      </p>

      <ul className="plan-card__features">
        {features.map((feature) => (
          <li key={feature} className="plan-card__feature">
            <Icon name="check" size={18} className="plan-card__check" />
            {feature}
          </li>
        ))}
      </ul>

      <Button href={cta.href} variant={featured ? 'dark' : 'outline'} size="block">
        {cta.label}
      </Button>
    </article>
  );
}
