import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './EmptyState.css';

/**
 * Estado vazio ilustrado: um ícone em camadas de luz, o título, o texto e as ações.
 * tone: 'paper' (sobre painel claro) | 'glass' (sobre painel escuro)
 */
export default function EmptyState({ icon = 'camera', title, text, tone = 'paper', children, className }) {
  return (
    <div className={cx('empty-state', `empty-state--${tone}`, className)}>
      <span className="empty-state__art" aria-hidden="true">
        <span className="empty-state__halo" />
        <span className="empty-state__ring" />
        <span className="empty-state__icon">
          <Icon name={icon} size={30} />
        </span>
        <Icon name="sparkle" size={16} className="empty-state__spark empty-state__spark--a" />
        <Icon name="sparkle" size={11} className="empty-state__spark empty-state__spark--b" />
      </span>
      <h3 className="heading empty-state__title">{title}</h3>
      {text && <p className="empty-state__text">{text}</p>}
      {children && <div className="empty-state__actions">{children}</div>}
    </div>
  );
}
