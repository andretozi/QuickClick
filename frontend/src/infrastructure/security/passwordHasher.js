/**
 * Infraestrutura · Senha (SIMULAÇÃO)
 *
 * Guarda só o hash SHA-256 da senha com um sal aleatório, usando crypto.subtle.
 * Isto NÃO é segurança de verdade: os dados ficam no navegador do próprio usuário,
 * e SHA-256 é rápido demais para guardar senhas num servidor.
 *
 * Quando o back existir, a senha vai por HTTPS para a API, que guarda o hash com um
 * algoritmo lento feito para senhas (Argon2, scrypt ou bcrypt), e este arquivo deixa
 * de existir. crypto.subtle só funciona em contexto seguro: 127.0.0.1, localhost ou HTTPS.
 */

const ALGORITHM = 'SHA-256';

const toHex = (buffer) => Array.from(new Uint8Array(buffer), (byte) => byte.toString(16).padStart(2, '0')).join('');

function randomSalt() {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return toHex(bytes);
}

async function digest(text) {
  if (!globalThis.crypto?.subtle) {
    throw new Error('contexto_inseguro');
  }
  const data = new TextEncoder().encode(text);
  return toHex(await crypto.subtle.digest(ALGORITHM, data));
}

/** Gera o registro guardado: { algoritmo, sal, hash }. */
export async function hashPassword(password, salt = randomSalt()) {
  return { algoritmo: ALGORITHM, sal: salt, hash: await digest(`${salt}:${password}`) };
}

/** Confere uma senha com o registro guardado. */
export async function verifyPassword(password, stored) {
  if (!stored?.sal || !stored?.hash) return false;
  const { hash } = await hashPassword(password, stored.sal);
  return hash === stored.hash;
}
