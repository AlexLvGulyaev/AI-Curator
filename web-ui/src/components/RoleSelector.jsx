import { useState } from 'react';
import useDemo from '../hooks/useDemo';

const ROLES = [
  {
    id: 'active_student',
    title: 'Активный студент',
    description: 'Вы вовлечены в курс, выполняете задания вовремя и хотите углубить знания.',
    icon: '🚀',
    accent: 'bg-ai-primary-light text-ai-primary',
  },
  {
    id: 'late_student',
    title: 'Отстающий студент',
    description: 'Вы пропустили несколько дедлайнов и хотите наверстать упущенное.',
    icon: '⏰',
    accent: 'bg-orange-100 text-orange-600',
  },
  {
    id: 'new_student',
    title: 'Новый студент',
    description: 'Вы только начинаете курс и хотите разобраться, с чего начать.',
    icon: '🌱',
    accent: 'bg-ai-teal-light text-ai-teal',
  },
];

function RoleSelector({ onSelectRole }) {
  const { isDemoReady, isLoading, error, startDemo } = useDemo();
  const [startError, setStartError] = useState(null);

  const handleStartDemo = async () => {
    setStartError(null);
    try {
      await startDemo();
    } catch (err) {
      setStartError(err.message || 'Не удалось начать демо-сессию.');
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-12 bg-ai-bg">
      <div className="mb-10 text-center">
        <div className="mb-4 inline-flex items-center justify-center w-16 h-16 rounded-ai bg-ai-primary-light text-3xl">
          🤖
        </div>
        <h1 className="mb-2 text-4xl font-bold font-display text-ai-text">
          AI Curator
        </h1>
        <p className="text-ai-text-secondary max-w-md mx-auto">
          Цифровой наставник для студентов. Начните безопасную демо-сессию, чтобы задать вопросы по курсу.
        </p>
      </div>

      {!isDemoReady ? (
        <div className="w-full max-w-md text-center">
          <button
            onClick={handleStartDemo}
            disabled={isLoading}
            className="ai-btn w-full px-6 py-4 text-base font-medium disabled:opacity-60"
          >
            {isLoading ? 'Запуск демо-сессии…' : '🔒 Начать демо-сессию'}
          </button>
          <p className="mt-4 text-sm text-ai-text-muted">
            Демо-режим ограничен: 20 запросов за 30 минут. Без пароля, без доступа к вашим данным.
          </p>
          {(startError || error) && (
            <div className="mt-4 rounded-ai border border-ai-error/20 bg-red-50 p-3 text-sm text-ai-error">
              {startError || error}
            </div>
          )}
        </div>
      ) : (
        <>
          <div className="grid w-full max-w-3xl gap-5 sm:grid-cols-1 md:grid-cols-3">
            {ROLES.map((role) => (
              <button
                key={role.id}
                onClick={() => onSelectRole(role.id)}
                className="ai-card group flex flex-col items-start p-6 text-left transition hover:border-ai-primary hover:shadow-ai-lg focus:outline-none focus:ring-2 focus:ring-ai-primary focus:ring-offset-2"
              >
                <span
                  className={`mb-4 inline-flex items-center justify-center w-12 h-12 rounded-ai text-2xl ${role.accent} transition group-hover:scale-110`}
                  role="img"
                  aria-label={role.title}
                >
                  {role.icon}
                </span>
                <h2 className="mb-2 text-lg font-semibold font-display text-ai-text">
                  {role.title}
                </h2>
                <p className="text-sm text-ai-text-secondary leading-relaxed">
                  {role.description}
                </p>
              </button>
            ))}
          </div>

          <p className="mt-10 max-w-md text-center text-xs text-ai-text-muted">
            Демо-режим без пароля. Роль сохраняется в браузере и используется для персонализации примеров прогресса и дедлайнов.
          </p>
        </>
      )}
    </div>
  );
}

export default RoleSelector;
