/**
 * Infraestrutura · Autenticação
 *
 * Ainda não existe back-end: este serviço só simula a ida ao servidor,
 * respondendo depois de um tempo. Quando a API existir, troque apenas
 * o corpo de signIn() — o resto do front não precisa mudar.
 */
const SIMULATED_DELAY_MS = 1600;

/**
 * @param {{ email: string, password: string }} credentials
 * @returns {Promise<void>}
 */
export function signIn(credentials) {
  void credentials; // será enviado para a API quando ela existir
  return new Promise((resolve) => {
    setTimeout(resolve, SIMULATED_DELAY_MS);
  });
}
