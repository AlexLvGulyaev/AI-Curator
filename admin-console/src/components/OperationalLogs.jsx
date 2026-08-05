
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  exportOperationalLogs,
  getOperationalLog,
  getOperationalLogs,
} from '../api/backend';
import {
  formatDetailsJson,
  statusBadgeClass,
} from '../utils/operationalConsoleUi';
import {
  formatDurationMs,
  formatTimestampMsk,
  intentLabelRu,
  shortId,
  statusLabelRu,
} from '../utils/operationalLabels';

const PAGE_SIZE = 7;
const WINDOW_OPTIONS = [
  { label: '24h', value: 1 },
  { label: '7d', value: 7 },
  { label: '30d', value: 30 },
  { label: 'все', value: null },
];

const STATUS_OPTIONS = [
  { value: 'all', label: 'все статусы' },
  { value: 'ok', label: 'успешно' },
  { value: 'error', label: 'ошибка' },
  { value: 'pending', label: 'ожидание' },
];

const INTENT_OPTIONS = [
  { value: 'all', label: 'все интенты' },
  { value: 'study', label: 'учебный' },
  { value: 'organizational', label: 'организационный' },
  { value: 'mixed', label: 'смешанный' },
  { value: 'progress', label: 'прогресс' },
  { value: 'deadline', label: 'дедлайн' },
  { value: 'out_of_scope', label: 'не распределено' },
];

const SOURCE_OPTIONS = [
  { value: 'all', label: 'все источники' },
  { value: 'lms', label: 'LMS' },
  { value: 'rag', label: 'База знаний' },
  { value: 'both', label: 'LMS + База знаний' },
  { value: 'cache', label: 'Кэш' },
  { value: 'fallback', label: 'Fallback бэкенда' },
  { value: 'error', label: 'Ошибка' },
];

function isoDate(offsetDays) {
  if (offsetDays == null) return '';
  const d = new Date();
  d.setDate(d.getDate() - offsetDays);
  return d.toISOString().slice(0, 10);
}

function buildPipelineTimeline(detail) {
  const timings = detail.analytics_events?.[0]?.payload?.timings_ms || {};
  const baseTime = detail.created_at;
  const stages = [];

  stages.push({
    key: 'received',
    label: 'Получен запрос',
    status: 'ok',
    duration_ms: 0,
    metadata: { query: detail.message, session_id: detail.session_id },
    timestamp: baseTime,
  });

  stages.push({
    key: 'intent_detect_ms',
    label: 'Классификация intent',
    status: detail.intent ? 'ok' : 'pending',
    duration_ms: timings.intent_detect_ms,
    metadata: { intent: detail.intent },
    timestamp: baseTime,
  });

  if (detail.cache_hit) {
    stages.push({
      key: 'cache_hit',
      label: 'Cache hit',
      status: 'ok',
      duration_ms: 0,
      metadata: { source: 'response_cache' },
      timestamp: baseTime,
    });
  }

  const hasLms = Array.isArray(detail.lms_calls) && detail.lms_calls.length > 0;
  if (hasLms) {
    const lmsDuration = detail.lms_calls.reduce((sum, c) => sum + (c.latency_ms || 0), 0);
    const hasError = detail.lms_calls.some((c) => c.status && c.status !== 'ok');
    stages.push({
      key: 'lms_call',
      label: 'LMS call',
      status: hasError ? 'error' : 'ok',
      duration_ms: lmsDuration || null,
      metadata: { calls: detail.lms_calls },
      timestamp: baseTime,
    });
  }

  const hasRag = detail.rag_filters && Object.keys(detail.rag_filters).length > 0;
  if (hasRag) {
    stages.push({
      key: 'rag_embedding_ms',
      label: 'Embedding запроса',
      status: 'ok',
      duration_ms: timings.rag_embedding_ms,
      metadata: {},
      timestamp: baseTime,
    });
    stages.push({
      key: 'rag_chroma_ms',
      label: 'Chroma search',
      status: detail.sources?.length ? 'ok' : 'warning',
      duration_ms: timings.rag_chroma_ms,
      metadata: { filters: detail.rag_filters, chunks: detail.sources?.length },
      timestamp: baseTime,
    });
    stages.push({
      key: 'rag_postprocess_ms',
      label: 'Постобработка RAG',
      status: 'ok',
      duration_ms: timings.rag_postprocess_ms,
      metadata: {},
      timestamp: baseTime,
    });
  }

  const llmCall = detail.llm_calls?.[0];
  stages.push({
    key: 'llm_generate_ms',
    label: 'Генерация LLM',
    status: llmCall ? (llmCall.status === 'ok' ? 'ok' : llmCall.status) : 'pending',
    duration_ms: timings.llm_generate_ms || llmCall?.latency_ms || null,
    metadata: { model: llmCall?.model || detail.llm_model, call: llmCall },
    timestamp: baseTime,
  });

  stages.push({
    key: 'validation_ms',
    label: 'Валидация ответа',
    status: detail.error ? 'error' : 'ok',
    duration_ms: timings.validation_ms || null,
    metadata: { has_sources: detail.sources?.length > 0, error: detail.error },
    timestamp: baseTime,
  });

  stages.push({
    key: 'response',
    label: 'Возврат ответа',
    status: detail.error ? 'error' : 'ok',
    duration_ms: 0,
    metadata: { answer_length: detail.answer?.length, answer_preview: detail.answer?.slice(0, 200) },
    timestamp: baseTime,
  });

  let offset = 0;
  for (const stage of stages) {
    const duration = Number.isFinite(stage.duration_ms) ? stage.duration_ms : 0;
    stage.offset_ms = offset;
    stage.delta_ms = duration;
    offset += duration;
  }

  return stages;
}

function CompactRow({ label, value, mono = false }) {
  return (
    <div className="grid grid-cols-[5.5rem_1fr] items-baseline gap-2 text-xs leading-tight min-w-0">
      <span className="text-ai-text-muted truncate">{label}:</span>
      <span
        className={`text-ai-text truncate ${mono ? 'font-mono' : ''}`}
        title={value}
      >
        {value || '—'}
      </span>
    </div>
  );
}

function SectionBox({ title, children, className = '' }) {
  return (
    <div className={`ai-card p-2 flex flex-col ${className}`}>
      {title && (
        <h4 className="text-[0.75rem] font-semibold uppercase tracking-wide text-ai-text-muted mb-1.5">
          {title}
        </h4>
      )}
      {children}
    </div>
  );
}

function RagChunksModal({ chunks, threshold, onClose }) {
  if (!chunks) return null;
  return (
    <div className="ai-modal-overlay" onClick={onClose}>
      <div className="ai-modal ai-modal--wide" onClick={(e) => e.stopPropagation()}>
        <div className="ai-modal__header">
          <h3 className="ai-modal__title">Найденные чанки</h3>
          <button type="button" className="ai-modal__close" onClick={onClose}>×</button>
        </div>
        <div className="ai-modal__body space-y-2">
          {chunks.length === 0 ? (
            <div className="text-sm text-ai-text-muted">Чанки не найдены.</div>
          ) : (
            chunks.map((chunk, idx) => {
              const distance = chunk.distance;
              const meta = chunk.metadata || {};
              const hit = distance != null && threshold != null && distance <= threshold;
              return (
                <div key={idx} className="rounded-ai border border-ai-border-subtle bg-black/10 p-2 text-xs">
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="mono text-ai-text-muted">#{idx + 1}</span>
                      <span className="mono text-ai-text">{meta.document_id != null ? `doc ${meta.document_id}` : '—'}</span>
                      <span className={`inline-flex rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${hit ? statusBadgeClass('ok') : statusBadgeClass('warning')}`}>
                        {hit ? 'HIT' : 'MISS'}
                      </span>
                    </div>
                    <span className="mono text-ai-text">distance: {distance != null ? distance.toFixed(4) : '—'}</span>
                  </div>
                  {meta.title ? (
                    <div className="mb-1 text-ai-text font-medium truncate">{meta.title}</div>
                  ) : null}
                  <details>
                    <summary className="cursor-pointer text-[10px] text-ai-accent">Показать полный текст</summary>
                    <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap rounded bg-ai-bg p-1.5 text-[10px] text-ai-text-secondary">
                      {chunk.content || '—'}
                    </pre>
                  </details>
                </div>
              );
            })
          )}
        </div>
        <div className="ai-modal__actions">
          <button type="button" className="ai-btn-outline rounded-ai px-3 py-1.5 text-sm" onClick={onClose}>
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
}

export default function OperationalLogs() {
  const [logs, setLogs] = useState({ items: [], total: 0, limit: PAGE_SIZE, offset: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [ragModalChunks, setRagModalChunks] = useState(null);

  const [windowDays, setWindowDays] = useState(7);
  const [statusFilter, setStatusFilter] = useState('all');
  const [intentFilter, setIntentFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [exporting, setExporting] = useState(false);

  const listRef = useRef(null);
  const pendingListFocusRef = useRef(false);
  const pendingPageSelectIndexRef = useRef(null);

  const filters = useMemo(
    () => ({
      status: statusFilter === 'all' ? undefined : statusFilter,
      intent: intentFilter === 'all' ? undefined : intentFilter,
      source_type: sourceFilter === 'all' ? undefined : sourceFilter,
      session_id: search.trim() || undefined,
      date_from: isoDate(windowDays),
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }),
    [statusFilter, intentFilter, sourceFilter, search, windowDays, page, refreshNonce]
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getOperationalLogs(filters)
      .then((data) => {
        if (!cancelled) {
          setLogs(data);
          if (data.items.length) {
            if (pendingPageSelectIndexRef.current != null) {
              const idx = pendingPageSelectIndexRef.current;
              pendingPageSelectIndexRef.current = null;
              const target = data.items[idx] || data.items[data.items.length - 1] || data.items[0];
              if (target?.id) {
                pendingListFocusRef.current = true;
                setSelectedId(target.id);
                return;
              }
            }
            if (!selectedId) {
              setSelectedId(data.items[0].id);
            }
          }
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filters]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    setDetailError(null);
    getOperationalLog(selectedId)
      .then((data) => {
        if (!cancelled) setDetail(data);
      })
      .catch((err) => {
        if (!cancelled) setDetailError(err.message);
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId, refreshNonce]);

  useEffect(() => {
    setPage(0);
  }, [statusFilter, intentFilter, sourceFilter, windowDays, search]);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
      const t = e.target;
      if (t && (t.closest('input') || t.closest('textarea') || t.closest('select') || t.isContentEditable)) {
        return;
      }
      const totalPages = Math.max(1, Math.ceil(logs.total / PAGE_SIZE));
      const curIdx = selectedId ? logs.items.findIndex((s) => String(s.id) === String(selectedId)) : 0;
      if (curIdx < 0) return;
      if (e.key === 'ArrowDown') {
        if (curIdx + 1 < logs.items.length) {
          const next = logs.items[curIdx + 1];
          if (!next?.id) return;
          e.preventDefault();
          pendingListFocusRef.current = true;
          setSelectedId(next.id);
          return;
        }
        if (page + 1 < totalPages) {
          e.preventDefault();
          pendingPageSelectIndexRef.current = 0;
          setPage((p) => p + 1);
        }
        return;
      }
      if (e.key === 'ArrowUp') {
        if (curIdx > 0) {
          const next = logs.items[curIdx - 1];
          if (!next?.id) return;
          e.preventDefault();
          pendingListFocusRef.current = true;
          setSelectedId(next.id);
          return;
        }
        if (page > 0) {
          e.preventDefault();
          pendingPageSelectIndexRef.current = PAGE_SIZE - 1;
          setPage((p) => p - 1);
        }
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [logs.items, selectedId, page, logs.total]);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(logs.total / PAGE_SIZE)), [logs.total]);

  useEffect(() => {
    if (!selectedId) return;
    const list = listRef.current;
    if (!list) return;
    const safeId =
      typeof CSS !== 'undefined' && typeof CSS.escape === 'function'
        ? CSS.escape(String(selectedId))
        : String(selectedId).replace(/"/g, '\\"');
    const row = list.querySelector(`[data-log-id="${safeId}"]`);
    if (!row) return;
    row.scrollIntoView({ block: 'nearest' });
    const listHasFocus =
      document.activeElement instanceof Node && list.contains(document.activeElement);
    const shouldFocus = pendingListFocusRef.current || listHasFocus;
    pendingListFocusRef.current = false;
    if (!shouldFocus) return;
    const id = window.requestAnimationFrame(() => {
      row.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(id);
  }, [selectedId, page]);

  function resetFilters() {
    setWindowDays(7);
    setStatusFilter('all');
    setIntentFilter('all');
    setSourceFilter('all');
    setSearch('');
    setPage(0);
  }

  async function handleExport() {
    if (exporting) return;
    setExporting(true);
    setError(null);
    try {
      const blob = await exportOperationalLogs({
        status: statusFilter === 'all' ? undefined : statusFilter,
        intent: intentFilter === 'all' ? undefined : intentFilter,
        source_type: sourceFilter === 'all' ? undefined : sourceFilter,
        session_id: search.trim() || undefined,
        date_from: isoDate(windowDays),
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ai_curator_operational_logs_${windowDays ? `${windowDays}d` : 'all'}_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    } finally {
      setExporting(false);
    }
  }

  function renderList() {
    if (loading && logs.items.length === 0) {
      return (
        <div className="flex h-48 items-center justify-center text-ai-text-muted">
          <span className="mr-2 inline-block animate-pulse">●</span>
          Загрузка логов…
        </div>
      );
    }
    if (error) {
      return (
        <div className="m-4 rounded-ai border border-ai-error/20 bg-red-500/10 p-4 text-sm text-ai-error">
          {error}
        </div>
      );
    }
    if (logs.items.length === 0) {
      return (
        <div className="flex h-48 items-center justify-center text-ai-text-muted">
          За выбранный период записей не найдены.
        </div>
      );
    }
    return (
      <div className="flex-1 overflow-y-auto pr-1 min-h-0" ref={listRef}>
        <div className="flex flex-col gap-2">
          {logs.items.map((log) => {
            const isSelected = selectedId === log.id;
            return (
              <button
                key={log.id}
                type="button"
                data-log-id={log.id}
                onClick={() => {
                  pendingListFocusRef.current = true;
                  setSelectedId(log.id);
                }}
                className={`text-left rounded-ai border p-2 transition-colors ${
                  isSelected
                    ? 'border-ai-primary bg-ai-primary-light'
                    : 'border-ai-border bg-ai-surface hover:border-ai-primary'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-xs text-ai-text-muted">
                    {formatTimestampMsk(log.created_at)}
                  </span>
                  <span className={`ai-status ai-status--${log.status === 'ok' ? 'ok' : log.status === 'error' ? 'error' : 'info'}`}>
                    {statusLabelRu(log.status)}
                  </span>
                  {log.cache_hit ? (
                    <span className="ai-status ai-status--ok">кэш</span>
                  ) : null}
                </div>
                <div className="text-sm font-medium text-ai-text line-clamp-2 mb-1">{log.message_preview}</div>
                <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-ai-text-secondary">
                  <span>#{log.id}</span>
                  {log.role ? (
                    <>
                      <span>·</span>
                      <span>{log.role}</span>
                    </>
                  ) : null}
                  {log.course_id ? (
                    <>
                      <span>·</span>
                      <span>course: {log.course_id}</span>
                    </>
                  ) : null}
                  {log.intent ? (
                    <>
                      <span>·</span>
                      <span>{intentLabelRu(log.intent)}</span>
                    </>
                  ) : null}
                  {log.latency_ms ? (
                    <>
                      <span>·</span>
                      <span>{formatDurationMs(log.latency_ms)}</span>
                    </>
                  ) : null}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  function renderDetail() {
    if (!selectedId) {
      return (
        <div className="ai-card flex h-full items-center justify-center p-4">
          <div className="ai-empty">Выберите запись для просмотра деталей.</div>
        </div>
      );
    }
    if (detailLoading && !detail) {
      return (
        <div className="ai-card flex h-full items-center justify-center p-4">
          <span className="mr-2 inline-block animate-pulse">●</span>
          Загрузка деталей…
        </div>
      );
    }
    if (detailError) {
      return (
        <div className="ai-card h-full p-4">
          <div className="ai-error text-sm">{detailError}</div>
        </div>
      );
    }
    if (!detail) return null;

    const pipelineStages = buildPipelineTimeline(detail);
    const pipelineSummary = pipelineStages.map((s) => s.label).join(' → ');

    return (
      <div className="ai-card flex h-full flex-col overflow-hidden p-2">
        <div className="mb-2 flex items-center justify-between border-b border-ai-border pb-2">
          <h3 className="ai-section__title">ДЕТАЛИЗАЦИЯ ЗАПРОСА</h3>
          <span className={`ai-status ai-status--${detail.status === 'ok' ? 'ok' : detail.status === 'error' ? 'error' : 'info'}`}>
            {statusLabelRu(detail.status)}
          </span>
        </div>

        <div className="flex h-full min-h-0 flex-col gap-2 pr-1">
          <div className="grid grid-cols-2 gap-2 shrink-0">
            <SectionBox title="Параметры запроса">
              <div className="space-y-1">
                <CompactRow label="Сессия" value={detail.session_id} mono />
                <CompactRow label="Роль" value={detail.role} />
                <CompactRow label="Курс" value={detail.course_id} />
                <CompactRow label="Сложность" value={detail.difficulty} />
                <CompactRow label="Создано" value={formatTimestampMsk(detail.created_at)} />
              </div>
            </SectionBox>

            <SectionBox title="Параметры исполнения">
              <div className="space-y-1">
                <CompactRow label="Интент" value={intentLabelRu(detail.intent)} />
                <CompactRow label="Latency" value={formatDurationMs(detail.latency_ms)} />
                <CompactRow label="Токены" value={detail.total_tokens} />
                <CompactRow label="Модель" value={detail.llm_model} />
                <CompactRow label="Оценка" value={detail.feedback_score} />
                <CompactRow label="Cache hit" value={detail.cache_hit ? 'да' : 'нет'} />
              </div>
            </SectionBox>
          </div>

          <SectionBox title="Цепочка этапов" className="shrink-0">
            <p className="text-xs text-ai-text-secondary break-words">{pipelineSummary}</p>
          </SectionBox>

          <div className="grid grid-cols-2 gap-2 shrink-0">
            <SectionBox title="Запрос пользователя" className="min-h-0">
              <pre className="max-h-[120px] overflow-auto whitespace-pre-wrap break-words rounded-ai bg-black/20 p-2 text-xs text-ai-text">
                {detail.message}
              </pre>
            </SectionBox>

            <SectionBox title="Ответ системы" className="min-h-0">
              <div className="max-h-[120px] overflow-auto rounded-ai bg-black/20 p-2 text-xs text-ai-text">
                {detail.answer ? (
                  <>
                    <p className="whitespace-pre-wrap break-words">{detail.answer}</p>
                    {detail.sources?.length ? (
                      <div className="mt-2 border-t border-ai-border-subtle pt-2">
                        <span className="text-ai-text-muted">Источники: </span>
                        <span>{detail.sources.map((s) => s.title || s.type).join(', ')}</span>
                      </div>
                    ) : null}
                  </>
                ) : (
                  <span className="text-ai-text-muted">—</span>
                )}
              </div>
            </SectionBox>
          </div>

          {detail.error ? (
            <SectionBox title="Ошибка" className="border-ai-error/20 bg-red-500/10 shrink-0">
              <pre className="whitespace-pre-wrap text-xs text-ai-error">{detail.error}</pre>
            </SectionBox>
          ) : null}

          <div className="ai-card flex min-h-0 flex-1 flex-col overflow-hidden p-2">
            <h4 className="mb-1.5 text-[0.75rem] font-semibold uppercase tracking-wide text-ai-text-muted">
              Таймлайн pipeline
            </h4>
            <div className="flex-1 min-h-0 overflow-y-auto pr-1">
              <div className="space-y-1">
                {pipelineStages.map((stage) => (
                  <div key={stage.key} className="rounded-ai border border-ai-border-subtle bg-black/10 text-xs">
                    <div className="flex items-center justify-between px-2 py-1.5 gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="mono text-ai-text-muted shrink-0">{formatTimestampMsk(stage.timestamp)}</span>
                        <span className={`inline-flex rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${statusBadgeClass(stage.status)}`}>
                          {statusLabelRu(stage.status)}
                        </span>
                        <span className="text-ai-text font-medium truncate">{stage.label}</span>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="mono text-ai-text">{formatDurationMs(stage.offset_ms)}</span>
                        <span className="mono text-ai-text-muted">+{formatDurationMs(stage.duration_ms)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 px-2 pb-1.5">
                      <details className="flex-1">
                        <summary className="cursor-pointer text-[10px] text-ai-accent">JSON payload</summary>
                        <pre className="mt-1 max-h-24 overflow-auto rounded bg-ai-bg p-1.5 text-[10px] text-ai-text-secondary">
                          {formatDetailsJson(stage.metadata)}
                        </pre>
                      </details>
                      {stage.key === 'rag_chroma_ms' && detail.execution_session ? (
                        <button
                          type="button"
                          onClick={() => {
                            const contextStep = detail.execution_session.steps?.find(
                              (s) => s.stage_name === 'context_build' && Array.isArray(s.step_metadata?.rag_context)
                            );
                            const meta = contextStep?.step_metadata || {};
                            setRagModalChunks({
                              chunks: meta.rag_context || [],
                              threshold: meta.rag_distance_threshold ?? detail.rag_filters?.rag_distance_threshold ?? null,
                            });
                          }}
                          className="text-[10px] text-ai-accent hover:underline"
                        >
                          Показать чанки
                        </button>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>

              <details className="mt-2">
                <summary className="cursor-pointer text-[10px] text-ai-text-muted">Технический снимок (JSON)</summary>
                <pre className="mt-1 whitespace-pre-wrap rounded-ai bg-black/20 p-2 text-[10px] text-ai-text-secondary">
                  {formatDetailsJson(detail)}
                </pre>
              </details>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="ai-config-page flex h-full flex-col">
      <div className="ai-page__header border-b border-ai-border">
        <div>
          <h1 className="ai-page__title">Логи</h1>
          <p className="ai-page__subtitle">Операционная консоль запросов и исполнений</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleExport}
            disabled={exporting}
            className="ai-btn-outline rounded-ai px-3 py-1.5 text-sm disabled:opacity-60"
          >
            {exporting ? 'Экспорт…' : 'Экспорт CSV'}
          </button>
          <button
            type="button"
            onClick={() => setRefreshNonce((n) => n + 1)}
            className="ai-btn-outline rounded-ai px-3 py-1.5 text-sm"
          >
            Обновить
          </button>
        </div>
      </div>

      <RagChunksModal
        chunks={ragModalChunks?.chunks}
        threshold={ragModalChunks?.threshold}
        onClose={() => setRagModalChunks(null)}
      />

      <div className="flex flex-1 overflow-hidden">
        <div className="ai-card flex h-full w-[420px] flex-col overflow-hidden p-3 pb-2">
          <div className="grid grid-cols-2 gap-2 mb-2">
            <select
              className="ai-select w-full px-2 py-1 text-xs"
              value={windowDays}
              onChange={(e) => setWindowDays(e.target.value === '' ? null : Number(e.target.value))}
            >
              {WINDOW_OPTIONS.map((w) => (
                <option key={w.label} value={w.value ?? ''}>
                  {w.label}
                </option>
              ))}
            </select>
            <select
              className="ai-select w-full px-2 py-1 text-xs"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
            <select
              className="ai-select w-full px-2 py-1 text-xs"
              value={intentFilter}
              onChange={(e) => setIntentFilter(e.target.value)}
            >
              {INTENT_OPTIONS.map((i) => (
                <option key={i.value} value={i.value}>
                  {i.label}
                </option>
              ))}
            </select>
            <select
              className="ai-select w-full px-2 py-1 text-xs"
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
            >
              {SOURCE_OPTIONS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          <input
            type="text"
            className="ai-input w-full mb-2 text-sm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Поиск по session_id..."
          />

          <div className="mb-2 flex items-center justify-between border-b border-ai-border pb-2 text-xs">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page <= 0}
              className="ai-btn-outline rounded-ai px-2 py-1"
            >
              ← Назад
            </button>
            <span className="text-ai-text-secondary">
              Страница {page + 1} из {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="ai-btn-outline rounded-ai px-2 py-1"
            >
              Вперёд →
            </button>
          </div>

          <div className="mb-2 flex items-center justify-between text-xs text-ai-text-secondary">
            <span>Всего {logs.total}</span>
            <button
              type="button"
              onClick={resetFilters}
              className="ai-btn-outline rounded-ai px-2 py-1 text-ai-accent hover:underline"
            >
              Сброс
            </button>
          </div>

          {renderList()}
        </div>

        <div className="flex-1 overflow-hidden bg-ai-bg p-2 pt-0 pb-2">{renderDetail()}</div>
      </div>
    </div>
  );
}
