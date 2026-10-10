import ListingArt from '@/presentation/components/ListingArt/ListingArt.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './ListingThumb.css';

/**
 * Miniatura de um anúncio: a foto de capa ou, nos anúncios de demonstração,
 * o desenho em SVG. Decorativa (o título do anúncio fica ao lado).
 * size: 'sm' | 'md' | 'lg' | 'fill'
 */
export default function ListingThumb({ listing, size = 'md', className }) {
  const photos = listing.photos ?? [];
  const photo = photos[listing.coverIndex ?? 0] ?? photos[0];

  return (
    <span className={cx('listing-thumb', `listing-thumb--${size}`, className)}>
      {photo ? (
        <img className="listing-thumb__image" src={photo} alt="" />
      ) : (
        <ListingArt kind={listing.illustration} />
      )}
    </span>
  );
}
