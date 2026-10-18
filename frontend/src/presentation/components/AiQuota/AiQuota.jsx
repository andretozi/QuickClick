import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './AiQuota.css';

/**
 * Selo do plano e as análises da IA que sobram no mês, sempre à vista no assistente.
 * - plan: nome do plano; remaining: texto das análises; empty: sem análises (tom de alerta)
 */
export default function AiQuota({ plan, remaining, empty = false, className }) {
  return (
    <p className={cx('ai-quota', empty && 'ai-quota--empty', className)} aria-live="polite">
      <span className="ai-quota__plan">
        <Icon name="sparkles" size={14} />
        {plan}
      </span>
      <span className="ai-quota__count">{remaining}</span>
    </p>
  );
}
