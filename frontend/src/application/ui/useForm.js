import { useCallback, useEffect, useRef, useState } from 'react';
import { focusFirstInvalid } from '@/infrastructure/browser/focus.js';
import { isValid } from '@/domain/validation/validators.js';

/**
 * Aplicação · Estado de um formulário
 *
 * - values: o que foi digitado (inputs controlados pelo atributo name)
 * - errors: código de erro por campo (o texto fica no domain/content). Os erros só
 *   aparecem depois da primeira tentativa de enviar; daí em diante, somem enquanto
 *   o vendedor corrige.
 * - check(): valida tudo antes de enviar e leva o foco ao primeiro campo com erro.
 *
 * `validate(values)` precisa ser uma função estável (declarada fora do componente).
 */
export default function useForm(initialValues, validate) {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const formRef = useRef(null);

  useEffect(() => {
    if (attempt > 0) focusFirstInvalid(formRef.current);
  }, [attempt]);

  useEffect(() => {
    if (submitted) setErrors(validate(values));
  }, [values, submitted, validate]);

  const setField = useCallback((name, value) => {
    setValues((current) => ({ ...current, [name]: value }));
  }, []);

  const handleChange = useCallback(
    (event) => {
      const { name, value, type, checked } = event.target;
      setField(name, type === 'checkbox' ? checked : value);
    },
    [setField]
  );

  /** Valida tudo. Devolve true quando dá para enviar. */
  const check = useCallback(() => {
    const found = validate(values);
    setErrors(found);
    setSubmitted(true);
    if (isValid(found)) return true;
    setAttempt((current) => current + 1);
    return false;
  }, [validate, values]);

  /** Erro que só o "servidor" sabe (ex.: email já cadastrado). */
  const setFieldError = useCallback((name, code) => {
    setErrors((current) => ({ ...current, [name]: code }));
    setAttempt((current) => current + 1);
  }, []);

  const reset = useCallback((nextValues) => {
    setValues(nextValues);
    setErrors({});
    setSubmitted(false);
  }, []);

  return { values, errors, formRef, handleChange, setField, setValues, check, setFieldError, reset };
}
