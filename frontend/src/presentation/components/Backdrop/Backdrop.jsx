import Blob from '@/presentation/components/Blob/Blob.jsx';
import Grain from '@/presentation/components/Grain/Grain.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './Backdrop.css';

/**
 * Fundo cinematográfico das telas da área logada: cacau profundo, luzes coral e
 * mel flutuando ([data-blob]), textura de pontos, vinheta e grão.
 * - fixed: fica parado atrás da página enquanto o conteúdo rola (AppShell)
 * - contained: ocupa só o bloco onde está (404, tela de carregando)
 */
export default function Backdrop({ mode = 'fixed', className }) {
  return (
    <div aria-hidden="true" className={cx('backdrop', `backdrop--${mode}`, className)}>
      <span className="backdrop__glow" />
      <Blob tone="coral" className="backdrop__blob backdrop__blob--a" />
      <Blob tone="honey" className="backdrop__blob backdrop__blob--b" />
      <Blob tone="coral" className="backdrop__blob backdrop__blob--c" />
      <span className="backdrop__dots" />
      <span className="backdrop__vignette" />
      <Grain />
    </div>
  );
}
