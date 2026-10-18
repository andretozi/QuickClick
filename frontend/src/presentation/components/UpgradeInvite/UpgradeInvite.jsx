import Button from '@/presentation/components/Button/Button.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './UpgradeInvite.css';

/** Convite discreto do plano pago (no Grátis): o que a IA completa faria aqui, sem atrapalhar. */
export default function UpgradeInvite({ title, text, action, className }) {
  return (
    <aside className={cx('upgrade-invite', className)}>
      <span className="upgrade-invite__icon" aria-hidden="true">
        <Icon name="sparkles" size={18} />
      </span>
      <div className="upgrade-invite__text">
        <p className="upgrade-invite__title">{title}</p>
        <p className="upgrade-invite__body">{text}</p>
      </div>
      {action && (
        <Button href={action.href} variant="outline" size="sm" className="upgrade-invite__action">
          {action.label}
        </Button>
      )}
    </aside>
  );
}
