import { cx } from '@/presentation/utils/cx.js';
import './Eyebrow.css';

/** Texto pequeno em caixa-alta acima dos títulos. tone: 'honey' | 'coral' | 'inherit' */
export default function Eyebrow({ tone = 'honey', className, children, ...rest }) {
  return (
    <p className={cx('eyebrow', `eyebrow--${tone}`, className)} {...rest}>
      {children}
    </p>
  );
}
