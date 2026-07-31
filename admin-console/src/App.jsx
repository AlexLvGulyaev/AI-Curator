import { useState } from 'react';
import useAuth from './hooks/useAuth';
import Login from './components/Login';
import Sidebar from './components/Sidebar';
import ErrorBoundary from './components/ErrorBoundary';
import Dashboard from './components/Dashboard';
import KbDocuments from './components/KbDocuments';
import KbDocumentUpload from './components/KbDocumentUpload';
import KbDocumentDetail from './components/KbDocumentDetail';
import AiConfig from './components/AiConfig';
import AiAndRetrievalConfig from './components/AiAndRetrievalConfig';
import Analytics from './components/Analytics';
import AuditLog from './components/AuditLog';

const KB_VIEWS = {
  list: 'list',
  upload: 'upload',
  detail: 'detail',
};

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
  const { token, isReady, isLoggedIn, login, logout } = useAuth();
  const [activePage, setActivePage] = useState('dashboard');
  const [kbView, setKbView] = useState(KB_VIEWS.list);
  const [selectedDocumentId, setSelectedDocumentId] = useState(null);

  if (!isReady) {
    return null;
  }

  if (!isLoggedIn) {
    return <Login onLogin={login} />;
  }

  const handleSelectKb = () => {
    setActivePage('kb');
    setKbView(KB_VIEWS.list);
    setSelectedDocumentId(null);
  };

  const handleUploadNew = () => {
    setKbView(KB_VIEWS.upload);
  };

  const handleSelectDocument = (doc) => {
    setSelectedDocumentId(doc.id);
    setKbView(KB_VIEWS.detail);
  };

  const handleKbDone = () => {
    setKbView(KB_VIEWS.list);
    setSelectedDocumentId(null);
  };

  const renderContent = () => {
    if (PLACEHOLDER_PAGES.has(activePage)) {
      return <Placeholder page={activePage} />;
    }
    if (activePage === 'dashboard') return <Dashboard />;
    if (activePage === 'kb') {
      if (kbView === KB_VIEWS.upload) {
        return <KbDocumentUpload onDone={handleKbDone} />;
      }
      if (kbView === KB_VIEWS.detail && selectedDocumentId) {
        return <KbDocumentDetail documentId={selectedDocumentId} onBack={handleKbDone} />;
      }
      return <KbDocuments onSelectDocument={handleSelectDocument} onUploadNew={handleUploadNew} />;
    }
    if (activePage === 'ai-config') return <AiAndRetrievalConfig />;
    if (activePage === 'analytics') return <Analytics />;
    if (activePage === 'audit') return <AuditLog />;
    return <Dashboard />;
  };

  return (
    <div className="ai-layout">
      <Sidebar
        active={activePage === 'kb' ? 'kb' : activePage}
        onChange={(page) => {
          if (page === 'kb') {
            handleSelectKb();
          } else {
            setActivePage(page);
          }
        }}
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
