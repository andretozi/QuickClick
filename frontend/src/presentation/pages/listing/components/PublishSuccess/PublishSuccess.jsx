import Button from '@/presentation/components/Button/Button.jsx';
import Eyebrow from '@/presentation/components/Eyebrow/Eyebrow.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import Panel from '@/presentation/components/Panel/Panel.jsx';
import { LISTING_WIZARD } from '@/domain/content/listingContent.js';
import './PublishSuccess.css';

/** Tela de sucesso depois de publicar (ou salvar fora do ar). */
export default function PublishSuccess({ published, photo, onAnother }) {
  const texts = LISTING_WIZARD.success;

  return (
    <Panel tone="glass" data-enter="2" className="publish-success" aria-labelledby="sucesso-titulo">
      <span className="publish-success__art" aria-hidden="true">
        <span className="publish-success__halo" />
        {photo && <img src={photo} alt="" className="publish-success__photo" />}
        <span className="publish-success__check">
          <Icon name="check" size={28} />
        </span>
      </span>
      <Eyebrow tone="coral">{texts.eyebrow}</Eyebrow>
      <h2 id="sucesso-titulo" data-page-focus tabIndex={-1} className="heading publish-success__title">
        {published ? texts.title : texts.titleSaved}
      </h2>
      <p className="publish-success__text">{published ? texts.text : texts.textSaved}</p>
      <div className="publish-success__actions">
        <Button href={texts.dashboard.href} icon="grid" iconPosition="start" iconSize={17}>
          {texts.dashboard.label}
        </Button>
        <Button variant="light" icon="plus" iconPosition="start" iconSize={17} onClick={onAnother}>
          {texts.another}
        </Button>
      </div>
    </Panel>
  );
}
