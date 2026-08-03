import { useState, useEffect } from 'react';
import useChat from '../hooks/useChat';
import DifficultyToggle from './DifficultyToggle';
import Message from './Message';
import { checkBackendStatus } from '../api/backend';

const ROLE_COURSES = {
  active_student: [
    { id: 3, name: 'Claude Code: от знакомства до автоматизации' },
    { id: 4, name: 'Промпт-инжиниринг' },
  ],
  late_student: [{ id: 3, name: 'Claude Code: от знакомства до автоматизации' }],
  new_student: [{ id: 3, name: 'Claude Code: от знакомства до автоматизации' }],
};

function Chat({ role, onChangeRole }) {
  const courses = ROLE_COURSES[role] || ROLE_COURSES.active_student;
  const [courseId, setCourseId] = useState(courses[0]?.id);
  const [input, setInput] = useState('');
  const [difficulty, setDifficulty] = useState('beginner');
  const [backendOnline, setBackendOnline] = useState(null);
  const { messages, isLoading, error, sendMessage, clearMessages } = useChat({
    role,
    courseId,
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

  useEffect(() => {
    clearMessages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId, difficulty]);

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
          {courses.length > 1 && (
            <select
              value={courseId}
              onChange={(e) => setCourseId(Number(e.target.value))}
              className="rounded-ai border border-ai-border bg-ai-surface px-3 py-1.5 text-sm text-ai-text focus:outline-none focus:ring-2 focus:ring-ai-primary"
            >
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          )}
          <DifficultyToggle value={difficulty} onChange={setDifficulty} />
          <button
            onClick={clearMessages}
            className="rounded-ai px-3 py-1.5 text-sm font-medium text-ai-text-secondary hover:bg-ai-surface-hover"
            title="Начать новый диалог"
          >
            Новый диалог
          </button>
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
