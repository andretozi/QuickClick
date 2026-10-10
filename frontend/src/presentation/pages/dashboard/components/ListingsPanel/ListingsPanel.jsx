import Button from '@/presentation/components/Button/Button.jsx';
import EmptyState from '@/presentation/components/EmptyState/EmptyState.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import Panel from '@/presentation/components/Panel/Panel.jsx';
import SelectField from '@/presentation/components/Field/SelectField.jsx';
import TextField from '@/presentation/components/Field/TextField.jsx';
import ListingRow from '../ListingRow/ListingRow.jsx';
import { LISTINGS_PANEL } from '@/domain/content/dashboardContent.js';
import './ListingsPanel.css';

/**
 * Aba "Anúncios" do painel: busca, filtro e ordenação, a lista e os estados
 * (carregando, erro, vazio e nenhum resultado). Tudo vem do useDashboard.
 */
export default function ListingsPanel({ dashboard }) {
  const { status, listings, visibleListings, filters, setFilter, clearFilters, busyId, mercadoLivreConnected } = dashboard;
  const { title, count, search, filter, sort, listLabel, empty, noResults, loading, loadError } = LISTINGS_PANEL;

  if (status === 'loading') {
    return (
      <Panel tone="glass" className="listings-panel__status" role="status">
        <span data-spin className="listings-panel__spinner" aria-hidden="true" />
        {loading}
      </Panel>
    );
  }

  if (status === 'error') {
    return (
      <Panel tone="glass" className="listings-panel__status" role="alert">
        <p className="listings-panel__status-title">{loadError.title}</p>
        <Button size="sm" variant="light" onClick={dashboard.retry}>
          {loadError.retry}
        </Button>
      </Panel>
    );
  }

  if (listings.length === 0) {
    return (
      <Panel tone="glass" data-enter="2">
        <EmptyState icon="camera" tone="glass" title={empty.title} text={empty.text}>
          <Button href={empty.cta.href} icon="plus" iconPosition="start" iconSize={18}>
            {empty.cta.label}
          </Button>
        </EmptyState>
      </Panel>
    );
  }

  return (
    <Panel tone="paper" data-enter="2" className="listings-panel" aria-labelledby="anuncios-titulo">
      <div className="listings-panel__head">
        <h2 id="anuncios-titulo" className="heading listings-panel__title">
          {title}
        </h2>
        <p className="listings-panel__count" aria-live="polite">
          {count(visibleListings.length, listings.length)}
        </p>
      </div>

      <div className="listings-panel__toolbar">
        <TextField
          id="anuncios-busca"
          name="query"
          type="search"
          label={search.label}
          placeholder={search.placeholder}
          value={filters.query}
          onChange={setFilter}
          leading={<Icon name="search" size={17} />}
          className="listings-panel__search"
        />
        <SelectField
          id="anuncios-filtro"
          name="status"
          label={filter.label}
          options={filter.options}
          value={filters.status}
          onChange={setFilter}
        />
        <SelectField
          id="anuncios-ordem"
          name="sort"
          label={sort.label}
          options={sort.options}
          value={filters.sort}
          onChange={setFilter}
        />
      </div>

      {visibleListings.length === 0 ? (
        <EmptyState icon="search" title={noResults.title} text={noResults.text} className="listings-panel__empty">
          <Button size="sm" variant="outline" onClick={clearFilters}>
            {noResults.clear}
          </Button>
        </EmptyState>
      ) : (
        <ul className="listings-panel__list" aria-label={listLabel}>
          {visibleListings.map((listing) => (
            <ListingRow
              key={listing.id}
              listing={listing}
              busy={busyId === listing.id}
              canPublish={mercadoLivreConnected}
              onToggle={dashboard.toggleStatus}
              onDuplicate={dashboard.duplicate}
              onRemove={dashboard.requestRemoval}
            />
          ))}
        </ul>
      )}
    </Panel>
  );
}
