/**
 * Infraestrutura · Serviço do Painel Administrativo e Moderação
 *
 * Comunicação com as rotas /api/admin para supervisão, aplicação de sanções,
 * encerramento forçado de sessões e expurgo de contas.
 */
import { ApiError, requestJson } from '../http/httpClient.js';

export class AdminServiceError extends Error {
  constructor({ status, code, userMessage = '' }) {
    super(userMessage || `Erro de administração (${code || status})`);
    this.name = 'AdminServiceError';
    this.status = status;
    this.code = code;
    this.userMessage = userMessage;
  }
}

function wrapError(error) {
  if (error instanceof ApiError) {
    return new AdminServiceError({
      status: error.status,
      code: error.code,
      userMessage: error.userMessage || 'Não foi possível completar a operação administrativa.'
    });
  }
  return new AdminServiceError({
    status: 0,
    code: 'sem_conexao',
    userMessage: 'Sem conexão com o servidor de moderação.'
  });
}

export async function fetchAdminOverview({ status = 'todos', search = '' } = {}) {
  try {
    const params = new URLSearchParams();
    if (status && status !== 'todos') params.set('status', status);
    if (search && search.trim()) params.set('busca', search.trim());
    const query = params.toString();
    const path = `/admin/overview${query ? `?${query}` : ''}`;
    return await requestJson(path);
  } catch (error) {
    throw wrapError(error);
  }
}

export async function fetchAdminAudit({ limit = 50 } = {}) {
  try {
    const path = `/admin/audit?limite=${encodeURIComponent(limit)}`;
    return await requestJson(path);
  } catch (error) {
    throw wrapError(error);
  }
}

export async function applyAccountPunishment(userId, { type, reason, suspensionDays = 7 }) {
  try {
    return await requestJson(`/admin/users/${encodeURIComponent(userId)}/punishment`, {
      method: 'POST',
      body: {
        tipo: type,
        motivo: reason,
        dias_suspensao: suspensionDays
      }
    });
  } catch (error) {
    throw wrapError(error);
  }
}

export async function killAccountSessions(userId) {
  try {
    return await requestJson(`/admin/users/${encodeURIComponent(userId)}/kill-sessions`, {
      method: 'POST'
    });
  } catch (error) {
    throw wrapError(error);
  }
}

export async function disconnectAccountMarketplace(userId, slug) {
  try {
    return await requestJson(`/admin/users/${encodeURIComponent(userId)}/marketplaces/${encodeURIComponent(slug)}`, {
      method: 'DELETE'
    });
  } catch (error) {
    throw wrapError(error);
  }
}

export async function deleteAccountAdmin(userId, { emailConfirmation, reason }) {
  try {
    return await requestJson(`/admin/users/${encodeURIComponent(userId)}`, {
      method: 'DELETE',
      body: {
        confirmacao_email: emailConfirmation,
        motivo: reason
      }
    });
  } catch (error) {
    throw wrapError(error);
  }
}
