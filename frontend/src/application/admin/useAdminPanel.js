/**
 * Aplicação · Hook do Painel de Moderação Administrativa
 *
 * Gerencia a busca consolidada de contas, filtros por situação,
 * despacho de sanções (advertência, suspensão, banimento, reativação),
 * queda de sessões forçada, desvinculação de marketplaces e exclusão permanente.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  applyAccountPunishment,
  deleteAccountAdmin,
  disconnectAccountMarketplace,
  fetchAdminAudit,
  fetchAdminOverview,
  killAccountSessions
} from '@/infrastructure/admin/adminService.js';
import { showToast, TOAST_TONES } from '@/application/feedback/toastStore.js';

export const ADMIN_TABS = {
  USERS: 'users',
  AUDIT: 'audit'
};

export default function useAdminPanel() {
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState(ADMIN_TABS.USERS);
  const [statusFilter, setStatusFilter] = useState('todos');
  const [searchTerm, setSearchTerm] = useState('');
  const [overview, setOverview] = useState({
    resumo: {
      total_contas: 0,
      sessoes_ativas: 0,
      contas_advertidas: 0,
      contas_suspensas: 0,
      contas_banidas: 0,
      conexoes_ativas: 0
    },
    contas: [],
    total_filtrado: 0
  });
  const [auditLog, setAuditLog] = useState([]);
  const [loadingAudit, setLoadingAudit] = useState(false);
  const [activeModal, setActiveModal] = useState(null);
  const [executing, setExecuting] = useState(false);

  const searchTimerRef = useRef(null);

  const loadOverview = useCallback(async (status, search) => {
    try {
      setLoading(true);
      const data = await fetchAdminOverview({ status, search });
      setOverview(data);
    } catch (error) {
      showToast({
        tone: TOAST_TONES.ERROR,
        title: 'Não foi possível carregar o painel',
        text: error.message || 'Verifique sua conexão ou permissões.'
      });
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAudit = useCallback(async () => {
    try {
      setLoadingAudit(true);
      const records = await fetchAdminAudit({ limit: 50 });
      setAuditLog(records);
    } catch (error) {
      showToast({
        tone: TOAST_TONES.ERROR,
        title: 'Falha ao buscar auditoria',
        text: error.message || 'Tente novamente mais tarde.'
      });
    } finally {
      setLoadingAudit(false);
    }
  }, []);

  // Recarrega overview quando muda filtro ou busca (com debounce na busca)
  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);

    searchTimerRef.current = setTimeout(() => {
      loadOverview(statusFilter, searchTerm);
    }, 250);

    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    };
  }, [statusFilter, searchTerm, loadOverview]);

  // Carrega log de auditoria ao abrir a aba correspondente
  useEffect(() => {
    if (tab === ADMIN_TABS.AUDIT) {
      loadAudit();
    }
  }, [tab, loadAudit]);

  const openModal = useCallback((type, account, channel = null) => {
    setActiveModal({ type, account, channel });
  }, []);

  const closeModal = useCallback(() => {
    if (executing) return;
    setActiveModal(null);
  }, [executing]);

  const executeAction = useCallback(async ({ reason = '', suspensionDays = 7, emailConfirmation = '' }) => {
    if (!activeModal) return;
    const { type, account, channel } = activeModal;
    setExecuting(true);

    try {
      if (['advertir', 'suspender', 'banir', 'reativar'].includes(type)) {
        const response = await applyAccountPunishment(account.id, {
          type,
          reason,
          suspensionDays: Number(suspensionDays) || 7
        });
        showToast({
          tone: TOAST_TONES.SUCCESS,
          title: 'Ação executada',
          text: response.mensagem || 'Situação da conta atualizada com sucesso.'
        });
      } else if (type === 'killSessions') {
        const response = await killAccountSessions(account.id);
        showToast({
          tone: TOAST_TONES.SUCCESS,
          title: 'Sessões encerradas',
          text: response.mensagem || 'Tokens invalidados.'
        });
      } else if (type === 'disconnect') {
        const response = await disconnectAccountMarketplace(account.id, channel.slug);
        showToast({
          tone: TOAST_TONES.SUCCESS,
          title: 'Marketplace desvinculado',
          text: response.mensagem || 'Canal removido da conta com sucesso.'
        });
      } else if (type === 'delete') {
        const response = await deleteAccountAdmin(account.id, {
          emailConfirmation,
          reason
        });
        showToast({
          tone: TOAST_TONES.SUCCESS,
          title: 'Conta excluída em definitivo',
          text: response.mensagem || 'Dados expurgados da plataforma.'
        });
      }

      setActiveModal(null);
      await loadOverview(statusFilter, searchTerm);
      if (tab === ADMIN_TABS.AUDIT) {
        await loadAudit();
      }
    } catch (error) {
      showToast({
        tone: TOAST_TONES.ERROR,
        title: 'Ação não permitida',
        text: error.message || 'Ocorreu um erro ao processar a moderação.'
      });
    } finally {
      setExecuting(false);
    }
  }, [activeModal, statusFilter, searchTerm, tab, loadOverview, loadAudit]);

  return {
    loading,
    tab,
    setTab,
    statusFilter,
    setStatusFilter,
    searchTerm,
    setSearchTerm,
    overview,
    auditLog,
    loadingAudit,
    activeModal,
    openModal,
    closeModal,
    executeAction,
    executing,
    refresh: () => loadOverview(statusFilter, searchTerm)
  };
}
