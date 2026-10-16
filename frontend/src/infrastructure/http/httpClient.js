/**
 * Infraestrutura · Cliente HTTP da API
 *
 * O único lugar do front que chama fetch. Todas as rotas começam com /api: no main.py
 * a API e o site estão no mesmo endereço, e no "npm run dev" o Vite repassa /api
 * para 127.0.0.1:8080.
 *
 * Anexa automaticamente o token JWT no cabeçalho Authorization: Bearer <token>
 * para garantir a segurança e autenticação das requisições.
 */
import { getStoredToken } from '../storage/sessionRepository.js';

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
 * @param {{ method?: string, body?: any, headers?: Record<string, string> }} options
 */
export async function requestJson(path, { method = 'GET', body, headers = {} } = {}) {
  let response;

  const requestHeaders = {
    Accept: 'application/json',
    ...headers
  };

  const token = getStoredToken();
  if (token && !requestHeaders.Authorization) {
    requestHeaders.Authorization = `Bearer ${token}`;
  }

  const fetchOptions = {
    method,
    headers: requestHeaders
  };

  if (body !== undefined) {
    if (typeof body === 'object' && body !== null && !(body instanceof FormData)) {
      if (!requestHeaders['Content-Type']) {
        requestHeaders['Content-Type'] = 'application/json';
      }
      fetchOptions.body = JSON.stringify(body);
    } else {
      fetchOptions.body = body;
    }
  }

  try {
    response = await fetch(`${API_BASE}${path}`, fetchOptions);
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
