import Field, { describedBy } from './Field.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';

/**
 * Lista de opções (o <select> do navegador, com a cara da Quick Click).
 * Usa o controle nativo de propósito: teclado, leitor de tela e celular funcionam sem esforço.
 * options: [{ value, label }]
 */
export default function SelectField({
  id,
  label,
  aside,
  hint,
  error,
  options,
  placeholder,
  className,
  compact = false,
  ...selectProps
}) {
  return (
    <Field id={id} label={label} aside={aside} hint={hint} error={error} className={className}>
      <div className="field__control">
        <select
          id={id}
          className={cx('field__input', 'field__select', compact && 'field__input--compact')}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(id, { hint, error })}
          {...selectProps}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <Icon name="chevron-down" size={18} className="field__chevron" />
      </div>
    </Field>
  );
}
