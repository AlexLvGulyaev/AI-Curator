import { useState } from 'react';
import useAuth from './hooks/useAuth';
import Login from './components/Login';
import Sidebar from './components/Sidebar';
import ErrorBoundary from './components/ErrorBoundary';
import Dashboard from './components/Dashboard';
import KbDocuments from './components/KbDocuments';
import AiAndRetrievalConfig from './components/AiAndRetrievalConfig';
import Analytics from './components/Analytics';
import AuditLog from './components/AuditLog';

const PLACEHOLDER_PAGES = new Set(['logs', 'dialogs', 'reports']);

function Placeholder({ page }) {
  return (
    <div className="flex h-full items-center justify-center text-ai-text-muted">
      <div className="text-center">
        <p className="text-4xl mb-4">🚧</p>
        <p className="text-lg font-semibold">В разработке</p>
        <p className="text-sm mt-2">Панель «{page}» будет реализована в следующем спринте.</p>
      </div>
    </div>
  );
}

function App() {
  const { isReady, isLoggedIn, login, logout } = useAuth();
  const [activePage, setActivePage] = useState('dashboard');

  if (!isReady) {
    return null;
  }

  if (!isLoggedIn) {
    return <Login onLogin={login} />;
  }

  const renderContent = () => {
    if (PLACEHOLDER_PAGES.has(activePage)) {
      return <Placeholder page={activePage} />;
    }
    if (activePage === 'dashboard') return <Dashboard />;
    if (activePage === 'kb') return <KbDocuments />;
    if (activePage === 'ai-config') return <AiAndRetrievalConfig />;
    if (activePage === 'analytics') return <Analytics />;
    if (activePage === 'audit') return <AuditLog />;
    return <Dashboard />;
  };

  return (
    <div className="ai-layout">
      <Sidebar
        active={activePage === 'kb' ? 'kb' : activePage}
        onChange={setActivePage}
        onLogout={logout}
      />
      <div className="ai-main">
        <div className="ai-header__wrapper">
          <header className="ai-header">
            <div>
              <div className="ai-header__title">Admin Console</div>
              <div className="ai-header__subtitle">FastAPI · консоль наблюдаемости</div>
            </div>
            <div className="ai-header__brand">Zerocoder</div>
          </header>
        </div>
        <main className="ai-content">
          <ErrorBoundary key={activePage}>
            {renderContent()}
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}

export default App;
