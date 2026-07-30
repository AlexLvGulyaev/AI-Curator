import { useCallback, useEffect, useState } from 'react';
import { sendChatMessage } from '../api/backend';

const GREETING = {
  role: 'assistant',
  content:
    'Привет! Я AI Curator. Задайте вопрос по курсу — я найду ответ в учебных материалах, проверю дедлайны и прогресс.',
  sources: [],
};

function storageKey(role) {
  return `ai-curator-messages-${role || 'guest'}`;
}

function getSessionId() {
  let id = localStorage.getItem('ai-curator-session-id');
  if (!id) {
    id = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    localStorage.setItem('ai-curator-session-id', id);
  }
  return id;
}

function loadMessages(role) {
  try {
    const raw = localStorage.getItem(storageKey(role));
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
    }
  } catch {
    // Ignore corrupted storage
  }
  return [GREETING];
}

function saveMessages(role, messages) {
  try {
    localStorage.setItem(storageKey(role), JSON.stringify(messages));
  } catch {
    // Storage may be unavailable
  }
}

function useChat({ role, courseId, difficulty }) {
  const [messages, setMessages] = useState(() => loadMessages(role));
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId] = useState(() => getSessionId());

  useEffect(() => {
    saveMessages(role, messages);
  }, [role, messages]);

  const sendMessage = useCallback(
    async (text) => {
      setError(null);
      setMessages((prev) => [...prev, { role: 'user', content: text }]);
      setIsLoading(true);

      try {
        const history = messages.slice(-6).map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const response = await sendChatMessage({
          message: text,
          role,
          difficulty,
          courseId,
          history,
          sessionId,
        });

        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: response.answer,
            sources: response.sources || [],
            meta: response.model
              ? `Модель: ${response.model} · Намерение: ${response.intent || '—'} · ${Math.round(response.latency_ms || 0)} мс`
              : null,
          },
        ]);
      } catch (err) {
        setError(err.message || 'Не удалось получить ответ от AI Curator.');
      } finally {
        setIsLoading(false);
      }
    },
    [role, courseId, difficulty, messages, sessionId]
  );

  const clearMessages = useCallback(() => {
    setMessages([GREETING]);
    setError(null);
  }, []);

  return { messages, isLoading, error, sendMessage, clearMessages };
}

export default useChat;
