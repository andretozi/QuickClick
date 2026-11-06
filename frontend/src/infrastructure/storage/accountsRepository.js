/**
 * Domínio · Entidades e mapeamento de contas autenticadas (localStorage)
 *
 * Sincroniza no navegador os dados retornados pela API (/api/auth/me, /api/me/plano)
 * junto com preferências visuais locais da conta (telefone e cor do avatar), sem
 * armazenar senhas nem simular autenticação local.
 */
import { STORAGE_KEYS, clearUser, nowIso, readJson, writeJson } from './localStore.js';

/** Códigos de erro estáveis alinhados aos códigos devolvidos pela API. */
export const ACCOUNT_ERRORS = {
  EMAIL_TAKEN: 'email_em_uso',
  INVALID_CREDENTIALS: 'credenciais_invalidas',
  ACCOUNT_SUSPENDED: 'conta_suspensa',
  ACCOUNT_BANNED: 'conta_banida',
  WRONG_PASSWORD: 'senha_atual_incorreta',
  CONFIRMATION_MISMATCH: 'confirmacao_incorreta',
  NOT_FOUND: 'conta_nao_encontrada'
};

export class AccountError extends Error {
  constructor(code, extras = {}) {
    super(code);
    this.name = 'AccountError';
    this.code = code;
    this.extras = extras;
  }
}

const normalizeEmail = (email) => String(email ?? '').trim().toLowerCase();

/** JSON guardado (português) → conta do front. */
const toAccount = (conta) =>
  conta
    ? {
        id: conta.id,
        name: conta.nome,
        email: conta.email,
        phone: conta.telefone ?? '',
        store: conta.loja,
        plan: conta.plano,
        role: conta.papel ?? 'vendedor',
        status: conta.status_conta ?? 'ativa',
        warning: conta.advertencia ?? null,
        hasPassword: conta.tem_senha !== undefined ? Boolean(conta.tem_senha) : true,
        avatarColor: conta.cor_avatar ?? 'coral',
        createdAt: conta.criada_em,
        updatedAt: conta.atualizada_em
      }
    : null;

const load = () => readJson(STORAGE_KEYS.ACCOUNTS, []);
const save = (contas) => writeJson(STORAGE_KEYS.ACCOUNTS, contas);

export async function getAccount(id) {
  return toAccount(load().find((conta) => conta.id === id));
}

/** Remove os dados locais da conta neste navegador após exclusão confirmada na API. */
export function purgeLocalAccount(id) {
  save(load().filter((item) => item.id !== id));
  clearUser(id);
}

/**
 * Ponto único de conversão e persistência local da conta autenticada na API.
 * Aceita tanto os campos em português da API (nome, loja, plano, papel, status_conta, tem_senha)
 * quanto campos já normalizados do front (name, store, plan, role, status, hasPassword, phone, avatarColor).
 */
export function upsertAccount(contaData) {
  const contas = load();
  const id = contaData.id;
  const normalizedEmail = normalizeEmail(contaData.email);
  const index = contas.findIndex((c) => c.id === id || c.email === normalizedEmail);
  const now = nowIso();
  const existing = index >= 0 ? contas[index] : null;
  const loja = String(contaData.store ?? contaData.loja ?? existing?.loja ?? '').trim();
  const rawName = String(contaData.name ?? contaData.nome ?? existing?.nome ?? '').trim();
  const nome = rawName || loja || normalizedEmail;
  const temSenha = contaData.hasPassword ?? contaData.tem_senha ?? existing?.tem_senha ?? true;
  const papel = contaData.role ?? contaData.papel ?? existing?.papel ?? 'vendedor';
  const statusConta = contaData.status ?? contaData.status_conta ?? existing?.status_conta ?? 'ativa';
  const advertencia = contaData.warning ?? contaData.advertencia ?? existing?.advertencia ?? null;

  const conta = {
    id,
    nome,
    email: normalizedEmail,
    telefone: String(contaData.phone ?? contaData.telefone ?? existing?.telefone ?? '').trim(),
    loja,
    plano: contaData.plan ?? contaData.plano ?? existing?.plano ?? 'gratis',
    papel,
    status_conta: statusConta,
    advertencia,
    tem_senha: Boolean(temSenha),
    cor_avatar: contaData.avatarColor ?? contaData.cor_avatar ?? existing?.cor_avatar ?? 'coral',
    criada_em: existing?.criada_em ?? now,
    atualizada_em: now
  };

  if (index >= 0) {
    const next = [...contas];
    next[index] = conta;
    save(next);
  } else {
    save([...contas, conta]);
  }
  return toAccount(conta);
}
