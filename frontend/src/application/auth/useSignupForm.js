import { useCallback, useEffect, useRef, useState } from 'react';
import useForm from '@/application/ui/useForm.js';
import { signUp } from '@/application/session/sessionStore.js';
import { ACCOUNT_ERRORS, describeAuthError } from '@/infrastructure/auth/authService.js';
import {
  validateEmail,
  validateName,
  validateNewPassword,
  validatePasswordConfirmation
} from '@/domain/validation/validators.js';

const EMPTY = { name: '', email: '', store: '', password: '', confirmation: '' };

const validateSignup = (values) => ({
  name: validateName(values.name),
  email: validateEmail(values.email),
  store: validateName(values.store),
  password: validateNewPassword(values.password),
  confirmation: validatePasswordConfirmation(values.password, values.confirmation)
});

/**
 * Aplicação · Caso de uso "criar conta".
 * Valida cada campo (a mensagem aparece embaixo dele), cria a conta no repositório
 * e já abre a sessão. A guarda de rotas leva para o painel, que mostra as boas vindas.
 */
export default function useSignupForm() {
  const form = useForm(EMPTY, validateSignup);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const { check, values, setFieldError } = form;

  const handleSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      if (loading || !check()) return;
      setFormError(null);
      setLoading(true);
      try {
        await signUp({ name: values.name, email: values.email, store: values.store, password: values.password });
      } catch (error) {
        if (!mounted.current) return;
        setLoading(false);
        const code = describeAuthError(error);
        if (code === ACCOUNT_ERRORS.EMAIL_TAKEN) setFieldError('email', 'email-taken');
        else setFormError(code === 'armazenamento_cheio' ? 'storage' : 'unknown');
      }
    },
    [check, loading, setFieldError, values]
  );

  return {
    values: form.values,
    errors: form.errors,
    formRef: form.formRef,
    handleChange: form.handleChange,
    handleSubmit,
    loading,
    formError
  };
}
