import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './Button.css';

/**
 * Botão único do projeto.
 * - Com `href` vira link (<a>), sem `href` vira <button>.
 * - variant: 'primary' | 'dark' | 'outline' | 'light'
 * - size:    'sm' | 'md' | 'lg' | 'block'
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  href,
  icon,
  iconPosition = 'end',
  iconSize = 18,
  loading = false,
  loadingText,
  className,
  children,
  type = 'button',
  ...rest
}) {
  const classes = cx('button', `button--${variant}`, `button--${size}`, className);
  const iconElement = icon ? <Icon name={icon} size={iconSize} className="button__icon" /> : null;

  const content = loading ? (
    <>
      <span className="button__spinner" aria-hidden="true" />
      {loadingText ?? children}
    </>
  ) : (
    <>
      {iconPosition === 'start' && iconElement}
      {children}
      {iconPosition === 'end' && iconElement}
    </>
  );

  if (href) {
    return (
      <a href={href} className={classes} {...rest}>
        {content}
      </a>
    );
  }

  return (
    <button type={type} className={classes} aria-busy={loading || undefined} {...rest}>
      {content}
    </button>
  );
}
