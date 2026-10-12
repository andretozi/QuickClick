import { cx } from '@/presentation/utils/cx.js';
import './StatusPill.css';

/**
 * Selo de situação com um ponto colorido ("Publicado", "Pausado", "Plano Grátis"...).
 * tone: 'green' | 'honey' | 'muted' | 'coral' (fundo claro) · 'cream' | 'mint' (fundo escuro)
 */
export default function StatusPill({ tone = 'muted', size = 'md', className, children }) {
  return (
    <span className={cx('status-pill', `status-pill--${tone}`, `status-pill--${size}`, className)}>
      <span className="status-pill__dot" aria-hidden="true" />
      {children}
    </span>
  );
}
