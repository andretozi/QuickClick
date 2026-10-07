import { useRef } from 'react';
import useLoginAnimations from '@/application/animation/useLoginAnimations.js';
import BrandPanel from './components/BrandPanel/BrandPanel.jsx';
import LoginForm from './components/LoginForm/LoginForm.jsx';
import './LoginPage.css';

/** Tela de login: painel da marca à esquerda e formulário à direita. */
export default function LoginPage() {
  const rootRef = useRef(null);
  useLoginAnimations(rootRef);

  return (
    <div ref={rootRef} className="login">
      <BrandPanel />
      <main className="login__main">
        <LoginForm />
      </main>
    </div>
  );
}
