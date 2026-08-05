import { createContext, useCallback, useEffect, useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://curator-api.alex-n8n.site';

const DemoContext = createContext(null);

const TOKEN_KEY = 'ai-curator-demo-token';
const SESSION_KEY = 'ai-curator-session-id';

function generateSessionId() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function DemoProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [sessionId, setSessionId] = useState(() => localStorage.getItem(SESSION_KEY) || generateSessionId());
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const startDemo = useCallback(async (existingSessionId = null) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/demo/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: existingSessionId || sessionId }),
      });

      const text = await response.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        data = { detail: text };
      }

      if (!response.ok) {
        throw new Error(data.detail || `Ошибка ${response.status}: ${text}`);
      }

      const newSessionId = data.session_id || existingSessionId || sessionId || generateSessionId();
      localStorage.setItem(TOKEN_KEY, data.token);
      localStorage.setItem(SESSION_KEY, newSessionId);
      setToken(data.token);
      setSessionId(newSessionId);
      setStatus(data);
      return { ...data, session_id: newSessionId };
    } catch (err) {
      setError(err.message || 'Не удалось начать демо-сессию.');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  const refreshStatus = useCallback(async () => {
    if (!token) return null;
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/demo/status`, {
        headers: { 'X-Demo-Token': token },
      });

      const text = await response.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        data = { detail: text };
      }

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          clearDemo();
        }
        throw new Error(data.detail || `Ошибка ${response.status}`);
      }

      setStatus(data);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    }
  }, [token]);

  const clearDemo = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(SESSION_KEY);
    setToken(null);
    setSessionId(generateSessionId());
    setStatus(null);
    setError(null);
  }, []);

  useEffect(() => {
    if (token) {
      refreshStatus();
      const interval = setInterval(refreshStatus, 5000);
      return () => clearInterval(interval);
    }
  }, [token, refreshStatus]);

  const value = {
    token,
    sessionId,
    status,
    error,
    isLoading,
    isDemoReady: !!token,
    startDemo,
    refreshStatus,
    clearDemo,
  };

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

export default DemoContext;
