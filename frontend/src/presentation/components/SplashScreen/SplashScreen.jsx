import { useRef } from 'react';
import Backdrop from '@/presentation/components/Backdrop/Backdrop.jsx';
import LogoMark from '@/presentation/components/Brand/LogoMark.jsx';
import { useStandaloneAnimations } from '@/application/animation/useShellAnimations.js';
import { SPLASH } from '@/domain/content/commonContent.js';
import './SplashScreen.css';

/** Tela curtinha enquanto a sessão é conferida ou um redirecionamento acontece. */
export default function SplashScreen() {
  const rootRef = useRef(null);
  useStandaloneAnimations(rootRef);

  return (
    <div ref={rootRef} className="splash" role="status" aria-label={SPLASH.label}>
      <Backdrop mode="contained" />
      <div className="splash__mark">
        <LogoMark size="lg" />
      </div>
    </div>
  );
}
