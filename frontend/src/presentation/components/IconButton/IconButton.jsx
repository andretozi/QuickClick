import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './IconButton.css';

/**
 * Botão só com ícone. O `label` vira o nome acessível e a dica ao parar o mouse.
 * - tone: 'paper' (sobre fundo claro) | 'glass' (sobre fundo escuro) | 'danger'
 * - size: 'sm' | 'md'
 * Com `href`, vira link.
 */
export default function IconButton({ icon, label, tone = 'paper', size = 'md', href, iconSize, className, ...rest }) {
  const classes = cx('icon-button', `icon-button--${tone}`, `icon-button--${size}`, className);
  const glyph = <Icon name={icon} size={iconSize ?? (size === 'sm' ? 16 : 19)} />;

  if (href) {
    return (
      <a href={href} className={classes} aria-label={label} title={label} {...rest}>
        {glyph}
      </a>
    );
  }
  return (
    <button type="button" className={classes} aria-label={label} title={label} {...rest}>
      {glyph}
    </button>
  );
}
