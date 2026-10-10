import { cx } from '@/presentation/utils/cx.js';
import './MarketplaceMark.css';

/**
 * Monograma de um marketplace: as iniciais numa cor que lembra a marca dele.
 * É a reserva do MarketplaceLogo, para quando o logo oficial não existe (TikTok Shop).
 * size: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
 */
export default function MarketplaceMark({ slug, monogram, size = 'md', className }) {
  return (
    <span
      aria-hidden="true"
      className={cx('marketplace-mark', `marketplace-mark--${size}`, `marketplace-mark--${slug}`, className)}
    >
      {monogram}
    </span>
  );
}
