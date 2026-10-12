import { cx } from '@/presentation/utils/cx.js';
import { coverPhoto } from '@/domain/listings/listingRules.js';
import './ListingThumb.css';

/**
 * Miniatura de um anúncio: a foto de capa (todo anúncio tem foto; sem ela, fica só o fundo).
 * Decorativa: o título do anúncio fica ao lado.
 */
export default function ListingThumb({ listing, className }) {
  const photo = coverPhoto(listing);

  return (
    <span className={cx('listing-thumb', className)}>
      {photo && <img className="listing-thumb__image" src={photo} alt="" />}
    </span>
  );
}
