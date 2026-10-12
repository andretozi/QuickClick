import Icon from '@/presentation/components/Icon/Icon.jsx';
import MarketplaceLogo from '@/presentation/components/MarketplaceLogo/MarketplaceLogo.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './ListingPreview.css';

/**
 * Prévia do anúncio do jeito que ele aparece no Mercado Livre (só uma ilustração:
 * cabeçalho amarelo, foto, título, preço e estoque). Decorativa; o resumo de verdade
 * fica ao lado, em texto.
 * - photo, title, price (texto pronto), condition (texto), stock (texto)
 * - texts: { label, shipping, buy }
 */
export default function ListingPreview({ photo, title, price, condition, stock, texts, className }) {
  return (
    <figure className={cx('listing-preview', className)}>
      <figcaption className="listing-preview__caption">{texts.label}</figcaption>
      <div className="listing-preview__device" aria-hidden="true">
        <div className="listing-preview__bar">
          <MarketplaceLogo slug="mercado-livre" size="sm" decorative />
          <span className="listing-preview__search" />
        </div>
        <div className="listing-preview__body">
          <div className="listing-preview__photo">
            {photo ? <img src={photo} alt="" className="listing-preview__image" /> : <Icon name="image" size={34} />}
          </div>
          <div className="listing-preview__info">
            <p className="listing-preview__condition">{condition}</p>
            <p className="listing-preview__title">{title}</p>
            <p className="listing-preview__price">{price}</p>
            <p className="listing-preview__shipping">{texts.shipping}</p>
            <p className="listing-preview__stock">{stock}</p>
            <span className="listing-preview__buy">{texts.buy}</span>
          </div>
        </div>
      </div>
    </figure>
  );
}
