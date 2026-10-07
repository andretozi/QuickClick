import { cx } from '@/presentation/utils/cx.js';
import './SceneCard.css';

/** Cartão escuro onde as ilustrações do "Como funciona" acontecem. tone: 'default' | 'warm' */
export default function SceneCard({ tone = 'default', className, children, ...rest }) {
  return (
    <div className={cx('scene-card', `scene-card--${tone}`, className)} {...rest}>
      {children}
    </div>
  );
}
