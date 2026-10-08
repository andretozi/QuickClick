import SceneCard from '../SceneCard/SceneCard.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import { SCENES } from '@/domain/content/landingContent.js';
import './SaleScene.css';

/** Passo 4: gráfico de faturamento subindo e a notificação de venda. */
export default function SaleScene() {
  const { store, avatar, caption, toastTitle, amount, bars } = SCENES.sale;

  return (
    <div className="sale-scene" data-scene="sale" aria-hidden="true">
      <SceneCard className="sale-scene__card">
        <div data-part="store" className="sale-scene__store">
          <div className="sale-scene__avatar">{avatar}</div>
          <div>
            <div className="sale-scene__store-name">{store}</div>
            <div className="sale-scene__caption">{caption}</div>
          </div>
        </div>

        <div className="sale-scene__chart">
          {bars.map((bar, index) => (
            <div
              key={index}
              data-part="bar"
              className={`sale-scene__bar sale-scene__bar--${bar.tone}`}
              style={{ '--bar-height': bar.height }}
            />
          ))}
        </div>

        <div className="sale-scene__notification">
          <div data-part="ring" className="sale-scene__ring" />
          <div data-part="toast" className="sale-scene__toast">
            <div className="sale-scene__toast-icon">
              <Icon name="check" size={18} strokeWidth={2.8} />
            </div>
            <div>
              <div className="sale-scene__toast-title">{toastTitle}</div>
              <div data-part="amount" className="sale-scene__amount">
                {amount}
              </div>
            </div>
          </div>
        </div>
      </SceneCard>
    </div>
  );
}
