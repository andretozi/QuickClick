/**
 * Domínio · Validação de formulários
 * Cada função devolve null (tudo certo) ou um código de erro. Os textos de cada
 * código ficam em domain/content/commonContent.js (FIELD_ERRORS).
 */

export const FIELD_ERROR = {
  REQUIRED: 'required',
  EMAIL: 'email',
  NAME_SHORT: 'name-short',
  PASSWORD_SHORT: 'password-short',
  PASSWORD_WEAK: 'password-weak',
  PASSWORD_MISMATCH: 'password-mismatch',
  PHONE: 'phone',
  TOO_LONG: 'too-long',
  PRICE: 'price',
  STOCK: 'stock'
};

export const PASSWORD_MIN_LENGTH = 8;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const isBlank = (value) => String(value ?? '').trim() === '';

export function required(value) {
  return isBlank(value) ? FIELD_ERROR.REQUIRED : null;
}

export function validateEmail(value) {
  if (isBlank(value)) return FIELD_ERROR.REQUIRED;
  return EMAIL_PATTERN.test(String(value).trim()) ? null : FIELD_ERROR.EMAIL;
}

export function validateName(value) {
  if (isBlank(value)) return FIELD_ERROR.REQUIRED;
  return String(value).trim().length < 2 ? FIELD_ERROR.NAME_SHORT : null;
}

/** Senha nova: pelo menos 8 caracteres, com letra e número. */
export function validateNewPassword(value) {
  if (isBlank(value)) return FIELD_ERROR.REQUIRED;
  const text = String(value);
  if (text.length < PASSWORD_MIN_LENGTH) return FIELD_ERROR.PASSWORD_SHORT;
  if (!/[a-zA-Z]/.test(text) || !/\d/.test(text)) return FIELD_ERROR.PASSWORD_WEAK;
  return null;
}

export function validatePasswordConfirmation(password, confirmation) {
  if (isBlank(confirmation)) return FIELD_ERROR.REQUIRED;
  return password === confirmation ? null : FIELD_ERROR.PASSWORD_MISMATCH;
}

/** Telefone é opcional; quando vem, precisa ter de 10 a 13 dígitos (DDD e, se quiser, o 55). */
export function validatePhone(value) {
  if (isBlank(value)) return null;
  const digits = String(value).replace(/\D/g, '');
  return digits.length >= 10 && digits.length <= 13 ? null : FIELD_ERROR.PHONE;
}

export function maxLength(value, limit) {
  return String(value ?? '').length > limit ? FIELD_ERROR.TOO_LONG : null;
}

/** true quando nenhum campo tem erro. */
export function isValid(errors) {
  return Object.values(errors).every((error) => !error);
}
