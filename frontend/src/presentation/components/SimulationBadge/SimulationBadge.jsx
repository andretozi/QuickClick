import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { SIMULATION_BADGE } from '@/domain/content/commonContent.js';
import './SimulationBadge.css';

/** Selo "Simulação" nos números que ainda não vêm de vendas de verdade (com a explicação). */
export default function SimulationBadge({ className }) {
  return (
    <span className={cx('simulation-badge', className)} title={SIMULATION_BADGE.hint}>
      <Icon name="sparkle" size={13} className="simulation-badge__icon" />
      {SIMULATION_BADGE.label}
      <span className="visually-hidden">{SIMULATION_BADGE.hint}</span>
    </span>
  );
}
