/**
 * Domínio · Conteúdo e textos do Painel Administrativo / Moderação
 *
 * Segue as diretrizes de redação: tom acolhedor, conciso, pontuação natural,
 * sem termos técnicos agressivos e sem barras ou hifens soltos.
 */

export const ADMIN_PAGE = {
  eyebrow: 'SUPERVISÃO E SEGURANÇA',
  title: 'Painel de Moderação',
  lead: 'Supervisione contas de vendedores, aplique medidas corretivas, encerre sessões remotamente e mantenha a integridade do ecossistema QuickClick.',
  stats: {
    label: 'Métricas gerais da plataforma',
    totalUsers: 'Total de contas',
    activeSessions: 'Sessões recentes',
    penalized: 'Contas punidas',
    connections: 'Vínculos de marketplaces'
  },
  filters: {
    statusLabel: 'Filtrar por situação',
    searchPlaceholder: 'Buscar por nome, email ou loja…',
    options: [
      { id: 'todos', label: 'Todas' },
      { id: 'ativas', label: 'Ativas' },
      { id: 'advertidas', label: 'Advertidas' },
      { id: 'suspensas', label: 'Suspensas' },
      { id: 'banidas', label: 'Banidas' }
    ]
  },
  table: {
    columns: {
      account: 'Vendedor e Loja',
      plan: 'Plano e Papel',
      status: 'Situação',
      activity: 'Última atividade',
      connections: 'Canais vinculados',
      actions: 'Ações'
    },
    emptyTitle: 'Nenhuma conta encontrada',
    emptyLead: 'Tente alterar os filtros ou o termo pesquisado para localizar vendedores.'
  },
  statusTones: {
    ativa: 'mint',
    advertida: 'amber',
    suspensa: 'coral',
    banida: 'ruby'
  },
  statusLabels: {
    ativa: 'Ativa',
    advertida: 'Advertida',
    suspensa: 'Suspensa',
    banida: 'Banida'
  },
  actions: {
    warn: 'Advertir',
    suspend: 'Suspender',
    ban: 'Banir',
    reactivate: 'Reativar',
    killSessions: 'Derrubar sessões',
    disconnect: 'Desvincular',
    deleteAccount: 'Excluir conta'
  },
  modals: {
    warn: {
      title: 'Aplicar advertência',
      lead: 'O vendedor receberá uma notificação orientativa ao acessar o painel.',
      reasonLabel: 'Motivo da advertência',
      reasonPlaceholder: 'Descreva a conduta ou orientação necessária…',
      confirm: 'Enviar advertência'
    },
    suspend: {
      title: 'Suspender conta temporariamente',
      lead: 'Durante a suspensão, o acesso à conta e às APIs de sincronização ficará bloqueado.',
      daysLabel: 'Duração da suspensão (em dias)',
      reasonLabel: 'Motivo da suspensão',
      reasonPlaceholder: 'Explique a infração detectada…',
      confirm: 'Confirmar suspensão'
    },
    ban: {
      title: 'Banir conta definitivamente',
      lead: 'O vendedor será impedido de entrar na plataforma e todas as sessões ativas serão encerradas imediatamente.',
      reasonLabel: 'Motivo do banimento',
      reasonPlaceholder: 'Justificativa do banimento…',
      confirm: 'Confirmar banimento'
    },
    reactivate: {
      title: 'Reativar conta',
      lead: 'A conta voltará à situação ativa, permitindo novos logins e operações normalmente.',
      reasonLabel: 'Motivo da reativação',
      reasonPlaceholder: 'Explique a regularização…',
      confirm: 'Reativar agora'
    },
    killSessions: {
      title: 'Derrubar todas as sessões',
      lead: 'Todos os tokens emitidos serão invalidados instantaneamente. O usuário precisará fazer login novamente.',
      confirm: 'Encerrar sessões'
    },
    disconnectMarketplace: {
      title: 'Desvincular canal de marketplace',
      lead: 'Os tokens e permissões de acesso ao marketplace selecionado serão excluídos do sistema.',
      confirm: 'Desvincular canal'
    },
    deleteAccount: {
      title: 'Excluir conta definitivamente',
      lead: 'Atenção: esta ação é irreversível. Todos os produtos cadastrados, vínculos de marketplaces, registros de inteligência artificial e preferências serão expurgados do banco de dados.',
      confirmationLabel: 'Confirme digitando o email exato da conta:',
      reasonLabel: 'Motivo da exclusão permanente',
      reasonPlaceholder: 'Justificativa para auditoria…',
      confirm: 'Excluir definitivamente'
    },
    cancel: 'Cancelar'
  },
  audit: {
    title: 'Trilha recente de auditoria',
    lead: 'Histórico imutável de ações administrativas para conformidade e segurança.',
    empty: 'Nenhuma ação de moderação registrada recentemente.'
  }
};
