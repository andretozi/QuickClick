import SceneCard from '../SceneCard/SceneCard.jsx';
import Icon from '@/presentation/components/Icon/Icon.jsx';
import { cx } from '@/presentation/utils/cx.js';
import { SCENES } from '@/domain/content/landingContent.js';
import './AiScene.css';

/** Passo 3: radar da IA comparando os marketplaces e recomendando o melhor. */
export default function AiScene() {
  const { channels, recommendedLabel, chartLabel, bars } = SCENES.ai;

  return (
    <div className="ai-scene" data-scene="ai" aria-hidden="true">
      <SceneCard>
        <div className="ai-scene__head">
          <div className="ai-scene__radar">
            <div data-part="sweep" className="ai-scene__sweep" />
            <div className="ai-scene__ring ai-scene__ring--outer" />
            <div className="ai-scene__ring ai-scene__ring--inner" />
            <div data-part="core" className="ai-scene__core">
              <Icon name="sparkle" size={26} />
            </div>
          </div>

          <div className="ai-scene__channels">
            <div data-part="scan" className="ai-scene__scan" />
            {channels.map((channel) => (
              <div
                key={channel.name}
                data-part="channel"
                data-recommended={channel.recommended || undefined}
                className={cx('ai-scene__channel', channel.recommended && 'ai-scene__channel--recommended')}
              >
                <span className={`ai-scene__dot ai-scene__dot--${channel.tone}`} />
                <div className="ai-scene__channel-body">
                  <div className="ai-scene__channel-name">{channel.name}</div>
                  <div className="ai-scene__channel-detail">{channel.detail}</div>
                </div>
                {channel.recommended && (
                  <span data-part="tag" className="ai-scene__tag">
                    {recommendedLabel}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="ai-scene__chart">
          <span className="ai-scene__chart-label">{chartLabel}</span>
          {bars.map((bar, index) => (
            <div
              key={index}
              data-part="bar"
              className={cx('ai-scene__bar', bar.peak && 'ai-scene__bar--peak')}
              style={{ '--bar-height': bar.height, '--bar-alpha': bar.alpha }}
            />
          ))}
        </div>
      </SceneCard>
    </div>
  );
}
