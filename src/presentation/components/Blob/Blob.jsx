import { cx } from '@/presentation/utils/cx.js';
import './Blob.css';

/**
 * Mancha de luz decorativa do fundo (animada pelo JS via [data-blob]).
 * A posição e o tamanho ficam no CSS da seção que a usa (mix BEM), ex.:
 *   <Blob tone="honey" className="hero__blob hero__blob--b" />
 */
export default function Blob({ tone = 'coral', className }) {
  return <div data-blob aria-hidden="true" className={cx('blob', `blob--${tone}`, className)} />;
}
