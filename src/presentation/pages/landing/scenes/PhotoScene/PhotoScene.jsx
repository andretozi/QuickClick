import Icon from '@/presentation/components/Icon/Icon.jsx';
import { SCENES } from '@/domain/content/landingContent.js';
import './PhotoScene.css';

const CORNERS = ['top-left', 'top-right', 'bottom-left', 'bottom-right'];

/** Passo 2: celular fotografando um produto e o anúncio aparecendo ao lado. */
export default function PhotoScene() {
  const { price, done } = SCENES.photo;

  return (
    <div className="photo-scene" data-scene="photo" aria-hidden="true">
      <div className="photo-scene__stage">
        <div className="photo-scene__phone">
          <div className="photo-scene__screen">
            {CORNERS.map((corner) => (
              <div key={corner} data-part="bracket" className={`photo-scene__bracket photo-scene__bracket--${corner}`} />
            ))}
            <div data-part="product" className="photo-scene__product">
              <div className="photo-scene__product-box" />
              <div className="photo-scene__product-shade" />
              <div className="photo-scene__product-tag" />
            </div>
            <div data-part="flash" className="photo-scene__flash" />
          </div>
          <div className="photo-scene__shutter-bar">
            <div data-part="shutter" className="photo-scene__shutter" />
          </div>
        </div>

        <div data-part="listing" className="photo-scene__listing">
          <div className="photo-scene__listing-head">
            <div className="photo-scene__thumb" />
            <div className="photo-scene__lines">
              <div className="photo-scene__line photo-scene__line--long" />
              <div className="photo-scene__line photo-scene__line--short" />
            </div>
          </div>
          <div className="photo-scene__listing-foot">
            <span className="photo-scene__price">{price}</span>
            <span className="photo-scene__done">
              {done}
              <Icon name="check" size={13} strokeWidth={3} />
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
