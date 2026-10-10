/**
 * Aplicação · Avisos rápidos (toasts)
 *
 * Qualquer caso de uso chama showToast({ tone, title, text }). A lista é uma store
 * pequena lida com useSyncExternalStore pelo ToastViewport. Cada aviso some sozinho;
 * antes de sair, ele fica marcado como "leaving" para a animação de saída tocar.
 */

export const TOAST_TONES = { SUCCESS: 'success', INFO: 'info', ERROR: 'error' };

const DEFAULT_DURATION_MS = 4200;
const LEAVE_MS = 280;
const MAX_VISIBLE = 3;

let toasts = [];
let nextId = 1;
const listeners = new Set();
const timers = new Map();

function emit() {
  listeners.forEach((listener) => listener());
}

export function dismissToast(id) {
  clearTimeout(timers.get(id));
  timers.delete(id);
  if (!toasts.some((toast) => toast.id === id && !toast.leaving)) return;
  toasts = toasts.map((toast) => (toast.id === id ? { ...toast, leaving: true } : toast));
  emit();
  setTimeout(() => {
    toasts = toasts.filter((toast) => toast.id !== id);
    emit();
  }, LEAVE_MS);
}

/** Mostra um aviso. Devolve o id (para fechar antes da hora, se precisar). */
export function showToast({ tone = TOAST_TONES.SUCCESS, title, text = '', duration = DEFAULT_DURATION_MS }) {
  const id = nextId;
  nextId += 1;
  toasts = [...toasts, { id, tone, title, text, leaving: false }];
  emit();

  const visible = toasts.filter((toast) => !toast.leaving);
  if (visible.length > MAX_VISIBLE) dismissToast(visible[0].id);
  if (duration) timers.set(id, setTimeout(() => dismissToast(id), duration));
  return id;
}

export function subscribeToToasts(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getToastsSnapshot() {
  return toasts;
}

export const TOAST_LEAVE_MS = LEAVE_MS;
