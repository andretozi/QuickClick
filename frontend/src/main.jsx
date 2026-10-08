// Estilos globais primeiro: os CSS dos componentes (importados pelo App) vêm depois
// e podem sobrescrever a base sem precisar de seletores mais fortes.
import '@/presentation/styles/tokens.css';
import '@/presentation/styles/base.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from '@/app/App.jsx';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);
