/**
 * Aplicação · O que o login e o cadastro dividem: o código do erro do formulário
 * inteiro e o aviso de "em breve" dos Termos e da Política de Privacidade.
 */
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';
import { LOGIN_SOON } from '@/domain/content/loginContent.js';

/** Código do erro do formulário inteiro: navegador sem espaço ("storage") ou qualquer outro ("unknown"). */
export function formErrorFor(code) {
  return code === 'armazenamento_cheio' ? 'storage' : 'unknown';
}

/** Termos e privacidade ainda não têm página: um aviso elegante. */
export function announceTermsSoon() {
  showToast({ tone: TOAST_TONES.INFO, ...LOGIN_SOON.terms });
}
