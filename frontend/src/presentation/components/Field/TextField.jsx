import Field, { describedBy } from './Field.jsx';
import { cx } from '@/presentation/utils/cx.js';

/**
 * Campo de texto simples (email, nome...). Props extras vão para o <input>.
 * - leading: algo antes do texto (um ícone de busca, "R$")
 * - hint / error: mensagens embaixo do campo, ligadas pelo aria-describedby
 */
export default function TextField({
  id,
  label,
  aside,
  hint,
  error,
  leading,
  className,
  inputClassName,
  type = 'text',
  ...inputProps
}) {
  const input = (
    <input
      id={id}
      type={type}
      className={cx('field__input', leading && 'field__input--with-leading', inputClassName)}
      aria-invalid={error ? true : undefined}
      aria-describedby={describedBy(id, { hint, error })}
      {...inputProps}
    />
  );

  return (
    <Field id={id} label={label} aside={aside} hint={hint} error={error} className={className}>
      {leading ? (
        <div className="field__control">
          <span className="field__leading" aria-hidden="true">
            {leading}
          </span>
          {input}
        </div>
      ) : (
        input
      )}
    </Field>
  );
}
