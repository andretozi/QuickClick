import { createPortal } from 'react-dom';
import Toast from './Toast.jsx';
import useToasts from '@/application/feedback/useToasts.js';
import { TOASTS } from '@/domain/content/commonContent.js';
import './ToastViewport.css';

/**
 * Região dos avisos rápidos, no canto da tela. Fica fora do #root (portal no body)
 * para continuar sendo lida pelo leitor de tela mesmo com um diálogo aberto.
 */
export default function ToastViewport() {
  const { toasts, dismiss } = useToasts();

  return createPortal(
    <section className="toasts" aria-label={TOASTS.region}>
      <ol className="toasts__list" aria-live="polite" aria-relevant="additions">
        {toasts.map((toast) => (
          <Toast key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </ol>
    </section>,
    document.body
  );
}
