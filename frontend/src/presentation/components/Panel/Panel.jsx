import { cx } from '@/presentation/utils/cx.js';
import './Panel.css';

/**
 * Painel em camadas da área logada (nunca um card chapado).
 * - tone 'paper': areia clara com degradê de 160°, borda iluminada e sombra quente
 *   (formulários, listas, logos: tudo que precisa de fundo claro)
 * - tone 'glass': vidro escuro fosco sobre o fundo cinematográfico (números e gráficos)
 * Props extras (data-enter, aria-labelledby...) vão para o elemento.
 */
export default function Panel({ as: Tag = 'section', tone = 'paper', className, children, ...rest }) {
  return (
    <Tag className={cx('panel', `panel--${tone}`, className)} {...rest}>
      {children}
    </Tag>
  );
}
