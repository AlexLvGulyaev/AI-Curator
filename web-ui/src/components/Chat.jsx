import { useState, useEffect } from 'react';
import useChat from '../hooks/useChat';
import DifficultyToggle from './DifficultyToggle';
import Message from './Message';
import { checkBackendStatus } from '../api/backend';

const DEMO_COURSE_ID = 3;

function Chat({ role, onChangeRole }) {
  const [input, setInput] = useState('');
  const [difficulty, setDifficulty] = useState('beginner');
  const [backendOnline, setBackendOnline] = useState(null);
  const { messages, isLoading, error, sendMessage } = useChat({
    role,
    courseId: DEMO_COURSE_ID,
    difficulty,
  });

  useEffect(() => {
    let mounted = true;
    checkBackendStatus().then((online) => {
      if (mounted) setBackendOnline(online);
    });
    return () => {
      mounted = false;
    };
  }, []);

  const handleSubmit = (event) => {
    event.preventDefault();
    const text = input.trim();
    if (!text || isLoading) return;
    setInput('');
    sendMessage(text);
  };

  const roleTitles = {
    active_student: 'Активный студент',
    late_student: 'Отстающий студент',
    new_student: 'Новый студент',
  };

  return (
    <div className="flex h-screen flex-col bg-ai-bg">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-ai-border bg-ai-surface px-4 py-3 shadow-ai">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-ai bg-ai-primary-light text-lg">
            🤖
          </div>
          <div>
            <h1 className="font-display text-lg font-bold text-ai-text">AI Curator</h1>
            <div className="flex items-center gap-2">
              <span
                className={`status-dot ${
                  backendOnline === null
                    ? ''
                    : backendOnline
                    ? 'online'
                    : 'error'
                }`}
              />
              <span className="text-xs text-ai-text-muted">
                {backendOnline === null
                  ? 'Проверка статуса…'
                  : backendOnline
                  ? 'Backend онлайн'
                  : 'Backend недоступен'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="hidden rounded-full bg-ai-primary-light px-3 py-1 text-xs font-medium text-ai-primary sm:inline-block">
            {roleTitles[role] || role}
          </span>
          <DifficultyToggle value={difficulty} onChange={setDifficulty} />
          <button
            onClick={onChangeRole}
            className="rounded-ai px-3 py-1.5 text-sm font-medium text-ai-text-secondary hover:bg-ai-surface-hover"
          >
            Сменить роль
          </button>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto flex max-w-3xl flex-col gap-5">
          {messages.map((message, index) => (
            <Message key={index} message={message} />
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="ai-card px-5 py-4 text-sm text-ai-text-muted">
                <span className="mr-2 inline-block animate-pulse">●</span>
                AI Curator думает…
              </div>
            </div>
          )}
          {error && (
            <div className="rounded-ai border border-ai-error/20 bg-red-50 p-4 text-sm text-ai-error">
              {error}
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-ai-border bg-ai-surface px-4 py-4"
      >
        <div className="mx-auto flex max-w-3xl gap-3">
          <input
            type="text"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Задайте вопрос по курсу…"
            className="ai-input flex-1 px-4 py-3 text-sm"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="ai-btn px-5 py-3 text-sm font-medium"
          >
            Отправить
          </button>
        </div>
      </form>
    </div>
  );
}

export default Chat;
