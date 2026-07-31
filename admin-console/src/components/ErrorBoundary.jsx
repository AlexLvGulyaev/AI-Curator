import { Component } from 'react';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen items-center justify-center bg-ai-bg p-6 text-ai-text">
          <div className="ai-card max-w-lg p-6">
            <p className="text-4xl mb-4">💥</p>
            <h1 className="font-display text-lg font-semibold mb-2">Ошибка интерфейса</h1>
            <p className="text-sm text-ai-text-secondary mb-4">
              Что-то пошло не так при отображении панели. Попробуйте обновить страницу.
            </p>
            {this.state.error && (
              <pre className="rounded-ai bg-ai-input p-3 text-xs text-ai-error overflow-auto max-h-48">
                {this.state.error.toString()}
              </pre>
            )}
            <button
              onClick={() => window.location.reload()}
              className="ai-btn mt-4 px-4 py-2 text-sm"
            >
              Обновить страницу
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
