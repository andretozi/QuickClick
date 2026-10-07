import LogoMark from './LogoMark.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './Brand.css';

/**
 * Marca completa: ícone + "Quick Click" (+ frase opcional).
 * - size: 'lg' (nav) | 'md' (login) | 'sm' (rodapé)
 * - tone: 'light' (fundo claro) | 'dark' (fundo escuro)
 * - href: quando informado, a marca vira link
 */
export default function Brand({ size = 'lg', tone = 'light', href, tagline, className }) {
  const Tag = href ? 'a' : 'div';

  return (
    <Tag
      href={href}
      className={cx('brand', `brand--${size}`, `brand--${tone}`, className)}
      aria-label={href ? 'Quick Click — início' : undefined}
    >
      <LogoMark size={size} />
      <span className="brand__text">
        <span className="brand__name">
          Quick <span className="brand__accent">Click</span>
        </span>
        {tagline && <span className="brand__tagline">{tagline}</span>}
      </span>
    </Tag>
  );
}
