/**
 * Aplicação · O que o login e o cadastro dividem: o código do erro do formulário
 * inteiro e o aviso de "em breve" dos Termos e da Política de Privacidade.
 */
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import { LOGIN_SOON } from '@/domain/content/loginContent.js';

/** Código do erro do formulário inteiro a partir do código devolvido pela API ou storage. */
export function formErrorFor(code) {
  if (code === 'armazenamento_cheio') return 'storage';
  if (code === 'muitas_tentativas') return 'rateLimit';
  if (code === 'email_em_uso') return 'emailTaken';
  if (code === 'token_invalido') return 'google';
  return 'unknown';
}

/** Termos e privacidade ainda não têm página: um aviso elegante. */
export function announceTermsSoon() {
  showToast({ tone: TOAST_TONES.INFO, ...LOGIN_SOON.terms });
}
