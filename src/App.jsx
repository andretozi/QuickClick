import { useEffect, useState } from 'react';
import Landing from './pages/Landing.jsx';
import Login from './pages/Login.jsx';

function readRoute() {
  return window.location.hash.replace(/^#\/?/, '').toLowerCase() || 'landing';
}

export default function App() {
  const [route, setRoute] = useState(readRoute);

  useEffect(() => {
    const onHash = () => {
      setRoute(readRoute());
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  if (route === 'login') return <Login />;
  return <Landing />;
}