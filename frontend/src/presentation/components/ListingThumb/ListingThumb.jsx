import { useState } from 'react';
import { cx } from '@/presentation/utils/cx.js';
import { coverPhoto } from '@/domain/listings/listingRules.js';
import './ListingThumb.css';

/**
 * Miniatura de um anúncio: a foto de capa. Sem foto, ou com uma URL que não carrega, fica só o
 * fundo como espaço reservado (nunca a imagem quebrada).
 * Decorativa: o título do anúncio fica ao lado.
 */
export default function ListingThumb({ listing, className }) {
  const photo = coverPhoto(listing);
  const [broken, setBroken] = useState(null);

  return (
    <span className={cx('listing-thumb', className)}>
      {photo && photo !== broken && (
        <img className="listing-thumb__image" src={photo} alt="" onError={() => setBroken(photo)} />
      )}
    </span>
  );
}
