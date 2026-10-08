/**
 * Infraestrutura · Cliente HTTP da API
 *
 * O único lugar do front que chama fetch. Todas as rotas começam com /api: no main.py
 * a API e o site estão no mesmo endereço, e no "npm run dev" o Vite repassa /api
 * para 127.0.0.1:8080.
 */
const API_BASE = '/api';

/** Falha numa chamada à API. `code` vem do back (ex.: "limite_do_plano") ou é "sem_conexao". */
export class ApiError extends Error {
  constructor({ status, code, userMessage = '' }) {
    super(`${status} ${code}`);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.userMessage = userMessage; // texto do back, já pronto para a tela (pode vir vazio)
  }
}

/**
 * Chama a API e devolve o JSON da resposta.
 * @param {string} path  ex.: "/marketplaces"
 * @param {{ method?: string }} options
 */
export async function requestJson(path, { method = 'GET' } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { method, headers: { Accept: 'application/json' } });
  } catch {
    throw new ApiError({ status: 0, code: 'sem_conexao' });
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const erro = data?.erro;
    throw new ApiError({
      status: response.status,
      // Sem o formato da API (ex.: o back fora do ar no "npm run dev") é falta de conexão
      code: erro?.codigo ?? (response.status >= 500 ? 'sem_conexao' : 'erro_desconhecido'),
      userMessage: erro?.mensagem ?? ''
    });
  }
  return data;
}
