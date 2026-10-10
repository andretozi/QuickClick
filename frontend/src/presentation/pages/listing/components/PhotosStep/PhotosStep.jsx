import FileDrop from '@/presentation/components/FileDrop/FileDrop.jsx';
import IconButton from '@/presentation/components/IconButton/IconButton.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { LISTING_LIMITS } from '@/domain/listings/listingRules.js';
import { LISTING_WIZARD } from '@/domain/content/listingContent.js';
import { FIELD_ERRORS } from '@/domain/content/commonContent.js';
import './PhotosStep.css';

/** Passo 1: até 6 fotos, arrastando ou escolhendo, e a escolha da capa. */
export default function PhotosStep({ editor }) {
  const { draft, photos, errors } = editor;
  const texts = LISTING_WIZARD.photos;
  const max = LISTING_LIMITS.PHOTOS_MAX;
  const photoError =
    photos.error === 'full' ? texts.full(max) : photos.error === 'invalid' ? texts.invalid : FIELD_ERRORS[errors.photos];

  return (
    <div className="photos-step">
      <header className="photos-step__head">
        <h2 className="heading photos-step__title">{texts.title}</h2>
        <p className="photos-step__lead">{texts.lead}</p>
      </header>

      <FileDrop
        id="anuncio-fotos"
        onFiles={photos.add}
        busy={photos.busy}
        disabled={draft.photos.length >= max}
        invalid={Boolean(errors.photos)}
        error={photoError}
        texts={{ ...texts.drop, hint: texts.drop.hint(max) }}
      />

      {draft.photos.length > 0 && (
        <>
          <p className="photos-step__count" aria-live="polite">
            {texts.count(draft.photos.length, max)}
          </p>
          <ul className="photos-step__grid">
            {draft.photos.map((photo, index) => {
              const cover = index === draft.coverIndex;
              return (
                <li key={photo.slice(-40)} className={cx('photos-step__item', cover && 'photos-step__item--cover')}>
                  <img src={photo} alt={texts.photoAlt(index + 1)} className="photos-step__image" />
                  {cover ? (
                    <span className="photos-step__badge">
                      <Icon name="star-filled" size={13} />
                      {texts.cover}
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="photos-step__make-cover"
                      onClick={() => photos.setCover(index)}
                      aria-label={texts.makeCoverLabel(index + 1)}
                    >
                      <Icon name="star" size={13} />
                      {texts.makeCover}
                    </button>
                  )}
                  <IconButton
                    icon="x"
                    size="sm"
                    tone="glass"
                    label={texts.removeLabel(index + 1)}
                    className="photos-step__remove"
                    onClick={() => photos.remove(index)}
                  />
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}
