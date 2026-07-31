import { useEffect, useMemo, useState } from 'react';
import { listKbDocuments } from '../api/backend';

const STATUSES = {
  draft: 'Черновик',
  pending: 'В ожидании',
  processing: 'Обработка',
  indexed: 'Индексирован',
  error: 'Ошибка',
  archived: 'Архив',
};

const STATUS_VARIANTS = {
  draft: 'muted',
  pending: 'info',
  processing: 'warning',
  indexed: 'ok',
  error: 'error',
  archived: 'muted',
};

function StatusBadge({ status }) {
  const variant = STATUS_VARIANTS[status] || 'muted';
  const label = STATUSES[status] || status;
  return <span className={`ai-status ai-status--${variant}`}>{label}</span>;
}

function KbDocumentList({ filters, selectedDocument, onSelectDocument, refreshTick }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 10;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = { limit: 500 };
      if (filters.status) params.status = filters.status;
      if (filters.document_type) params.document_type = filters.document_type;
      const data = await listKbDocuments(params);
      setDocuments(data);
      setPage(1);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.status, filters.document_type, refreshTick]);

  const filteredDocuments = useMemo(() => {
    const search = (filters.search || '').toLowerCase();
    if (!search) return documents;
    return documents.filter((doc) =>
      [doc.title, doc.document_type, doc.status, String(doc.id)]
        .filter(Boolean)
        .some((field) => field.toLowerCase().includes(search))
    );
  }, [documents, filters.search]);

  const totalPages = Math.max(1, Math.ceil(filteredDocuments.length / PAGE_SIZE));
  const paginatedDocuments = filteredDocuments.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  if (loading) {
    return (
      <div className="ai-card flex h-full items-center justify-center p-4">
        <span className="mr-2 inline-block animate-pulse">●</span>
        Загрузка документов…
      </div>
    );
  }

  if (error) {
    return (
      <div className="ai-card h-full p-4">
        <div className="ai-error text-sm">{error}</div>
      </div>
    );
  }

  return (
    <div className="ai-card flex h-full flex-col overflow-hidden">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="ai-section__title">Документы</h3>
        <span className="text-xs text-ai-text-muted">
          {filteredDocuments.length} документов
        </span>
      </div>

      <div className="flex-1 overflow-y-auto pr-1">
        {paginatedDocuments.length === 0 ? (
          <div className="ai-empty py-8">Документы не найдены.</div>
        ) : (
          <div className="flex flex-col gap-2">
            {paginatedDocuments.map((doc) => {
              const activeVersion = doc.versions?.find((v) => v.id === doc.active_version_id);
              const isSelected = selectedDocument?.id === doc.id;
              return (
                <button
                  key={doc.id}
                  onClick={() => onSelectDocument(doc)}
                  className={`text-left rounded-ai border p-3 transition-colors ${
                    isSelected
                      ? 'border-ai-primary bg-ai-primary-light'
                      : 'border-ai-border bg-ai-surface hover:border-ai-primary'
                  }`}
                  type="button"
                >
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <StatusBadge status={doc.status} />
                    <span className="text-xs text-ai-text-muted">
                      {new Date(doc.created_at).toLocaleDateString('ru-RU')}
                    </span>
                  </div>
                  <div className="mb-1 text-sm font-medium text-ai-text line-clamp-2">
                    {doc.title}
                  </div>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ai-text-secondary">
                    <span className="capitalize">{doc.document_type}</span>
                    <span>{doc.difficulty}</span>
                    <span>
                      v{activeVersion?.version_number || '?'} · {activeVersion?.chunk_count || 0} чанков
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="mt-3 flex items-center justify-between border-t border-ai-border pt-2 text-xs">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="ai-btn-outline px-2 py-1"
            type="button"
          >
            ← Назад
          </button>
          <span className="text-ai-text-secondary">
            Страница {page} из {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="ai-btn-outline px-2 py-1"
            type="button"
          >
            Вперёд →
          </button>
        </div>
      )}
    </div>
  );
}

export default KbDocumentList;
