import { useEffect, useMemo, useRef, useState } from 'react';
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

const STATUS_OPTIONS = [
  { value: '', label: 'Все статусы' },
  { value: 'draft', label: 'Черновик' },
  { value: 'pending', label: 'В ожидании' },
  { value: 'processing', label: 'Обработка' },
  { value: 'indexed', label: 'Индексирован' },
  { value: 'error', label: 'Ошибка' },
  { value: 'archived', label: 'Архив' },
];

const TYPE_OPTIONS = [
  { value: '', label: 'Все типы' },
  { value: 'lecture', label: 'Лекция' },
  { value: 'methodical', label: 'Методичка' },
  { value: 'faq', label: 'FAQ' },
  { value: 'instruction', label: 'Инструкция' },
  { value: 'glossary', label: 'Глоссарий' },
  { value: 'example', label: 'Пример' },
  { value: 'external', label: 'Внешний ресурс' },
];

function StatusBadge({ status }) {
  const variant = STATUS_VARIANTS[status] || 'muted';
  const label = STATUSES[status] || status;
  return <span className={`ai-status ai-status--${variant}`}>{label}</span>;
}

function KbDocumentList({ filters, onFiltersChange, selectedDocument, onSelectDocument, refreshTick }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 7;
  const listRef = useRef(null);
  const pendingListFocusRef = useRef(false);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
      const t = e.target;
      if (t && (t.closest('input') || t.closest('textarea') || t.closest('select') || t.isContentEditable)) {
        return;
      }
      if (!filteredDocuments.length) return;
      const absIdx = selectedDocument
        ? filteredDocuments.findIndex((d) => String(d.id) === String(selectedDocument.id))
        : 0;
      if (absIdx < 0) return;
      const nextAbsIdx =
        e.key === 'ArrowDown'
          ? Math.min(filteredDocuments.length - 1, absIdx + 1)
          : Math.max(0, absIdx - 1);
      if (nextAbsIdx === absIdx) return;
      e.preventDefault();
      const next = filteredDocuments[nextAbsIdx];
      if (!next?.id) return;
      pendingListFocusRef.current = true;
      setPage(Math.floor(nextAbsIdx / PAGE_SIZE) + 1);
      onSelectDocument(next);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDocument, filters.search, filters.status, filters.document_type]);

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

  // Auto-focus on first document when list loads and nothing is selected
  useEffect(() => {
    if (!selectedDocument && paginatedDocuments.length > 0) {
      onSelectDocument(paginatedDocuments[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paginatedDocuments.map((d) => d.id).join(','), selectedDocument?.id]);

  useEffect(() => {
    if (!selectedDocument?.id) return;
    const list = listRef.current;
    if (!list) return;
    const safeId =
      typeof CSS !== 'undefined' && typeof CSS.escape === 'function'
        ? CSS.escape(String(selectedDocument.id))
        : String(selectedDocument.id).replace(/"/g, '\\"');
    const row = list.querySelector(`[data-doc-id="${safeId}"]`);
    if (!row) return;
    row.scrollIntoView({ block: 'nearest' });
    const listHasFocus = document.activeElement instanceof Node && list.contains(document.activeElement);
    const shouldFocus = pendingListFocusRef.current || listHasFocus;
    pendingListFocusRef.current = false;
    if (!shouldFocus) return;
    const id = window.requestAnimationFrame(() => {
      row.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(id);
  }, [selectedDocument?.id, page]);

  const handleSearchChange = (event) => {
    onFiltersChange({ ...filters, search: event.target.value });
  };

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
    <div className="ai-card flex h-full flex-col overflow-hidden p-3">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <select
          value={filters.status || ''}
          onChange={(event) => onFiltersChange({ ...filters, status: event.target.value })}
          className="ai-select w-auto min-w-[130px]"
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
        <select
          value={filters.document_type || ''}
          onChange={(event) => onFiltersChange({ ...filters, document_type: event.target.value })}
          className="ai-select w-auto min-w-[130px]"
        >
          {TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </div>

      {/* Search */}
      <input
        type="text"
        value={filters.search || ''}
        onChange={handleSearchChange}
        placeholder="Поиск по имени файла, статусу, версии..."
        className="ai-input w-full mb-2"
      />

      {/* Pagination on top */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-b border-ai-border pb-2 mb-2 text-xs">
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

      {/* Document list */}
      <div className="flex-1 overflow-y-auto pr-1 min-h-0" ref={listRef}>
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
                  data-doc-id={doc.id}
                  onClick={() => onSelectDocument(doc)}
                  className={`text-left rounded-ai border p-2 transition-colors ${
                    isSelected
                      ? 'border-ai-primary bg-ai-primary-light'
                      : 'border-ai-border bg-ai-surface hover:border-ai-primary'
                  }`}
                  type="button"
                >
                  {/* Row 1: date + status */}
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs text-ai-text-muted">
                      {new Date(doc.created_at).toLocaleString('ru-RU')}
                    </span>
                    <StatusBadge status={doc.status} />
                  </div>
                  {/* Row 2: file name */}
                  <div className="text-sm font-medium text-ai-text line-clamp-2 mb-1">
                    {doc.title}
                  </div>
                  {/* Row 3: version / chunks / embedding */}
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-ai-text-secondary">
                    <span>v{activeVersion?.version_number || '?'}</span>
                    <span>·</span>
                    <span>{activeVersion?.chunk_count || 0} чанков</span>
                    <span>·</span>
                    <span className="truncate max-w-[120px]">
                      {activeVersion?.embedding_model || '—'}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default KbDocumentList;
