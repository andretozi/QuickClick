import Icon from '@/presentation/components/Icon/Icon.jsx';
import './BenefitCard.css';

/** Cartão de vantagem: ícone colorido + título + texto. tone: 'coral' | 'honey' | 'green' */
export default function BenefitCard({ icon, tone, title, description, ...rest }) {
  return (
    <article className="benefit-card" {...rest}>
      <div className={`benefit-card__icon benefit-card__icon--${tone}`}>
        <Icon name={icon} size={26} />
      </div>
      <h3 className="heading benefit-card__title">{title}</h3>
      <p className="benefit-card__description">{description}</p>
    </article>
  );
}
