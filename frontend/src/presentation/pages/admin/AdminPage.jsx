import { useState } from 'react';
import Avatar from '@/presentation/components/Avatar/Avatar.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import EmptyState from '@/presentation/components/EmptyState/EmptyState.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import Modal from '@/presentation/components/Modal/Modal.jsx';
import PageHeader from '@/presentation/components/PageHeader/PageHeader.jsx';
import Panel from '@/presentation/components/Panel/Panel.jsx';
import SegmentedControl from '@/presentation/components/SegmentedControl/SegmentedControl.jsx';
import StatCard from '@/presentation/components/StatCard/StatCard.jsx';
import StatusPill from '@/presentation/components/StatusPill/StatusPill.jsx';
import useAdminPanel, { ADMIN_TABS } from '@/application/admin/useAdminPanel.js';
import { ADMIN_PAGE } from '@/domain/content/adminContent.js';
import { cx } from '@/presentation/utils/cx.js';
import './AdminPage.css';

function formatDate(isoString) {
  if (!isoString) return 'Nunca';
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return isoString;
  }
}

export default function AdminPage() {
  const admin = useAdminPanel();
  const {
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
    executing
  } = admin;

  // Form states para os modais
  const [modalReason, setModalReason] = useState('');
  const [modalDays, setModalDays] = useState(7);
  const [modalEmailConfirm, setModalEmailConfirm] = useState('');

  const handleOpenModal = (type, account, channel = null) => {
    setModalReason('');
    setModalDays(7);
    setModalEmailConfirm('');
    openModal(type, account, channel);
  };

  const handleConfirmModal = (e) => {
    e.preventDefault();
    executeAction({
      reason: modalReason,
      suspensionDays: modalDays,
      emailConfirmation: modalEmailConfirm
    });
  };

  const { resumo, contas, total_filtrado } = overview;
  const penalizadas = (resumo.contas_advertidas || 0) + (resumo.contas_suspensas || 0) + (resumo.contas_banidas || 0);

  return (
    <div className="admin-page">
      <PageHeader
        eyebrow={ADMIN_PAGE.eyebrow}
        title={ADMIN_PAGE.title}
        lead={ADMIN_PAGE.lead}
        actions={
          <Button
            variant="outline"
            size="sm"
            icon="sync"
            iconPosition="start"
            iconSize={16}
            onClick={admin.refresh}
            disabled={loading}
          >
            Atualizar
          </Button>
        }
      >
        <StatusPill tone="mint" size="sm">
          Acesso Administrativo
        </StatusPill>
        <StatusPill tone="cream" size="sm">
          {total_filtrado} contas monitoradas
        </StatusPill>
      </PageHeader>

      {/* Cards de Métricas Consolidadas */}
      <ul className="admin-page__stats" aria-label={ADMIN_PAGE.stats.label}>
        <StatCard
          icon="user"
          tone="cream"
          label={ADMIN_PAGE.stats.totalUsers}
          value={resumo.total_contas || 0}
        />
        <StatCard
          icon="clock"
          tone="mint"
          label={ADMIN_PAGE.stats.activeSessions}
          value={resumo.sessoes_ativas || 0}
        />
        <StatCard
          icon="alert"
          tone={penalizadas > 0 ? 'coral' : 'honey'}
          label={ADMIN_PAGE.stats.penalized}
          value={penalizadas}
        />
        <StatCard
          icon="link"
          tone="honey"
          label={ADMIN_PAGE.stats.connections}
          value={resumo.conexoes_ativas || 0}
        />
      </ul>

      {/* Navegação entre Contas e Auditoria */}
      <div className="admin-page__tabs-bar">
        <SegmentedControl
          value={tab}
          onChange={setTab}
          options={[
            { id: ADMIN_TABS.USERS, label: 'Contas e Vendedores' },
            { id: ADMIN_TABS.AUDIT, label: 'Trilha de Auditoria' }
          ]}
        />
      </div>

      {tab === ADMIN_TABS.USERS && (
        <Panel tone="paper" className="admin-page__main-panel">
          {/* Barra de Filtros e Busca */}
          <div className="admin-page__toolbar">
            <div className="admin-page__filters">
              {ADMIN_PAGE.filters.options.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  className={cx(
                    'admin-page__filter-pill',
                    statusFilter === opt.id && 'admin-page__filter-pill--active'
                  )}
                  onClick={() => setStatusFilter(opt.id)}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            <div className="admin-page__search-box">
              <Icon name="search" size={16} className="admin-page__search-icon" />
              <input
                type="search"
                className="admin-page__search-input"
                placeholder={ADMIN_PAGE.filters.searchPlaceholder}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                aria-label={ADMIN_PAGE.filters.searchPlaceholder}
              />
            </div>
          </div>

          {/* Tabela de Contas */}
          {contas.length === 0 && !loading ? (
            <EmptyState
              icon="search"
              title={ADMIN_PAGE.table.emptyTitle}
              description={ADMIN_PAGE.table.emptyLead}
            />
          ) : (
            <div className="admin-page__table-wrapper">
              <table className="admin-page__table">
                <thead>
                  <tr>
                    <th>{ADMIN_PAGE.table.columns.account}</th>
                    <th>{ADMIN_PAGE.table.columns.plan}</th>
                    <th>{ADMIN_PAGE.table.columns.status}</th>
                    <th>{ADMIN_PAGE.table.columns.activity}</th>
                    <th>{ADMIN_PAGE.table.columns.connections}</th>
                    <th className="admin-page__th-actions">{ADMIN_PAGE.table.columns.actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {contas.map((c) => (
                    <tr key={c.id} className={cx('admin-page__row', c.status_conta !== 'ativa' && 'admin-page__row--penalized')}>
                      {/* Vendedor e Loja */}
                      <td>
                        <div className="admin-page__account-cell">
                          <Avatar name={c.nome} size="md" />
                          <div className="admin-page__account-info">
                            <span className="admin-page__account-name">{c.nome}</span>
                            <span className="admin-page__account-email">{c.email}</span>
                            <span className="admin-page__account-store">Loja: {c.loja}</span>
                          </div>
                        </div>
                      </td>

                      {/* Plano e Papel */}
                      <td>
                        <div className="admin-page__role-cell">
                          <span className="admin-page__plan-name">Plano {c.plano}</span>
                          {c.papel === 'admin' ? (
                            <StatusPill tone="mint" size="sm">Admin</StatusPill>
                          ) : (
                            <span className="admin-page__role-tag">Vendedor</span>
                          )}
                        </div>
                      </td>

                      {/* Situação da Conta */}
                      <td>
                        <div className="admin-page__status-cell">
                          <StatusPill
                            tone={ADMIN_PAGE.statusTones[c.status_conta] || 'muted'}
                            size="sm"
                          >
                            {ADMIN_PAGE.statusLabels[c.status_conta] || c.status_conta}
                          </StatusPill>
                          {c.sessao_ativa && (
                            <span className="admin-page__online-dot" title="Sessão recente ativa" />
                          )}
                          {c.motivo_moderacao && (
                            <p className="admin-page__status-reason">{c.motivo_moderacao}</p>
                          )}
                          {c.suspensa_ate && (
                            <p className="admin-page__status-until">Até {formatDate(c.suspensa_ate)}</p>
                          )}
                        </div>
                      </td>

                      {/* Atividade */}
                      <td>
                        <div className="admin-page__activity-cell">
                          <span>Login: {formatDate(c.ultimo_login_em)}</span>
                          <span className="admin-page__access-time">Acesso: {formatDate(c.ultimo_acesso_em)}</span>
                          <span className="admin-page__created-time">Criado: {formatDate(c.criado_em)}</span>
                        </div>
                      </td>

                      {/* Conexões de Marketplaces */}
                      <td>
                        <div className="admin-page__channels-cell">
                          {c.marketplaces_conectados.length === 0 ? (
                            <span className="admin-page__no-channels">Nenhum</span>
                          ) : (
                            c.marketplaces_conectados.map((m) => (
                              <span key={m.slug} className="admin-page__channel-badge">
                                <Icon name="link" size={12} />
                                {m.nome}
                                <button
                                  type="button"
                                  className="admin-page__channel-unbind"
                                  title={`Desvincular ${m.nome}`}
                                  onClick={() => handleOpenModal('disconnect', c, m)}
                                >
                                  ×
                                </button>
                              </span>
                            ))
                          )}
                          <div className="admin-page__counts-tag">
                            <span>{c.total_produtos} anúncios</span> · <span>{c.total_analises_ia} IA</span>
                          </div>
                        </div>
                      </td>

                      {/* Ações Administrativas */}
                      <td className="admin-page__td-actions">
                        <div className="admin-page__action-buttons">
                          {c.status_conta === 'ativa' && (
                            <>
                              <button
                                type="button"
                                className="admin-page__btn admin-page__btn--warn"
                                onClick={() => handleOpenModal('advertir', c)}
                                title="Aplicar advertência"
                              >
                                {ADMIN_PAGE.actions.warn}
                              </button>
                              <button
                                type="button"
                                className="admin-page__btn admin-page__btn--suspend"
                                onClick={() => handleOpenModal('suspender', c)}
                                title="Suspender temporariamente"
                              >
                                {ADMIN_PAGE.actions.suspend}
                              </button>
                            </>
                          )}

                          {c.status_conta !== 'banida' && (
                            <button
                              type="button"
                              className="admin-page__btn admin-page__btn--ban"
                              onClick={() => handleOpenModal('banir', c)}
                              title="Banir vendedor"
                            >
                              {ADMIN_PAGE.actions.ban}
                            </button>
                          )}

                          {c.status_conta !== 'ativa' && (
                            <button
                              type="button"
                              className="admin-page__btn admin-page__btn--reactivate"
                              onClick={() => handleOpenModal('reativar', c)}
                              title="Reativar conta"
                            >
                              {ADMIN_PAGE.actions.reactivate}
                            </button>
                          )}

                          <button
                            type="button"
                            className="admin-page__btn admin-page__btn--kill"
                            onClick={() => handleOpenModal('killSessions', c)}
                            title="Derrubar todas as sessões ativas"
                          >
                            <Icon name="logout" size={14} />
                          </button>

                          <button
                            type="button"
                            className="admin-page__btn admin-page__btn--delete"
                            onClick={() => handleOpenModal('delete', c)}
                            title="Excluir conta definitivamente"
                          >
                            <Icon name="trash" size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      )}

      {/* Aba de Auditoria */}
      {tab === ADMIN_TABS.AUDIT && (
        <Panel tone="paper" className="admin-page__audit-panel">
          <div className="admin-page__audit-header">
            <div>
              <h2 className="admin-page__audit-title">{ADMIN_PAGE.audit.title}</h2>
              <p className="admin-page__audit-lead">{ADMIN_PAGE.audit.lead}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              icon="sync"
              onClick={admin.loadAudit}
              disabled={loadingAudit}
            >
              Recarregar logs
            </Button>
          </div>

          {auditLog.length === 0 && !loadingAudit ? (
            <EmptyState
              icon="shield"
              title="Sem registros"
              description={ADMIN_PAGE.audit.empty}
            />
          ) : (
            <ul className="admin-page__audit-list">
              {auditLog.map((log) => (
                <li key={log.id} className="admin-page__audit-item">
                  <div className="admin-page__audit-top">
                    <span className={cx('admin-page__audit-action', `admin-page__audit-action--${log.acao}`)}>
                      {log.acao}
                    </span>
                    <span className="admin-page__audit-time">{formatDate(log.criado_em)}</span>
                  </div>
                  <div className="admin-page__audit-meta">
                    <span>Admin: <strong>{log.admin_email}</strong></span>
                    <span>Alvo: <strong>{log.alvo_identificador}</strong> (ID #{log.alvo_id})</span>
                  </div>
                  {log.motivo && <p className="admin-page__audit-reason">Motivo: {log.motivo}</p>}
                </li>
              ))}
            </ul>
          )}
        </Panel>
      )}

      {/* Modais de Ação */}
      {activeModal && (
        <Modal
          open={Boolean(activeModal)}
          onClose={closeModal}
          title={
            activeModal.type === 'advertir'
              ? ADMIN_PAGE.modals.warn.title
              : activeModal.type === 'suspender'
              ? ADMIN_PAGE.modals.suspend.title
              : activeModal.type === 'banir'
              ? ADMIN_PAGE.modals.ban.title
              : activeModal.type === 'reativar'
              ? ADMIN_PAGE.modals.reactivate.title
              : activeModal.type === 'killSessions'
              ? ADMIN_PAGE.modals.killSessions.title
              : activeModal.type === 'disconnect'
              ? ADMIN_PAGE.modals.disconnectMarketplace.title
              : ADMIN_PAGE.modals.deleteAccount.title
          }
          description={
            activeModal.type === 'advertir'
              ? ADMIN_PAGE.modals.warn.lead
              : activeModal.type === 'suspender'
              ? ADMIN_PAGE.modals.suspend.lead
              : activeModal.type === 'banir'
              ? ADMIN_PAGE.modals.ban.lead
              : activeModal.type === 'reativar'
              ? ADMIN_PAGE.modals.reactivate.lead
              : activeModal.type === 'killSessions'
              ? ADMIN_PAGE.modals.killSessions.lead
              : activeModal.type === 'disconnect'
              ? ADMIN_PAGE.modals.disconnectMarketplace.lead
              : ADMIN_PAGE.modals.deleteAccount.lead
          }
          icon={
            activeModal.type === 'delete' || activeModal.type === 'banir'
              ? 'alert'
              : 'shield'
          }
          iconTone={
            activeModal.type === 'delete' || activeModal.type === 'banir'
              ? 'danger'
              : 'coral'
          }
          dismissible={!executing}
          actions={
            <div className="admin-page__modal-actions">
              <Button
                variant="outline"
                size="md"
                onClick={closeModal}
                disabled={executing}
              >
                {ADMIN_PAGE.modals.cancel}
              </Button>
              <Button
                variant={activeModal.type === 'delete' || activeModal.type === 'banir' ? 'danger' : 'primary'}
                size="md"
                onClick={handleConfirmModal}
                disabled={executing || (activeModal.type === 'delete' && modalEmailConfirm.trim().toLowerCase() !== activeModal.account.email.toLowerCase())}
              >
                {executing ? 'Processando…' : 'Confirmar ação'}
              </Button>
            </div>
          }
        >
          <form className="admin-page__modal-form" onSubmit={handleConfirmModal}>
            {activeModal.account && (
              <div className="admin-page__modal-target">
                Conta alvo: <strong>{activeModal.account.nome}</strong> ({activeModal.account.email})
              </div>
            )}

            {activeModal.channel && (
              <div className="admin-page__modal-target">
                Marketplace: <strong>{activeModal.channel.nome}</strong>
              </div>
            )}

            {activeModal.type === 'suspender' && (
              <div className="admin-page__form-group">
                <label htmlFor="admin-suspension-days" className="admin-page__label">
                  {ADMIN_PAGE.modals.suspend.daysLabel}
                </label>
                <input
                  id="admin-suspension-days"
                  type="number"
                  min="1"
                  max="365"
                  className="admin-page__input"
                  value={modalDays}
                  onChange={(e) => setModalDays(e.target.value)}
                  required
                />
              </div>
            )}

            {['advertir', 'suspender', 'banir', 'reativar', 'delete'].includes(activeModal.type) && (
              <div className="admin-page__form-group">
                <label htmlFor="admin-reason" className="admin-page__label">
                  Motivo da ação (registrado na auditoria)
                </label>
                <textarea
                  id="admin-reason"
                  rows="3"
                  className="admin-page__textarea"
                  placeholder="Justifique a decisão para controle interno…"
                  value={modalReason}
                  onChange={(e) => setModalReason(e.target.value)}
                  required={activeModal.type !== 'reativar'}
                />
              </div>
            )}

            {activeModal.type === 'delete' && (
              <div className="admin-page__form-group admin-page__form-group--danger">
                <label htmlFor="admin-email-confirm" className="admin-page__label">
                  {ADMIN_PAGE.modals.deleteAccount.confirmationLabel}
                </label>
                <input
                  id="admin-email-confirm"
                  type="email"
                  className="admin-page__input"
                  placeholder={activeModal.account.email}
                  value={modalEmailConfirm}
                  onChange={(e) => setModalEmailConfirm(e.target.value)}
                  required
                />
              </div>
            )}
          </form>
        </Modal>
      )}
    </div>
  );
}
