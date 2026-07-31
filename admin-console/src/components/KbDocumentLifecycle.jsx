import { useEffect, useState } from 'react';
import { getKbDocumentTimeline } from '../api/backend';

const EVENT_ICONS = {
  upload: '📤',
  preprocess_start: '⚙️',
  preprocess_done: '✅',
  preprocess_error: '❌',
  index_start: '🔍',
  index_done: '✅',
  index_error: '❌',
  reindex_start: '🔄',
  reindex_done: '✅',
  reindex_error: '❌',
  publish: '📢',
  unpublish: '🔕',
  metadata_update: '✏️',
  version_activate: '▶️',
  delete: '🗑️',
  error: '❌',
};

const STATUS_VARIANTS = {
  success: 'ok',
  error: 'error',
  pending: 'warning',
};

function StatusBadge({ status }) {
  const variant = STATUS_VARIANTS[status] || 'muted';
  return (
    <span className={`ai-status ai-status--${variant}`}>
      {status === 'success' ? 'УСПЕХ' : status === 'error' ? 'ОШИБКА' : 'В ПРОЦЕССЕ'}
    </span>
  );
}

function KbDocumentLifecycle({ documentId }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);

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
    <div className="ai-card flex h-full flex-col overflow-hidden">
      <div className="mb-3">
        <h3 className="ai-section__title">ЖИЗНЕННЫЙ ЦИКЛ</h3>
        <p className="ai-section__subtitle">Хронология событий документа</p>
      </div>

      <div className="flex-1 overflow-y-auto pr-1">
        {events.length === 0 ? (
          <div className="ai-empty py-8">Событий пока нет.</div>
        ) : (
          <div className="relative flex flex-col gap-3 pl-4">
            <div className="absolute left-[11px] top-2 bottom-2 w-px bg-ai-border" />
            {events.map((event) => (
              <div key={event.id} className="relative flex gap-3">
                <div className="z-10 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ai-surface border border-ai-border text-xs">
                  {EVENT_ICONS[event.event_type] || '•'}
                </div>
                <div className="flex-1 rounded-ai border border-ai-border bg-ai-surface p-2 text-sm">
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="font-medium text-ai-text">
                      {event.event_type}
                    </span>
                    <StatusBadge status={event.status} />
                  </div>
                  <div className="mb-1 text-xs text-ai-text-secondary">
                    {event.message || '(нет описания)'}
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-ai-text-muted">
                      {new Date(event.created_at).toLocaleString('ru-RU')}
                    </span>
                    {event.details && Object.keys(event.details).length > 0 && (
                      <button
                        onClick={() => setSelectedEvent(event)}
                        className="text-xs text-ai-primary hover:underline"
                        type="button"
                      >
                        Технический снимок
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selectedEvent && (
        <div
          className="ai-modal-overlay"
          onClick={() => setSelectedEvent(null)}
          role="presentation"
        >
          <div
            className="ai-modal"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <div className="ai-modal__header">
              <h4 className="ai-modal__title">
                Снимок: {selectedEvent.event_type}
              </h4>
              <button
                onClick={() => setSelectedEvent(null)}
                className="ai-modal__close"
                type="button"
                aria-label="Закрыть"
              >
                ×
              </button>
            </div>
            <pre className="ai-code-preview m-4 min-h-[160px]">
              {JSON.stringify(selectedEvent.details, null, 2)}
            </pre>
            <div className="ai-modal__actions">
              <button
                onClick={() => setSelectedEvent(null)}
                className="ai-btn px-4 py-2"
                type="button"
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default KbDocumentLifecycle;
