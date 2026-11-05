import { useCallback, useState } from 'react';
import useForm from '@/application/ui/useForm.js';
import useMountedRef from '@/application/ui/useMountedRef.js';
import useGoogleClientId from '@/application/auth/useGoogleClientId.js';
import { announceTermsSoon, formErrorFor } from '@/application/auth/authForm.js';
import { completeGoogleSignUp, signIn, signInWithGoogle } from '@/application/session/sessionStore.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import { ACCOUNT_ERRORS, describeAuthError } from '@/infrastructure/auth/authService.js';
import { maxLength, required, validateEmail, validateName } from '@/domain/validation/validators.js';
import { LOGIN_SOON } from '@/domain/content/loginContent.js';

const EMPTY_CREDENTIALS = { email: '', password: '' };
const STORE_MAX_LENGTH = 120;

const validateLogin = (values) => ({
  email: validateEmail(values.email),
  password: required(values.password)
});

const validateStoreName = (value) => validateName(value) ?? maxLength(value, STORE_MAX_LENGTH);

/**
 * Aplicação · Caso de uso "entrar na conta" (email/senha e Google OAuth).
 * Valida credenciais ou o ID Token do Google, conduz o passo de nome da loja quando
 * a conta Google é nova e inicia a sessão JWT. A guarda de rotas redireciona ao Dashboard.
 */
export default function useLoginForm() {
  const form = useForm(EMPTY_CREDENTIALS, validateLogin);
  const googleClientId = useGoogleClientId();
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState(null);
  const [pendingGoogleUser, setPendingGoogleUser] = useState(null);
  const [storeName, setStoreName] = useState('');
  const [storeNameError, setStoreNameError] = useState(null);
  const mounted = useMountedRef();

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
    [setFieldError, mounted]
  );

  const handleSubmit = useCallback(
    (event) => {
      event.preventDefault();
      if (loading || !check()) return;
      submit(values);
    },
    [check, loading, submit, values]
  );

  const handleGoogleSuccess = useCallback(
    async (credentialResponse) => {
      const token = credentialResponse?.credential;
      if (!token) {
        setFormError('google');
        return;
      }
      setFormError(null);
      setLoading(true);
      try {
        const result = await signInWithGoogle(token);
        if (!mounted.current) return;
        if (result.status === 'needs_store_name') {
          setPendingGoogleUser({ email: result.email, googleId: result.googleId });
          setStoreName('');
          setStoreNameError(null);
          setLoading(false);
        }
      } catch (error) {
        if (!mounted.current) return;
        setLoading(false);
        const code = describeAuthError(error);
        setFormError(formErrorFor(code));
      }
    },
    [mounted]
  );

  const handleGoogleError = useCallback(() => {
    setFormError('google');
  }, []);

  const handleStoreNameChange = useCallback(
    (event) => {
      const next = event.target.value;
      setStoreName(next);
      if (storeNameError) {
        setStoreNameError(validateStoreName(next));
      }
    },
    [storeNameError]
  );

  const handleStoreNameSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      if (loading || !pendingGoogleUser) return;
      const validationError = validateStoreName(storeName);
      if (validationError) {
        setStoreNameError(validationError);
        return;
      }
      setStoreNameError(null);
      setFormError(null);
      setLoading(true);
      try {
        await completeGoogleSignUp({
          email: pendingGoogleUser.email,
          googleId: pendingGoogleUser.googleId,
          storeName: storeName.trim()
        });
      } catch (error) {
        if (!mounted.current) return;
        setLoading(false);
        const code = describeAuthError(error);
        setFormError(formErrorFor(code));
      }
    },
    [loading, mounted, pendingGoogleUser, storeName]
  );

  const announceSocialSoon = useCallback((provider) => {
    if (provider.id === 'google') {
      showToast({ tone: TOAST_TONES.INFO, ...LOGIN_SOON.googleUnavailable });
      return;
    }
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
    googleEnabled: Boolean(googleClientId),
    pendingGoogleUser,
    storeName,
    storeNameError,
    handleGoogleSuccess,
    handleGoogleError,
    handleStoreNameChange,
    handleStoreNameSubmit,
    announceSocialSoon,
    announceForgotSoon,
    announceTermsSoon
  };
}
