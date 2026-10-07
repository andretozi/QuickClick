import { cx } from '@/presentation/utils/cx.js';
import './Section.css';

/**
 * Casca padrão de toda seção: fundo, textura de pontos, decoração e
 * o container central (`section__inner`).
 *
 * - tone: 'light' | 'dark'
 * - dotted: aplica a textura de pontos
 * - backdrop: elementos decorativos atrás do conteúdo (ex.: <Blob />)
 */
export default function Section({
  as: Tag = 'section',
  id,
  tone = 'light',
  dotted = false,
  backdrop,
  className,
  innerClassName,
  children
}) {
  return (
    <Tag
      id={id}
      className={cx('section', `section--${tone}`, dotted && 'section--dotted', className)}
    >
      {backdrop}
      <div className={cx('section__inner', innerClassName)}>{children}</div>
    </Tag>
  );
}
