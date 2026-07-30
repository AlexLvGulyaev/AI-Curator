import { useState } from 'react';
import useAuth from './hooks/useAuth';
import Login from './components/Login';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import KbDocuments from './components/KbDocuments';
import KbDocumentUpload from './components/KbDocumentUpload';
import KbDocumentDetail from './components/KbDocumentDetail';
import AiConfig from './components/AiConfig';
import Analytics from './components/Analytics';
import AuditLog from './components/AuditLog';

const KB_VIEWS = {
  list: 'list',
  upload: 'upload',
  detail: 'detail',
};

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
    if (activePage === 'ai-config') return <AiConfig />;
    if (activePage === 'analytics') return <Analytics />;
    if (activePage === 'audit') return <AuditLog />;
    return <Dashboard />;
  };

  return (
    <div className="flex h-screen bg-ai-bg">
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
      <main className="flex-1 overflow-y-auto">
        {renderContent()}
      </main>
    </div>
  );
}

export default App;
