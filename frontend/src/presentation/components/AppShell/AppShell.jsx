import { useRef } from 'react';
import Backdrop from '@/presentation/components/Backdrop/Backdrop.jsx';
import SiteNav from '@/presentation/components/SiteNav/SiteNav.jsx';
import useShellAnimations from '@/application/animation/useShellAnimations.js';
import { APP_NAV } from '@/domain/content/appContent.js';
import './AppShell.css';

/**
 * Casca das páginas logadas: o mesmo navbar do site (no tom escuro), o fundo
 * cinematográfico parado atrás e o conteúdo da página. A casca continua montada
 * entre uma página e outra; só o conteúdo troca, com a entrada em sequência
 * ([data-enter]: 1 = título, 2 = conteúdo, 3 = detalhes).
 */
export default function AppShell({ current, children }) {
  const rootRef = useRef(null);
  const mainRef = useRef(null);
  useShellAnimations(rootRef);

  // "Pular para o conteúdo" é um botão: um link com hash viraria uma rota da landing
  const skipToContent = () => mainRef.current?.focus();

  return (
    <div ref={rootRef} className="app-shell">
      <button type="button" className="app-shell__skip" onClick={skipToContent}>
        {APP_NAV.skipLink}
      </button>
      <Backdrop mode="fixed" />
      <SiteNav tone="dark" variant="app" current={current} />
      <main ref={mainRef} tabIndex={-1} className="app-shell__main">
        {children}
      </main>
    </div>
  );
}
