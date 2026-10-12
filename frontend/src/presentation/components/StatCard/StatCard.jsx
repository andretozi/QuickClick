import CountUp from '@/presentation/components/CountUp/CountUp.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './StatCard.css';

/**
 * Número de destaque do painel, em vidro escuro, que conta ao aparecer.
 * tone: 'coral' | 'honey' | 'green' | 'cream' (cor do ícone e do brilho)
 * format: 'number' | 'money' (valor em centavos)
 */
export default function StatCard({ icon, label, value, format = 'number', foot, tone = 'coral', delay = 0, className }) {
  return (
    <li data-enter="2" className={cx('stat-card', `stat-card--${tone}`, className)}>
      <span className="stat-card__icon" aria-hidden="true">
        <Icon name={icon} size={20} />
      </span>
      <p className="stat-card__label">{label}</p>
      <p className="stat-card__value">
        <CountUp value={value} format={format} delay={delay} />
      </p>
      {foot && <p className="stat-card__foot">{foot}</p>}
    </li>
  );
}
