import { useCallback, useEffect, useRef, useState } from 'react';
import { signIn } from '@/infrastructure/auth/authService.js';

const EMPTY_CREDENTIALS = { email: '', password: '' };

/**
 * Aplicação · Caso de uso "entrar na conta".
 * Guarda o que foi digitado, controla o estado de carregamento e chama o serviço
 * de autenticação. A tela (LoginForm) só desenha o que este hook devolve.
 */
export default function useLoginForm() {
  const [credentials, setCredentials] = useState(EMPTY_CREDENTIALS);
  const [loading, setLoading] = useState(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  /** onChange genérico: usa o atributo name do input ("email" ou "password"). */
  const handleChange = useCallback((event) => {
    const { name, value } = event.target;
    setCredentials((current) => ({ ...current, [name]: value }));
  }, []);

  const handleSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      if (loading) return;
      setLoading(true);
      try {
        await signIn(credentials);
      } finally {
        if (mounted.current) setLoading(false);
      }
    },
    [credentials, loading]
  );

  return { credentials, loading, handleChange, handleSubmit };
}
