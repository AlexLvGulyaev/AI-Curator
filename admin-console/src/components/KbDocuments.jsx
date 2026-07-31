import { useState } from 'react';
import KbDocumentToolbar from './KbDocumentToolbar';
import KbDocumentList from './KbDocumentList';
import KbDocumentSummary from './KbDocumentSummary';
import KbDocumentLifecycle from './KbDocumentLifecycle';
import KbDocumentUpload from './KbDocumentUpload';
import {
  getKbStatus,
  reindexAllKbDocuments,
  reindexKbDocument,
} from '../api/backend';

function KbDocuments({ onUploadNew }) {
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
    setActionLoading('reindex-selected');
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
    onUploadNew?.();
  };

  if (showUpload) {
    return (
      <div className="ai-config-page">
        <KbDocumentUpload onDone={handleUploadDone} />
      </div>
    );
  }

  return (
    <div className="ai-config-page">
      <KbDocumentToolbar
        status={status}
        filters={filters}
        onFiltersChange={setFilters}
        onRefresh={handleRefresh}
        onUpload={handleUpload}
        onReindexAll={handleReindexAll}
        selectedDocument={selectedDocument}
        onReindexSelected={handleReindexSelected}
        actionLoading={actionLoading}
      />

      {error && (
        <div className="ai-error mb-3 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 min-h-0 flex-1">
        <div className="lg:col-span-3 min-h-0">
          <KbDocumentList
            filters={filters}
            selectedDocument={selectedDocument}
            onSelectDocument={setSelectedDocument}
            refreshTick={refreshTick}
          />
        </div>

        <div className="lg:col-span-5 min-h-0">
          <KbDocumentSummary
            documentId={selectedDocument?.id}
            onAction={() => {
              setRefreshTick((t) => t + 1);
              refreshStatus();
            }}
          />
        </div>

        <div className="lg:col-span-4 min-h-0">
          <KbDocumentLifecycle documentId={selectedDocument?.id} />
        </div>
      </div>
    </div>
  );
}

export default KbDocuments;
