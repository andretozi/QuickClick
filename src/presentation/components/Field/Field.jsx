import './Field.css';

/**
 * Estrutura comum de um campo de formulário: rótulo (+ conteúdo opcional
 * à direita, como um link) e o controle em si (children).
 */
export default function Field({ id, label, aside, children }) {
  return (
    <div className="field">
      <div className="field__header">
        <label htmlFor={id} className="field__label">
          {label}
        </label>
        {aside}
      </div>
      {children}
    </div>
  );
}
