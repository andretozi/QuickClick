import AiProgress from '@/presentation/components/AiProgress/AiProgress.jsx';
import Button from '@/presentation/components/Button/Button.jsx';
import FormAlert from '@/presentation/components/FormAlert/FormAlert.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import { READING_STAGES, photoQualityTips, stagesProgress } from '@/domain/listings/aiAnalysis.js';
import { coverPhoto } from '@/domain/listings/listingRules.js';
import { LISTING_WIZARD, aiErrorText } from '@/domain/content/listingContent.js';
import './AnalysisStep.css';

/** Passo 2: a IA lê as fotos no back. Progresso real, dicas de foto e, sem IA, os campos manuais. */
export default function AnalysisStep({ editor }) {
  const { draft, ai, quota, resume, fillByHand, goTo, steps } = editor;
  const texts = LISTING_WIZARD.analysis;
  const { analysis, phase } = ai;
  const unavailable = !analysis && quota && (!quota.available || quota.remaining <= 0);
  const reason = quota?.remaining <= 0 ? 'cota_esgotada' : quota?.unavailableReason;
  const failure = phase === 'failed' ? analysis.error : ai.error;
  const stages = stagesProgress(READING_STAGES, analysis).map((stage) => ({
    ...stage,
    label: texts.stages[stage.id]
  }));
  const tips = photoQualityTips(analysis);
  const budget = analysis?.notices?.some((notice) => notice.code === 'orcamento_do_dia');

  return (
    <div className="analysis-step">
      <header>
        <h2 className="heading analysis-step__title">{texts.title}</h2>
        <p className="analysis-step__lead">{texts.lead}</p>
      </header>

      {unavailable && (
        <div className="analysis-step__stop" data-enter="3">
          <FormAlert {...(texts.unavailable[reason] ?? texts.unavailable.provedor_indisponivel)} />
          <Button icon="edit" iconPosition="start" iconSize={16} onClick={fillByHand}>
            {texts.manual}
          </Button>
        </div>
      )}

      {!unavailable && (phase === 'running' || phase === 'idle') && !failure && (
        <AiProgress stages={stages} photo={coverPhoto(draft)} data-enter="3" />
      )}

      {phase === 'idle' && !unavailable && !ai.sending && !failure && (
        <Button variant="dark" icon="sparkles" iconPosition="start" iconSize={17} onClick={editor.startAnalysis}>
          {texts.start}
        </Button>
      )}

      {(phase === 'waiting' || phase === 'ready') && (
        <p className="analysis-step__ready" data-enter="3">
          <Icon name="check-circle" size={20} />
          {texts.ready}
          <Button size="sm" icon="arrow-right" iconSize={15} onClick={() => goTo(steps.indexOf('confirm'))}>
            {texts.toConfirm}
          </Button>
        </p>
      )}

      {failure && (
        <div className="analysis-step__stop" data-enter="3">
          <FormAlert {...aiErrorText(failure.code, failure.message)} />
          <div className="analysis-step__actions">
            {(analysis?.canResume || !analysis) && (
              <Button
                variant="dark"
                icon="sync"
                iconPosition="start"
                iconSize={16}
                loading={ai.sending}
                onClick={analysis ? resume : editor.startAnalysis}
              >
                {texts.retry}
              </Button>
            )}
            <Button variant="outline" icon="edit" iconPosition="start" iconSize={16} onClick={fillByHand}>
              {texts.manual}
            </Button>
          </div>
        </div>
      )}

      {budget && <p className="analysis-step__notice">{LISTING_WIZARD.quota.budget}</p>}

      {tips.length > 0 && (
        <ul className="analysis-step__tips">
          {tips.map((photo) => (
            <li key={photo.index} className="analysis-step__tip" data-enter="3">
              <Icon name="camera" size={16} />
              {texts.quality[photo.quality]?.(photo.index + 1)}
            </li>
          ))}
        </ul>
      )}

      {phase === 'running' && (
        <button type="button" className="analysis-step__skip" onClick={fillByHand}>
          {texts.manual}
        </button>
      )}
    </div>
  );
}
