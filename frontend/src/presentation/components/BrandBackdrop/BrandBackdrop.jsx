import Grain from '@/presentation/components/Grain/Grain.jsx';
import { cx } from '@/presentation/utils/cx.js';
import './BrandBackdrop.css';

/**
 * Imagens de fundo opcionais (geradas por nós numa ferramenta de IA), uma por marca:
 * assets/marketplaces/fundos/<slug>.webp. Sem o arquivo, o fundo é 100% código.
 */
const PHOTOS = Object.fromEntries(
  Object.entries(import.meta.glob('../../assets/marketplaces/fundos/*.webp', { eager: true, import: 'default' })).map(
    ([path, url]) => [path.split('/').pop().replace('.webp', ''), url]
  )
);

/**
 * Fundo cinematográfico nas cores de uma marca, em camadas:
 *   base     degradê em malha com a paleta (primary, secondary, deep);
 *   foto     a imagem opcional, por baixo dos efeitos;
 *   far      manchas de luz grandes e desfocadas (camada de trás do parallax);
 *   streaks  faixas de luz atravessando;
 *   spot     a luz clara no centro, onde o logo fica (o logo lê sobre ela);
 *   vinheta e granulação de filme.
 * As camadas que se mexem têm data-part; quem anima (infrastructure/animation) as acha por ele.
 * - palette: { primary, secondary, deep, glow } (domain/content/marketplacesContent.js)
 * - spotlight: false para não ter a luz do centro (topo de página, por exemplo)
 */
export default function BrandBackdrop({ slug, palette, spotlight = true, className }) {
  const photo = PHOTOS[slug];
  const style = {
    '--brand-primary': palette.primary,
    '--brand-secondary': palette.secondary,
    '--brand-deep': palette.deep,
    '--brand-glow': palette.glow
  };

  return (
    <div aria-hidden="true" className={cx('brand-backdrop', className)} style={style}>
      <span className="brand-backdrop__base" />
      {photo && <img className="brand-backdrop__photo" src={photo} alt="" decoding="async" />}
      <span data-part="depth-far" className="brand-backdrop__far">
        <span data-part="drift" className="brand-backdrop__orb brand-backdrop__orb--a" />
        <span data-part="drift" className="brand-backdrop__orb brand-backdrop__orb--b" />
        <span data-part="drift" className="brand-backdrop__orb brand-backdrop__orb--c" />
      </span>
      <span data-part="depth-near" className="brand-backdrop__streaks">
        <span data-part="streak" className="brand-backdrop__streak brand-backdrop__streak--a" />
        <span data-part="streak" className="brand-backdrop__streak brand-backdrop__streak--b" />
      </span>
      {spotlight && <span data-part="spot" className="brand-backdrop__spot" />}
      <span className="brand-backdrop__vignette" />
      <Grain className="brand-backdrop__grain" />
    </div>
  );
}
