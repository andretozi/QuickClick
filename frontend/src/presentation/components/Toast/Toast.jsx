import { useRef } from 'react';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import { useToastAnimation } from '@/application/animation/useOverlayAnimation.js';
import { cx } from '@/presentation/utils/cx.js';
import { TOASTS } from '@/domain/content/commonContent.js';
import './Toast.css';

const ICON_BY_TONE = { success: 'check', info: 'info', error: 'alert' };

/** Um aviso rápido: ícone do tom, título, texto e o botão de fechar. Entra e sai com mola. */
export default function Toast({ toast, onDismiss }) {
  const ref = useRef(null);
  useToastAnimation(ref, toast.leaving);

  return (
    <li ref={ref} className={cx('toast', `toast--${toast.tone}`)}>
      <span data-part="icon" className="toast__icon" aria-hidden="true">
        <Icon name={ICON_BY_TONE[toast.tone] ?? 'info'} size={18} />
      </span>
      <div className="toast__body">
        <p className="toast__title">{toast.title}</p>
        {toast.text && <p className="toast__text">{toast.text}</p>}
      </div>
      <button type="button" className="toast__close" aria-label={TOASTS.close} onClick={() => onDismiss(toast.id)}>
        <Icon name="x" size={16} />
      </button>
    </li>
  );
}
