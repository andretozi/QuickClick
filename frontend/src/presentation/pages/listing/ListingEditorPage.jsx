import { useRef } from 'react';
import Button from '@/presentation/components/Button/Button.jsx';
import EmptyState from '@/presentation/components/EmptyState/EmptyState.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import PageHeader from '@/presentation/components/PageHeader/PageHeader.jsx';
import Panel from '@/presentation/components/Panel/Panel.jsx';
import ParticleBurst from '@/presentation/components/ParticleBurst/ParticleBurst.jsx';
import Stepper from '@/presentation/components/Stepper/Stepper.jsx';
import StatusPanel from '@/presentation/components/StatusPanel/StatusPanel.jsx';
import AiQuota from '@/presentation/components/AiQuota/AiQuota.jsx';
import PhotosStep from './components/PhotosStep/PhotosStep.jsx';
import AnalysisStep from './components/AnalysisStep/AnalysisStep.jsx';
import ConfirmStep from './components/ConfirmStep/ConfirmStep.jsx';
import DetailsStep from './components/DetailsStep/DetailsStep.jsx';
import PriceStep from './components/PriceStep/PriceStep.jsx';
import ChannelsStep from './components/ChannelsStep/ChannelsStep.jsx';
import PublishStep from './components/PublishStep/PublishStep.jsx';
import PublishSuccess from './components/PublishSuccess/PublishSuccess.jsx';
import useListingEditor from '@/application/listings/useListingEditor.js';
import useCelebration from '@/application/animation/useCelebration.js';
import { hrefForListing } from '@/application/navigation/routes.js';
import { cx } from '@/presentation/utils/cx.js';
import { LISTING_EDITOR, LISTING_WIZARD } from '@/domain/content/listingContent.js';
import { STORAGE_ERRORS } from '@/domain/content/commonContent.js';
import { coverPhoto } from '@/domain/listings/listingRules.js';
import './ListingEditorPage.css';

const STEP_VIEWS = {
  photos: PhotosStep,
  analysis: AnalysisStep,
  confirm: ConfirmStep,
  details: DetailsStep,
  price: PriceStep,
  channels: ChannelsStep,
  publish: PublishStep
};

/**
 * Criar anúncio (#/anuncios/novo) e editar (#/anuncios/:id/editar): o assistente com o trilho
 * animado (fotos, análise da IA, confirmar, detalhes, preço, canais e publicar), o rascunho
 * salvo sozinho, o selo do plano com as análises restantes e a comemoração ao publicar.
 */
export default function ListingEditorPage({ params }) {
  const rootRef = useRef(null);
  const celebrate = useCelebration(rootRef);
  const editor = useListingEditor({ listingId: params?.id, celebrate });
  const { editing, status, step, stepIndex, steps, result, publishing } = editor;
  const header = editing ? LISTING_EDITOR : LISTING_WIZARD;
  const { nav } = LISTING_WIZARD;
  const StepView = STEP_VIEWS[step];
  const last = stepIndex === steps.length - 1;
  const { quota } = editor;
  const quotaTexts = LISTING_WIZARD.quota;

  // O botão de seguir de cada passo: no Confirmar, confirma; na Análise, só quando a leitura terminou
  let forward = { label: nav.next, onClick: editor.next };
  if (step === 'confirm') {
    forward = { label: LISTING_WIZARD.confirm.button, onClick: editor.confirm, loading: editor.ai.sending, loadingText: LISTING_WIZARD.confirm.sending };
  } else if (step === 'analysis') {
    forward = ['waiting', 'ready'].includes(editor.ai.phase) ? { label: LISTING_WIZARD.analysis.toConfirm, onClick: editor.next } : null;
  }

  return (
    <div ref={rootRef} className="listing-editor">
      <ParticleBurst data-part="particles" className="listing-editor__particles" />
      <span data-part="celebrate-cursor" className="listing-editor__cursor" aria-hidden="true">
        <Icon name="logo-spark" size={84} className="listing-editor__cursor-icon" />
      </span>

      <PageHeader
        eyebrow={header.eyebrow}
        title={header.title}
        lead={header.lead}
        actions={
          editing ? (
            <Button
              href={params?.id ? hrefForListing(params.id) : LISTING_EDITOR.back.href}
              variant="light"
              size="sm"
              icon="arrow-left"
              iconPosition="start"
              iconSize={16}
            >
              {LISTING_EDITOR.back.label}
            </Button>
          ) : (
            !result && (
              <div className="listing-editor__status">
                {quota && (
                  <AiQuota
                    plan={quotaTexts.badge(quotaTexts.plans[quota.plan] ?? quota.plan)}
                    remaining={quota.remaining > 0 ? quotaTexts.remaining(quota.remaining, quota.perMonth) : quotaTexts.none}
                    empty={quota.remaining <= 0}
                  />
                )}
                {editor.savedAt && (
                  <p className="listing-editor__saved" aria-live="polite">
                    <Icon name="check-circle" size={16} />
                    {LISTING_WIZARD.draftSaved(editor.savedAt)}
                  </p>
                )}
              </div>
            )
          )
        }
      />

      {status === 'loading' && <StatusPanel text={LISTING_EDITOR.loading} />}

      {status === 'not-found' && (
        <Panel tone="glass" data-enter="2">
          <EmptyState icon="search" tone="glass" title={LISTING_EDITOR.notFound.title} text={LISTING_EDITOR.notFound.text}>
            <Button href={LISTING_EDITOR.notFound.action.href}>{LISTING_EDITOR.notFound.action.label}</Button>
          </EmptyState>
        </Panel>
      )}

      {status === 'ready' && result && (
        <PublishSuccess
          published={result.published}
          permalink={result.permalink}
          photo={coverPhoto(editor.draft)}
          onAnother={editor.restart}
        />
      )}

      {status === 'ready' && !result && (
        <>
          <Stepper
            data-enter="1"
            label={LISTING_WIZARD.steps.label}
            steps={steps.map((id) => ({ id, ...LISTING_WIZARD.steps.items[id] }))}
            current={stepIndex}
            visited={editor.visited}
            onSelect={editor.goTo}
            className="listing-editor__stepper"
          />

          {editor.storageFull && (
            <p className="listing-editor__warning" role="alert">
              <Icon name="alert" size={18} />
              <span>
                <strong>{STORAGE_ERRORS.full.title}</strong> {STORAGE_ERRORS.full.text}
              </span>
            </p>
          )}

          <Panel tone="paper" data-enter="2" className="listing-editor__panel">
            <p className="visually-hidden" aria-live="polite">
              {LISTING_WIZARD.steps.current(stepIndex + 1, steps.length)}
            </p>
            <div ref={editor.formRef} key={step} className="listing-editor__step">
              <StepView editor={editor} />
            </div>

            <footer className="listing-editor__footer">
              <Button
                variant="outline"
                icon="arrow-left"
                iconPosition="start"
                iconSize={16}
                onClick={editor.back}
                className={cx(stepIndex === 0 && 'listing-editor__hidden')}
                disabled={stepIndex === 0}
              >
                {nav.back}
              </Button>

              <div className="listing-editor__footer-end">
                {editing && (
                  <Button
                    variant={last ? 'primary' : 'dark'}
                    icon="check"
                    iconPosition="start"
                    iconSize={17}
                    onClick={editor.finish}
                    loading={publishing}
                    loadingText={nav.saving}
                    disabled={publishing}
                  >
                    {nav.save}
                  </Button>
                )}
                {!last && forward && (
                  <Button
                    icon="arrow-right"
                    iconSize={16}
                    variant={editing ? 'light' : 'primary'}
                    onClick={forward.onClick}
                    loading={forward.loading}
                    loadingText={forward.loadingText}
                    disabled={forward.loading}
                  >
                    {forward.label}
                  </Button>
                )}
                {last && !editing && (
                  <Button
                    data-part="celebrate-target"
                    size="lg"
                    icon="sparkles"
                    iconPosition="start"
                    iconSize={19}
                    onClick={editor.finish}
                    loading={publishing}
                    loadingText={editor.willPublish ? nav.publishing : nav.saving}
                    disabled={publishing}
                    className="listing-editor__publish"
                  >
                    {editor.willPublish ? nav.publish : nav.saveNew}
                  </Button>
                )}
              </div>
            </footer>
          </Panel>
        </>
      )}
    </div>
  );
}
