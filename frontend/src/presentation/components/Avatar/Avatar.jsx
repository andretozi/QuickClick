import { cx } from '@/presentation/utils/cx.js';
import { initials } from '@/domain/format/format.js';
import './Avatar.css';

/**
 * Iniciais do vendedor num círculo com degradê.
 * - color: 'coral' (coral e mel, o padrão) | 'honey' | 'green' | 'cocoa'
 * - size: 'sm' | 'md' | 'lg' | 'xl'
 * Decorativo: quem usa escreve o nome do vendedor ao lado ou no aria-label.
 */
export default function Avatar({ name, color = 'coral', size = 'md', className }) {
  return (
    <span aria-hidden="true" className={cx('avatar', `avatar--${color}`, `avatar--${size}`, className)}>
      {initials(name)}
    </span>
  );
}
