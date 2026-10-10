import { useCallback, useEffect, useRef, useState } from 'react';
import useForm from '@/application/ui/useForm.js';
import { signIn } from '@/application/session/sessionStore.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import { ACCOUNT_ERRORS, describeAuthError } from '@/infrastructure/auth/authService.js';
import { required, validateEmail } from '@/domain/validation/validators.js';
import { LOGIN_SOON } from '@/domain/content/loginContent.js';

const EMPTY_CREDENTIALS = { email: '', password: '' };

const validateLogin = (values) => ({
  email: validateEmail(values.email),
  password: required(values.password)
});

/** Código do erro do formulário inteiro (o texto fica em LOGIN_FORM.errors). */
function formErrorFor(code) {
  return code === 'armazenamento_cheio' ? 'storage' : 'unknown';
}

/**
 * Aplicação · Caso de uso "entrar na conta".
 * Valida email e senha, confere a conta no repositório (simulado no navegador) e
 * abre a sessão. Quem leva o vendedor para o destino (ou para o painel) é a guarda
 * de rotas, assim que a sessão muda. A tela (LoginForm) só desenha o que este hook devolve.
 */
export default function useLoginForm() {
  const form = useForm(EMPTY_CREDENTIALS, validateLogin);
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

  const submit = useCallback(
    async (credentials) => {
      setFormError(null);
      setLoading(true);
      try {
        await signIn(credentials);
      } catch (error) {
        if (!mounted.current) return;
        setLoading(false);
        const code = describeAuthError(error);
        // email ou senha errados: a mensagem fica embaixo da senha (sem contar qual dos dois errou)
        if (code === ACCOUNT_ERRORS.INVALID_CREDENTIALS) setFieldError('password', 'invalid-credentials');
        else setFormError(formErrorFor(code));
      }
    },
    [setFieldError]
  );

  const handleSubmit = useCallback(
    (event) => {
      event.preventDefault();
      if (loading || !check()) return;
      submit(values);
    },
    [check, loading, submit, values]
  );

  /** Google, Apple e Facebook ainda não funcionam: um aviso elegante. */
  const announceSocialSoon = useCallback((provider) => {
    showToast({ tone: TOAST_TONES.INFO, ...LOGIN_SOON.social(provider.name) });
  }, []);

  const announceForgotSoon = useCallback((event) => {
    event.preventDefault();
    showToast({ tone: TOAST_TONES.INFO, ...LOGIN_SOON.forgot });
  }, []);

  return {
    values: form.values,
    errors: form.errors,
    formRef: form.formRef,
    handleChange: form.handleChange,
    handleSubmit,
    loading,
    formError,
    announceSocialSoon,
    announceForgotSoon
  };
}
