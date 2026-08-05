import { useEffect, useState } from 'react';
import { useDemo } from '../contexts/DemoContext';

function KbDocumentToolbar({
  status,
  selectedDocument,
  onUpload,
  onReindexAll,
  onReindexSelected,
  onEdit,
  onUploadVersion,
  actionLoading,
}) {
  const { isDemo } = useDemo();
  const [backendName, setBackendName] = useState('CHROMA');

  useEffect(() => {
    if (status?.active_retrieval_backend) {
      setBackendName(String(status.active_retrieval_backend).toUpperCase());
    }
  }, [status]);

  const statusClass =
    'inline-flex min-w-[120px] items-center justify-center whitespace-nowrap rounded-ai px-3 py-1.5 text-sm';

  return (
    <div className="ai-card mb-2 py-2 px-3">
      <div className="flex items-start gap-4">
        <div className="flex items-center gap-4 min-w-0 flex-shrink-0">
          <div>
            <div className="text-[0.65rem] text-ai-text-muted uppercase tracking-wide">ACTIVE BACKEND</div>
            <div className="flex items-center gap-2 text-sm font-semibold text-ai-text">
              <span className="ai-status ai-status--ok">{backendName}</span>
              <span className="text-ai-text-secondary font-normal">
                {status?.indexed_chunks ?? 0} чанков
              </span>
            </div>
          </div>
          <div className="hidden sm:block h-8 w-px bg-ai-border flex-shrink-0" />
          <div className="hidden md:block">
            <div className="text-[0.65rem] text-ai-text-muted uppercase tracking-wide">Embedding model</div>
            <div className="text-sm text-ai-text-secondary truncate max-w-[200px]">
              {status?.embedding_model || 'text-embedding-3-small'}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 flex-1">
          <button
            onClick={onUpload}
            disabled={isDemo || actionLoading === 'upload'}
            className={`ai-btn ${statusClass}`}
            type="button"
            title={isDemo ? 'Демо-режим: изменения запрещены' : undefined}
          >
            {actionLoading === 'upload' ? '…' : '+ Загрузить файл'}
          </button>
          <button
            onClick={onUploadVersion}
            disabled={isDemo || !selectedDocument || actionLoading === 'upload-version'}
            className={`ai-btn-outline ${statusClass}`}
            type="button"
            title={isDemo ? 'Демо-режим: изменения запрещены' : undefined}
          >
            {actionLoading === 'upload-version' ? '…' : 'Загрузить версию'}
          </button>
          <button
            onClick={onEdit}
            disabled={isDemo || !selectedDocument || actionLoading === 'edit'}
            className={`ai-btn-outline ${statusClass}`}
            type="button"
            title={isDemo ? 'Демо-режим: изменения запрещены' : undefined}
          >
            {actionLoading === 'edit' ? '…' : 'Редактировать'}
          </button>
          <button
            onClick={onReindexSelected}
            disabled={isDemo || !selectedDocument || actionLoading === 'reindex'}
            className={`ai-btn-outline ${statusClass}`}
            type="button"
            title={isDemo ? 'Демо-режим: изменения запрещены' : undefined}
          >
            {actionLoading === 'reindex' ? '…' : 'Переиндексировать'}
          </button>
          <button
            onClick={onReindexAll}
            disabled={isDemo || actionLoading === 'reindex-all'}
            className={`ai-btn-outline ${statusClass}`}
            type="button"
            title={isDemo ? 'Демо-режим: изменения запрещены' : undefined}
          >
            {actionLoading === 'reindex-all' ? '…' : 'Переиндексировать всё'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default KbDocumentToolbar;
