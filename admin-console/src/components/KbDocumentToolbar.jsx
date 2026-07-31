import { useState } from 'react';

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

function KbDocumentToolbar({
  status,
  filters,
  onFiltersChange,
  onRefresh,
  onUpload,
  onReindexAll,
  selectedDocument,
  onReindexSelected,
  actionLoading,
}) {
  const [search, setSearch] = useState('');

  const handleSearchChange = (event) => {
    setSearch(event.target.value);
    onFiltersChange({ ...filters, search: event.target.value });
  };

  return (
    <div className="ai-card mb-3">
      <div className="flex flex-col gap-3">
        {/* Top row: status + actions */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-4">
            <div>
              <div className="text-xs text-ai-text-muted uppercase tracking-wide">ACTIVE BACKEND</div>
              <div className="flex items-center gap-2 text-sm font-semibold text-ai-text">
                <span className="ai-status ai-status--ok">CHROMA</span>
                <span className="text-ai-text-secondary font-normal">
                  {status?.indexed_chunks ?? 0} чанков
                </span>
              </div>
            </div>
            <div className="hidden sm:block h-8 w-px bg-ai-border" />
            <div>
              <div className="text-xs text-ai-text-muted uppercase tracking-wide">Embedding model</div>
              <div className="text-sm text-ai-text-secondary">text-embedding-3-small</div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={onUpload}
              className="ai-btn px-3 py-1.5 text-sm"
              type="button"
            >
              + Загрузить файл
            </button>
            <button
              onClick={onReindexSelected}
              disabled={!selectedDocument || actionLoading === 'reindex-selected'}
              className="ai-btn-outline px-3 py-1.5 text-sm"
              type="button"
            >
              {actionLoading === 'reindex-selected' ? '…' : 'Переиндексировать документ'}
            </button>
            <button
              onClick={onReindexAll}
              disabled={actionLoading === 'reindex-all'}
              className="ai-btn-outline px-3 py-1.5 text-sm"
              type="button"
            >
              {actionLoading === 'reindex-all' ? '…' : 'Переиндексировать всё'}
            </button>
            <button
              onClick={onRefresh}
              disabled={actionLoading === 'refresh'}
              className="ai-btn-outline px-3 py-1.5 text-sm"
              type="button"
            >
              {actionLoading === 'refresh' ? '…' : 'Обновить'}
            </button>
          </div>
        </div>

        {/* Bottom row: filters */}
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={filters.status || ''}
            onChange={(event) => onFiltersChange({ ...filters, status: event.target.value })}
            className="ai-select w-auto min-w-[140px]"
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>

          <select
            value={filters.document_type || ''}
            onChange={(event) => onFiltersChange({ ...filters, document_type: event.target.value })}
            className="ai-select w-auto min-w-[140px]"
          >
            {TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>

          <input
            type="text"
            value={search}
            onChange={handleSearchChange}
            placeholder="Поиск по имени файла, статусу, версии..."
            className="ai-input flex-1 min-w-[200px]"
          />
        </div>
      </div>
    </div>
  );
}

export default KbDocumentToolbar;
