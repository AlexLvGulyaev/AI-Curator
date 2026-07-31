import { useEffect, useState } from 'react';
import { getKbDocumentTimeline } from '../api/backend';

const STATUS_VARIANTS = {
  success: 'ok',
  error: 'error',
  pending: 'warning',
};

const EVENT_ICONS = {
  upload: '↑',
  preprocess_start: '⚙',
  preprocess_done: '⚙',
  preprocess_error: '⚙',
  index_start: '🔍',
  index_done: '🔍',
  index_error: '🔍',
  reindex_start: '↻',
  reindex_done: '↻',
  reindex_error: '↻',
  publish: '📢',
  unpublish: '🔕',
  metadata_update: '✎',
  version_activate: '▶',
  delete: '🗑',
  error: '⚠',
};

const EVENT_TYPE_LABELS = {
  upload: 'Загрузка документа',
  preprocess_start: 'Preprocessing',
  preprocess_done: 'Preprocessing',
  preprocess_error: 'Ошибка preprocessing',
  index_start: 'Индексация',
  index_done: 'Индексация',
  index_error: 'Ошибка индексации',
  reindex_start: 'Переиндексация',
  reindex_done: 'Переиндексация',
  reindex_error: 'Ошибка переиндексации',
  publish: 'Публикация',
  unpublish: 'Снятие публикации',
  metadata_update: 'Обновление метаданных',
  version_activate: 'Активация версии',
  delete: 'Удаление',
  error: 'Ошибка',
};

function StatusBadge({ status }) {
  const variant = STATUS_VARIANTS[status] || 'muted';
  return (
    <span className={`ai-status ai-status--${variant}`}>
      {status === 'success' ? 'УСПЕХ' : status === 'error' ? 'ОШИБКА' : 'В ПРОЦЕССЕ'}
    </span>
  );
}

function formatDuration(ms) {
  if (ms === null || ms === undefined) return null;
  if (ms < 1000) return `${ms} мс`;
  if (ms < 60000) return `${Math.round(ms / 100) / 10} с`;
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.round((ms % 60000) / 1000);
  return `${minutes} м${seconds ? ` ${seconds} с` : ''}`;
}

function KbDocumentLifecycle({ documentId }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedEventId, setExpandedEventId] = useState(null);

  async function load() {
    if (!documentId) {
      setEvents([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getKbDocumentTimeline(documentId, 100);
      setEvents(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  if (loading) {
    return (
      <div className="ai-card flex h-full items-center justify-center p-4">
        <span className="mr-2 inline-block animate-pulse">●</span>
        Загрузка lifecycle…
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
    <div className="ai-card flex h-full flex-col overflow-hidden p-1.5">
      <div className="mb-1.5 border-b border-ai-border pb-1.5">
        <h3 className="ai-section__title">ЖИЗНЕННЫЙ ЦИКЛ</h3>
      </div>

      <div className="flex-1 overflow-y-auto pr-1">
        {events.length === 0 ? (
          <div className="ai-empty py-8 text-xs">Событий пока нет.</div>
        ) : (
          <div className="flex flex-col gap-1">
            {events.map((event) => {
              const isExpanded = expandedEventId === event.id;
              const duration = formatDuration(event.duration_ms);
              const icon = EVENT_ICONS[event.event_type] || '•';
              const label = EVENT_TYPE_LABELS[event.event_type] || event.event_type;
              return (
                <div
                  key={event.id}
                  className="rounded-ai border border-ai-border bg-ai-surface text-xs"
                >
                  <div className="flex items-center justify-between gap-2 px-1.5 py-0.5 border-b border-ai-border-subtle">
                    <span className="text-ai-text-muted whitespace-nowrap">
                      {new Date(event.created_at).toLocaleString('ru-RU')}
                    </span>
                    <div className="flex items-center gap-1.5 whitespace-nowrap">
                      <StatusBadge status={event.status} />
                      {duration && (
                        <span className="text-ai-text-muted">{duration}</span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-start gap-1.5 px-1.5 py-0.5">
                    <span className="mt-0.5 text-ai-text-secondary w-4 text-center flex-shrink-0">{icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-ai-text truncate">{label}</div>
                      {event.message && event.message !== label && (
                        <div className="text-ai-text-secondary truncate" title={event.message}>
                          {event.message}
                        </div>
                      )}
                    </div>
                  </div>

                  {event.details && Object.keys(event.details).length > 0 && (
                    <div className="border-t border-ai-border-subtle">
                      <button
                        onClick={() => setExpandedEventId(isExpanded ? null : event.id)}
                        className="flex w-full items-center gap-1 px-1.5 py-0.5 text-ai-primary hover:underline text-xs"
                        type="button"
                      >
                        <span>{isExpanded ? '▼' : '▶'}</span>
                        <span>
                          {isExpanded ? 'Скрыть снимок' : 'Технический снимок'}
                        </span>
                      </button>
                      {isExpanded && (
                        <pre className="ai-code-preview m-1 min-h-[60px]">
                          {JSON.stringify(event.details, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default KbDocumentLifecycle;
