import { useEffect, useState } from 'react';
import KbDocumentToolbar from './KbDocumentToolbar';
import KbDocumentList from './KbDocumentList';
import KbDocumentSummary from './KbDocumentSummary';
import KbDocumentLifecycle from './KbDocumentLifecycle';
import KbDocumentUpload from './KbDocumentUpload';
import KbDocumentEditModal from './KbDocumentEditModal';
import KbDocumentTextEditor from './KbDocumentTextEditor';
import {
  getKbStatus,
  reindexAllKbDocuments,
  reindexKbDocument,
} from '../api/backend';

function KbDocuments() {
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [filters, setFilters] = useState({
    status: '',
    document_type: '',
    search: '',
  });
  const [status, setStatus] = useState(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [actionLoading, setActionLoading] = useState(null);
  const [error, setError] = useState(null);
  const [showUpload, setShowUpload] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [showVersionUpload, setShowVersionUpload] = useState(false);
  const [textEditor, setTextEditor] = useState(null);

  async function refreshStatus() {
    try {
      const data = await getKbStatus();
      setStatus(data);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleRefresh() {
    setActionLoading('refresh');
    setError(null);
    try {
      await refreshStatus();
      setRefreshTick((t) => t + 1);
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReindexAll() {
    setActionLoading('reindex-all');
    setError(null);
    try {
      await reindexAllKbDocuments();
      setRefreshTick((t) => t + 1);
      await refreshStatus();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReindexSelected() {
    if (!selectedDocument) return;
    setActionLoading('reindex');
    setError(null);
    try {
      await reindexKbDocument(selectedDocument.id);
      setRefreshTick((t) => t + 1);
      await refreshStatus();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  }

  const handleUpload = () => {
    setShowUpload(true);
  };

  const handleUploadDone = () => {
    setShowUpload(false);
    setRefreshTick((t) => t + 1);
    refreshStatus();
  };

  const handleEditDone = () => {
    setShowEdit(false);
    setRefreshTick((t) => t + 1);
    refreshStatus();
  };

  const handleVersionUploadDone = () => {
    setShowVersionUpload(false);
    setRefreshTick((t) => t + 1);
    refreshStatus();
  };

  const handleOpenTextEditor = ({ stage }) => {
    if (!selectedDocument) return;
    setTextEditor({
      documentId: selectedDocument.id,
      versionId: selectedDocument.active_version_id || selectedDocument.id,
      stage,
    });
  };

  const handleTextEditorDone = () => {
    setTextEditor(null);
    setRefreshTick((t) => t + 1);
    refreshStatus();
  };

  useEffect(() => {
    refreshStatus();
  }, []);

  if (showUpload) {
    return (
      <div className="ai-config-page">
        <KbDocumentUpload mode="document" onDone={handleUploadDone} />
      </div>
    );
  }

  return (
    <div className="ai-config-page">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-base font-semibold text-ai-text">База знаний. Документы</h2>
        <button
          onClick={handleRefresh}
          disabled={actionLoading === 'refresh'}
          className="ai-btn-outline rounded-ai px-3 py-1.5 text-sm"
          type="button"
        >
          {actionLoading === 'refresh' ? '…' : 'Обновить'}
        </button>
      </div>

      <KbDocumentToolbar
        status={status}
        selectedDocument={selectedDocument}
        onUpload={handleUpload}
        onUploadVersion={() => setShowVersionUpload(true)}
        onEdit={() => setShowEdit(true)}
        onReindexSelected={handleReindexSelected}
        onReindexAll={handleReindexAll}
        actionLoading={actionLoading}
      />

      {error && (
        <div className="ai-error mb-3 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 min-h-0 flex-1">
        <div className="lg:col-span-3 min-h-0">
          <KbDocumentList
            filters={filters}
            onFiltersChange={setFilters}
            selectedDocument={selectedDocument}
            onSelectDocument={setSelectedDocument}
            refreshTick={refreshTick}
          />
        </div>

        <div className="lg:col-span-6 min-h-0">
          <KbDocumentSummary
            documentId={selectedDocument?.id}
            onAction={() => {
              setRefreshTick((t) => t + 1);
              refreshStatus();
            }}
            onOpenTextEditor={handleOpenTextEditor}
          />
        </div>

        <div className="lg:col-span-3 min-h-0">
          <KbDocumentLifecycle documentId={selectedDocument?.id} />
        </div>
      </div>

      {showEdit && selectedDocument && (
        <KbDocumentEditModal
          document={selectedDocument}
          onDone={handleEditDone}
          onCancel={() => setShowEdit(false)}
        />
      )}

      {showVersionUpload && selectedDocument && (
        <KbDocumentUpload
          mode="version"
          documentId={selectedDocument.id}
          onDone={handleVersionUploadDone}
        />
      )}

      {textEditor && (
        <KbDocumentTextEditor
          documentId={textEditor.documentId}
          versionId={textEditor.versionId}
          stage={textEditor.stage}
          onDone={handleTextEditorDone}
          onCancel={() => setTextEditor(null)}
        />
      )}
    </div>
  );
}

export default KbDocuments;
