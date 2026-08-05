import { useCallback, useEffect, useState } from 'react';

const TOKEN_KEY = 'ai-curator-admin-token';

function isDemoToken(token) {
  const configuredDemoToken = import.meta.env.VITE_ADMIN_DEMO_TOKEN;
  return Boolean(configuredDemoToken) && token === configuredDemoToken;
}

function useAuth() {
  const [token, setToken] = useState(null);
  const [isDemo, setIsDemo] = useState(false);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (saved) {
      setToken(saved);
      setIsDemo(isDemoToken(saved));
    }
    setIsReady(true);
  }, []);

  const login = useCallback((newToken) => {
    const demo = isDemoToken(newToken);
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
    setIsDemo(demo);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setIsDemo(false);
  }, []);

  return { token, isReady, isLoggedIn: Boolean(token), isDemo, login, logout };
}

export default useAuth;
