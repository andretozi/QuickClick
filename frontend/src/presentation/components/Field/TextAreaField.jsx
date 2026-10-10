import Field, { describedBy } from './Field.jsx';
import { cx } from '@/presentation/utils/cx.js';

/** Texto longo (descrição do anúncio). Props extras vão para o <textarea>. */
export default function TextAreaField({ id, label, aside, hint, error, className, rows = 5, ...textareaProps }) {
  return (
    <Field id={id} label={label} aside={aside} hint={hint} error={error} className={className}>
      <textarea
        id={id}
        rows={rows}
        className={cx('field__input', 'field__textarea')}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, { hint, error })}
        {...textareaProps}
      />
    </Field>
  );
}
