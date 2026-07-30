import { useCallback, useEffect, useState } from 'react';

const TOKEN_KEY = 'ai-curator-admin-token';

function useAuth() {
  const [token, setToken] = useState(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (saved) {
      setToken(saved);
    }
    setIsReady(true);
  }, []);

  const login = useCallback((newToken) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
  }, []);

  return { token, isReady, isLoggedIn: Boolean(token), login, logout };
}

export default useAuth;
