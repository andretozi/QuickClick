import { cx } from '@/presentation/utils/cx.js';
import './Grain.css';

/** Granulação sutil de filme por cima do fundo. Só decoração: o leitor de tela ignora. */
export default function Grain({ className }) {
  return <span aria-hidden="true" className={cx('grain', className)} />;
}
