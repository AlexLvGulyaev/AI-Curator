import { useState } from 'react';

function Login({ onLogin }) {
  const [token, setToken] = useState('');
  const [error, setError] = useState(null);

  const handleSubmit = (event) => {
    event.preventDefault();
    setError(null);
    const trimmed = token.trim();
    if (!trimmed) {
      setError('Введите токен.');
      return;
    }
    onLogin(trimmed);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-ai-bg px-4">
      <div className="ai-card w-full max-w-md p-8">
        <div className="mb-6 text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-ai bg-ai-primary-light text-3xl">
            ⚙️
          </div>
          <h1 className="mb-2 font-display text-2xl font-bold text-ai-text">
            AI Curator Admin Console
          </h1>
          <p className="text-sm text-ai-text-muted">
            Введите Bearer token для доступа к панели управления.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-ai-text-secondary">
              Bearer token
            </label>
            <input
              type="password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              placeholder="Вставьте токен..."
              className="ai-input w-full px-4 py-3"
            />
          </div>

          {error && (
            <div className="rounded-ai border border-ai-error/20 bg-red-500/10 p-3 text-sm text-ai-error">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="ai-btn w-full px-4 py-3"
          >
            Войти
          </button>
        </form>
      </div>
    </div>
  );
}

export default Login;
