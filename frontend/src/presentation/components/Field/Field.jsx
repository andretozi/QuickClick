import { cx } from '@/presentation/utils/cx.js';
import './Field.css';

/** ids das mensagens embaixo do campo, para o aria-describedby do controle. */
export function describedBy(id, { hint, error }) {
  return [hint && `${id}-dica`, error && `${id}-erro`].filter(Boolean).join(' ') || undefined;
}

/**
 * Estrutura comum de um campo de formulário: rótulo (+ conteúdo opcional à direita,
 * como um link), o controle em si (children), a dica e a mensagem de erro.
 * O controle liga as mensagens pelo aria-describedby (veja describedBy).
 */
export default function Field({ id, label, aside, hint, error, className, children }) {
  return (
    <div className={cx('field', error && 'field--invalid', className)}>
      <div className="field__header">
        <label htmlFor={id} className="field__label">
          {label}
        </label>
        {aside}
      </div>
      {children}
      {hint && (
        <p id={`${id}-dica`} className="field__hint">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-erro`} className="field__error">
          {error}
        </p>
      )}
    </div>
  );
}
