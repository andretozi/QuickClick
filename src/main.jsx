import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './styles/global.css';

// StrictMode intentionally omitted: React 18 double-invokes effects in dev,
// which would fire IntersectionObservers and hero-cursor timers twice and
// desync the choreography copied verbatim from the DCLogic runtime.
createRoot(document.getElementById('root')).render(<App />);