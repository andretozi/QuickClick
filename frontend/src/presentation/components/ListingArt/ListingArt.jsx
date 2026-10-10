import { cx } from '@/presentation/utils/cx.js';
import './ListingArt.css';

/**
 * Desenhos simples (SVG feitos aqui mesmo) que fazem as vezes de foto nos anúncios
 * de demonstração. Nenhuma imagem de terceiros. As cores vêm dos tokens, pelo CSS.
 */
const ART = {
  tenis: (
    <>
      <ellipse className="listing-art__shadow" cx="60" cy="96" rx="44" ry="6" />
      <path className="listing-art__cream" d="M14 82h80a10 10 0 0110 10v1a4 4 0 01-4 4H22a8 8 0 01-8-8v-7z" />
      <path
        className="listing-art__coral"
        d="M18 84c2-17 10-29 23-31l17-3c6-1 10 3 14 9 6 8 18 13 27 17 5 2 7 6 5 10H18z"
      />
      <path className="listing-art__line listing-art__line--cream" d="M45 57l8 7M52 54l8 7M59 53l7 7" />
      <path className="listing-art__line listing-art__line--honey" d="M30 76c16-6 34-5 54 4" />
    </>
  ),
  luminaria: (
    <>
      <path className="listing-art__glow" d="M82 58L62 100h44z" />
      <ellipse className="listing-art__shadow" cx="44" cy="100" rx="30" ry="5" />
      <ellipse className="listing-art__cocoa" cx="40" cy="95" rx="20" ry="6" />
      <path className="listing-art__line listing-art__line--cocoa listing-art__line--thick" d="M40 92L52 60l26-16" />
      <circle className="listing-art__honey" cx="52" cy="60" r="4.5" />
      <path className="listing-art__honey" d="M66 38l22-12 14 22-24 12z" />
      <path className="listing-art__cream" d="M80 60l20-10 2 4-20 10z" />
    </>
  ),
  fone: (
    <>
      <ellipse className="listing-art__shadow" cx="60" cy="98" rx="38" ry="5" />
      <path className="listing-art__line listing-art__line--cocoa listing-art__line--thick" d="M30 68c0-34 60-34 60 0" />
      <rect className="listing-art__coral" x="20" y="62" width="18" height="30" rx="8" />
      <rect className="listing-art__coral" x="82" y="62" width="18" height="30" rx="8" />
      <rect className="listing-art__cream" x="34" y="66" width="6" height="22" rx="3" />
      <rect className="listing-art__cream" x="80" y="66" width="6" height="22" rx="3" />
    </>
  ),
  mochila: (
    <>
      <ellipse className="listing-art__shadow" cx="60" cy="100" rx="34" ry="5" />
      <path className="listing-art__line listing-art__line--leather-dark listing-art__line--thick" d="M48 34c0-12 24-12 24 0" />
      <rect className="listing-art__leather" x="32" y="32" width="56" height="64" rx="18" />
      <path className="listing-art__leather-dark" d="M32 50c0-10 8-18 18-18h20c10 0 18 8 18 18v6H32z" />
      <rect className="listing-art__leather-dark" x="42" y="66" width="36" height="22" rx="8" />
      <rect className="listing-art__honey" x="56" y="52" width="8" height="8" rx="2" />
    </>
  ),
  vaso: (
    <>
      <path className="listing-art__leaf" d="M60 44C48 30 34 30 28 36c10 2 20 6 32 8z" />
      <path className="listing-art__leaf" d="M60 44c10-16 24-20 32-14-10 4-20 8-32 14z" />
      <path className="listing-art__leaf-dark" d="M60 46c-2-14 2-26 10-32 2 12-2 22-10 32z" />
      <ellipse className="listing-art__shadow" cx="60" cy="100" rx="28" ry="5" />
      <path className="listing-art__green" d="M48 52c-9 12-10 34 2 46h20c12-12 11-34 2-46z" />
      <rect className="listing-art__green-dark" x="47" y="44" width="26" height="10" rx="5" />
      <path className="listing-art__line listing-art__line--cream" d="M52 72c5 3 11 3 16 0" />
    </>
  ),
  jaqueta: (
    <>
      <ellipse className="listing-art__shadow" cx="60" cy="102" rx="36" ry="5" />
      <path className="listing-art__denim" d="M40 30l12-4 8 8 8-8 12 4 16 20-10 10-4-6v44H38V54l-4 6-10-10z" />
      <path className="listing-art__denim-dark" d="M52 26l8 8 8-8 4 8-12 14-12-14z" />
      <path className="listing-art__line listing-art__line--cream" d="M60 48v46" />
      <rect className="listing-art__denim-dark" x="44" y="62" width="12" height="10" rx="2" />
      <rect className="listing-art__denim-dark" x="64" y="62" width="12" height="10" rx="2" />
      <circle className="listing-art__cream" cx="64" cy="56" r="1.8" />
      <circle className="listing-art__cream" cx="64" cy="78" r="1.8" />
    </>
  ),
  cafeteira: (
    <>
      <ellipse className="listing-art__shadow" cx="58" cy="100" rx="30" ry="5" />
      <path className="listing-art__steel" d="M42 66h32l6 30H36z" />
      <path className="listing-art__steel-dark" d="M38 60h40v8H38z" />
      <path className="listing-art__steel" d="M44 30h28l6 30H38z" />
      <path className="listing-art__steel-dark" d="M72 34l12-4-6 10z" />
      <circle className="listing-art__cocoa" cx="58" cy="27" r="4" />
      <path className="listing-art__line listing-art__line--cocoa listing-art__line--thick" d="M40 36c-12 2-14 18-2 22" />
    </>
  ),
  livros: (
    <>
      <ellipse className="listing-art__shadow" cx="60" cy="100" rx="40" ry="5" />
      <rect className="listing-art__green" x="24" y="80" width="72" height="16" rx="3" />
      <rect className="listing-art__coral" x="30" y="64" width="64" height="16" rx="3" />
      <rect className="listing-art__honey" x="22" y="48" width="70" height="16" rx="3" />
      <rect className="listing-art__cocoa" x="34" y="34" width="56" height="14" rx="3" />
      <path className="listing-art__line listing-art__line--cream" d="M30 88h14M38 72h14M30 56h14M42 41h12" />
    </>
  ),
  pacote: (
    <>
      <ellipse className="listing-art__shadow" cx="60" cy="98" rx="34" ry="5" />
      <path className="listing-art__honey" d="M60 30l30 14v34L60 92 30 78V44z" />
      <path className="listing-art__leather" d="M60 58L30 44v34l30 14z" />
      <path className="listing-art__line listing-art__line--cream" d="M30 44l30 14 30-14M60 58v34" />
    </>
  )
};

/** kind: 'tenis' | 'luminaria' | 'fone' | 'mochila' | 'vaso' | 'jaqueta' | 'cafeteira' | 'livros' */
export default function ListingArt({ kind, className }) {
  const art = ART[kind] ?? ART.pacote;
  return (
    <span aria-hidden="true" className={cx('listing-art', `listing-art--${ART[kind] ? kind : 'pacote'}`, className)}>
      <svg viewBox="0 0 120 120" className="listing-art__svg" focusable="false">
        {art}
      </svg>
    </span>
  );
}
