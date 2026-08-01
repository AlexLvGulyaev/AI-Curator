import { useEffect, useMemo, useRef, useState } from 'react';
import { getDialogSession, getDialogSessions } from '../api/backend';
import OperationalModalityBadge from './OperationalModalityBadge';
import OperationalPipelineStageIcon from './OperationalPipelineStageIcon';
import SessionJsonSnapshot from './SessionJsonSnapshot';
import {
  formatDetailsJson,
  pipelineStageVariant,
} from '../utils/operationalConsoleUi';
import {
  formatDurationMs,
  formatTimestampMsk,
  normalizeStatus,
  routeLabelRu,
  shortId,
  stageToActionRu,
  statusLabelRu,
} from '../utils/operationalLabels';

const PAGE_SIZE = 7;
const WINDOW_OPTIONS = [
  { label: '24h', value: 24 },
  { label: '7d', value: 168 },
  { label: '30d', value: 720 },
  { label: 'все', value: null },
];

const MODE_OPTIONS = [
  { value: 'all', label: 'все режимы' },
  { value: 'text', label: 'текст' },
  { value: 'lms', label: 'LMS' },
  { value: 'rag', label: 'RAG' },
  { value: 'mixed', label: 'mixed' },
];

const ACTIVE_OPTIONS = [
  { value: 'all', label: 'все статусы' },
  { value: 'active', label: 'активные' },
  { value: 'inactive', label: 'неактивные' },
];

function ActiveBadge({ active }) {
  return (
    <span className={`ai-status ${active ? 'ai-status--ok' : 'ai-status--muted'}`}>
      {active ? 'АКТИВНА' : 'НЕАКТИВНА'}
    </span>
  );
}

function OpsRow({ label, value }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </>
  );
}

function toTs(iso) {
  if (!iso) return null;
  const n = new Date(iso).getTime();
  return Number.isFinite(n) ? n : null;
}

function pairDialogRows(turns, executions) {
  const rows = [];
  let pendingUser = null;
  for (const t of turns) {
    const userMsg = t.user_message;
    const assistantMsg = t.assistant_answer;
    const ts = t.created_at || null;
    if (userMsg != null) {
      if (pendingUser != null) {
        rows.push({
          user: pendingUser.content,
          assistant: '—',
          cache_hit: null,
          response_time_ms: null,
          execution_id: null,
        });
      }
      pendingUser = { content: userMsg, created_at: ts, request_id: t.request_id };
    }
    if (assistantMsg != null) {
      const ex = findExecutionForRequest(executions, pendingUser?.request_id);
      rows.push({
        user: pendingUser?.content || '—',
        assistant: assistantMsg,
        cache_hit: ex?.cache_hit ?? null,
        response_time_ms: t.latency_ms ?? ex?.duration_ms ?? null,
        execution_id: ex?.id ?? null,
        sources: t.sources,
      });
      pendingUser = null;
    }
  }
  if (pendingUser != null) {
    rows.push({
      user: pendingUser.content,
      assistant: '—',
      cache_hit: null,
      response_time_ms: null,
      execution_id: null,
    });
  }
  return rows;
}

function findExecutionForRequest(executions, requestId) {
  if (!requestId || !executions?.length) return null;
  return executions.find((e) => e.request_id === requestId) || null;
}

function DialogDetail({ detail }) {
  const dialogRows = useMemo(
    () => pairDialogRows(detail.turns || [], detail.execution_sessions || []),
    [detail.turns, detail.execution_sessions]
  );
  const latestExecution = detail.execution_sessions?.[detail.execution_sessions.length - 1] || null;
  const budget = detail.budget || {};
  const runtime = latestExecution || {};

  return (
    <div className="logs-detail memory-detail-panel">
      <div className="logs-detail__head">
        <h2 className="logs-detail__title">Сводка диалоговой сессии</h2>
        <ActiveBadge active={detail.is_active} />
      </div>

      <div className="logs-summary-grid memory-summary-grid">
        <div className="logs-summary-col memory-summary-col">
          <h3 className="memory-summary-col__title">Параметры сессии</h3>
          <dl className="kv logs-detail-kv">
            <OpsRow
              label="session_id"
              value={<span className="mono break-all">{shortId(detail.session_id, 12)}</span>}
            />
            <OpsRow label="visitor IP" value={<span className="mono">{runtime.client_ip || '—'}</span>} />
            <OpsRow label="Режим" value={<span className="mono">{detail.mode || '—'}</span>} />
            <OpsRow label="Активна" value={<ActiveBadge active={detail.is_active} />} />
            <OpsRow label="Сообщений" value={String(detail.message_count ?? 0)} />
            <OpsRow label="Turns~" value={String(dialogRows.length)} />
            <OpsRow
              label="Обновлена"
              value={
                detail.last_message_at ? (
                  <span className="mono">{formatTimestampMsk(detail.last_message_at)}</span>
                ) : (
                  '—'
                )
              }
            />
          </dl>
        </div>

        <div className="logs-summary-col memory-summary-col">
          <h3 className="memory-summary-col__title">Параметры исполнения</h3>
          <dl className="kv logs-detail-kv">
            <OpsRow
              label="RAG"
              value={detail.mode === 'rag' || detail.mode === 'mixed' ? 'да' : 'нет'}
            />
            <OpsRow
              label="provider / model"
              value={
                <span className="mono">
                  {runtime.provider_key || '—'} / {runtime.model_name || budget.model || '—'}
                </span>
              }
            />
            <OpsRow label="response time" value={formatDurationMs(runtime.duration_ms)} />
            <OpsRow label="source" value={<span className="mono">{detail.memory_source || 'PostgreSQL'}</span>} />
            <OpsRow label="route" value={<span className="mono">{runtime.route || '—'}</span>} />
          </dl>
        </div>

        <div className="logs-summary-col memory-summary-col">
          <h3 className="memory-summary-col__title">Memory policy / limits</h3>
          <dl className="kv logs-detail-kv">
            <OpsRow label="model" value={<span className="mono">{budget.model || '—'}</span>} />
            <OpsRow label="max_tokens" value={String(budget.max_tokens ?? '—')} />
            <OpsRow label="temperature" value={budget.temperature != null ? String(budget.temperature) : '—'} />
          </dl>
        </div>
      </div>

      <div className="memory-dialog-panel">
        <h3 className="logs-detail-block__title">Диалог сессии</h3>
        <p className="memory-dialog-panel__lead muted">
          Парные реплики по времени; при неполном turn пустая ячейка.
        </p>
        <div className="memory-dialog-table-wrap">
          <table className="memory-dialog-table">
            <thead>
              <tr>
                <th>Запрос пользователя</th>
                <th>Ответ системы</th>
                <th className="memory-dialog-table__col--narrow">Cache hit</th>
                <th className="memory-dialog-table__col--narrow">Response time</th>
              </tr>
            </thead>
            <tbody>
              {dialogRows.length ? (
                dialogRows.map((row, i) => (
                  <tr key={i}>
                    <td className="memory-dialog-table__cell memory-dialog-table__cell--user">
                      {row.user}
                    </td>
                    <td className="memory-dialog-table__cell memory-dialog-table__cell--assistant">
                      {row.assistant}
                      {row.sources?.length ? (
                        <div className="memory-response-sources">
                          <span className="memory-response-sources__divider" />
                          <span className="memory-response-sources__label">Источники:</span>
                          {row.sources.map((s) => s.title || s.chunk_id || String(s)).join(', ')}
                        </div>
                      ) : null}
                    </td>
                    <td className="memory-dialog-table__cell memory-dialog-table__cell--runtime">
                      {row.cache_hit === null ? '—' : row.cache_hit ? 'hit' : 'miss'}
                    </td>
                    <td className="memory-dialog-table__cell memory-dialog-table__cell--runtime">
                      {formatDurationMs(row.response_time_ms)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="muted memory-dialog-table__empty">
                    Нет user/assistant сообщений.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {latestExecution ? (
        <details className="memory-timeline-fold page__mt">
          <summary className="memory-timeline-fold__summary logs-timeline-heading">
            Таймлайн execution pipeline
          </summary>
          <div className="logs-timeline">
            {latestExecution.steps.map((step, i) => {
              const prev = i > 0 ? toTs(latestExecution.steps[i - 1].finished_at) : null;
              const cur = toTs(step.finished_at);
              const delta = prev != null && cur != null ? Math.max(0, cur - prev) : null;
              const stageRaw = String(step.stage_name || '').trim();
              const label = stageToActionRu(stageRaw);
              const status = normalizeStatus(step.status);
              return (
                <div key={step.id} className="logs-stage logs-stage--compact" title={`stage: ${stageRaw}`}>
                  <div className="logs-stage__top">
                    <span className="mono logs-stage__time">{formatTimestampMsk(step.finished_at)}</span>
                    <span className="logs-stage__label af-logs-stage-label-with-icon">
                      <OperationalPipelineStageIcon stage={stageRaw} status={step.status} />
                      {label}
                    </span>
                    <span className={`logs-status logs-status--${status}`}>{statusLabelRu(step.status)}</span>
                    {step.duration_ms != null ? (
                      <span className="muted mono" title="Длительность выполнения шага">
                        {formatDurationMs(step.duration_ms)}
                      </span>
                    ) : null}
                    {delta != null ? (
                      <span
                        className="muted mono logs-stage__delta"
                        title="Время, прошедшее с предыдущего шага"
                      >
                        +{delta} мс
                      </span>
                    ) : null}
                  </div>
                  <details className="logs-stage__details">
                    <summary className="log-details__summary">
                      {formatDetailsJson(step.step_metadata).slice(0, 56)}
                      {formatDetailsJson(step.step_metadata).length > 56 ? '…' : ''}
                    </summary>
                    <pre className="log-details__json mono">{formatDetailsJson(step.step_metadata)}</pre>
                  </details>
                </div>
              );
            })}
          </div>
        </details>
      ) : null}

      <SessionJsonSnapshot
        className="page__mt"
        body={detail}
        summaryLabel="Технический снимок диалога (JSON)"
      />
    </div>
  );
}

export default function DialogSessions() {
  const [list, setList] = useState({ items: [], total: 0, limit: PAGE_SIZE, offset: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [windowLabel, setWindowLabel] = useState('24h');
  const [modeFilter, setModeFilter] = useState('all');
  const [activeFilter, setActiveFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [pageIndex, setPageIndex] = useState(0);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);

  const listRef = useRef(null);
  const pendingListFocusRef = useRef(false);

  const hours = useMemo(
    () => WINDOW_OPTIONS.find((w) => w.label === windowLabel)?.value ?? null,
    [windowLabel]
  );

  const loadList = useMemo(
    () => async () => {
      setLoading(true);
      setError(null);
      try {
        const params = {
          limit: PAGE_SIZE,
          offset: pageIndex * PAGE_SIZE,
        };
        if (hours != null) params.hours = hours;
        if (modeFilter !== 'all') params.mode = modeFilter;
        if (activeFilter === 'active') params.active_only = true;
        if (activeFilter === 'inactive') params.active_only = false;
        if (searchQuery.trim()) params.search = searchQuery.trim();
        const data = await getDialogSessions(params);
        setList(data);
      } catch (e) {
        setList({ items: [], total: 0, limit: PAGE_SIZE, offset: 0 });
        setError(e instanceof Error ? e.message : 'Ошибка загрузки диалогов');
      } finally {
        setLoading(false);
      }
    },
    [hours, modeFilter, activeFilter, searchQuery, pageIndex, refreshNonce]
  );

  useEffect(() => {
    loadList();
  }, [loadList]);

  useEffect(() => {
    setPageIndex(0);
  }, [searchQuery, activeFilter, modeFilter, windowLabel, refreshNonce]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setDetailError(null);
      setDetailLoading(false);
      return;
    }
    let cancelled = false;
    setDetail(null);
    setDetailLoading(true);
    setDetailError(null);
    (async () => {
      try {
        const d = await getDialogSession(selectedId);
        if (!cancelled) setDetail(d);
      } catch (e) {
        if (!cancelled) setDetailError(e instanceof Error ? e.message : 'detail error');
      } finally {
        if (!cancelled) setDetailLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId, refreshNonce]);

  useEffect(() => {
    if (loading || error) return;
    if (list.total === 0) {
      if (selectedId) setSelectedId(null);
      return;
    }
    const inList = selectedId ? list.items.some((r) => r.session_id === selectedId) : false;
    if (!selectedId || !inList) {
      setSelectedId(list.items[0]?.session_id || null);
    }
  }, [loading, error, list, selectedId]);

  useEffect(() => {
    if (!selectedId) return;
    const listEl = listRef.current;
    if (!listEl) return;
    const safeId =
      typeof CSS !== 'undefined' && typeof CSS.escape === 'function'
        ? CSS.escape(String(selectedId))
        : String(selectedId).replace(/"/g, '\\"');
    const row = listEl.querySelector(`[data-session-id="${safeId}"]`);
    if (!row) return;
    row.scrollIntoView({ block: 'nearest' });
    const listHasFocus = document.activeElement instanceof Node && listEl.contains(document.activeElement);
    const shouldFocus = pendingListFocusRef.current || listHasFocus;
    pendingListFocusRef.current = false;
    if (!shouldFocus) return;
    const id = window.requestAnimationFrame(() => {
      row.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(id);
  }, [selectedId, pageIndex]);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
      const t = e.target;
      if (t && (t.closest('input') || t.closest('textarea') || t.closest('select') || t.isContentEditable)) {
        return;
      }
      if (!list.items.length) return;
      const curIdx = selectedId ? list.items.findIndex((s) => s.session_id === selectedId) : 0;
      if (curIdx < 0) return;
      const nextIdx =
        e.key === 'ArrowDown'
          ? Math.min(list.items.length - 1, curIdx + 1)
          : Math.max(0, curIdx - 1);
      if (nextIdx === curIdx) return;
      e.preventDefault();
      const next = list.items[nextIdx];
      if (!next?.session_id) return;
      pendingListFocusRef.current = true;
      setPageIndex(Math.floor(nextIdx / PAGE_SIZE));
      setSelectedId(next.session_id);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [list.items, selectedId]);

  const totalPages = Math.max(1, Math.ceil(list.total / PAGE_SIZE));
  const safePageIdx = Math.min(pageIndex, Math.max(0, totalPages - 1));

  useEffect(() => {
    if (pageIndex !== safePageIdx) setPageIndex(safePageIdx);
  }, [pageIndex, safePageIdx]);

  const pageSessions = list.items;

  const goPrevPage = () => {
    pendingListFocusRef.current = true;
    const np = Math.max(0, safePageIdx - 1);
    setPageIndex(np);
  };

  const goNextPage = () => {
    pendingListFocusRef.current = true;
    const np = Math.min(totalPages - 1, safePageIdx + 1);
    setPageIndex(np);
  };

  const resetPagination = () => {
    pendingListFocusRef.current = true;
    setPageIndex(0);
    setSearchQuery('');
    setActiveFilter('all');
    setModeFilter('all');
    setWindowLabel('24h');
    const first = list.items[0]?.session_id || null;
    if (first) setSelectedId(first);
  };

  const listMetaLine = `Страница ${safePageIdx + 1} из ${totalPages} · сессий: ${list.total} · показано: ${pageSessions.length}`;

  return (
    <div className="page logs-page memory-console-page">
      <div className="flex items-start justify-between border-b border-ai-border pb-3 mb-3">
        <div>
          <h1 className="font-display text-xl font-bold text-ai-text">Dialog Sessions</h1>
          <p className="page__lead muted text-sm">Операционная консоль диалоговых сессий</p>
        </div>
        <button
          type="button"
          onClick={() => setRefreshNonce((n) => n + 1)}
          className="ai-btn-outline text-sm px-3 py-1.5"
          disabled={loading}
        >
          {loading ? '…' : 'Обновить'}
        </button>
      </div>

      {error ? (
        <div className="panel panel--error page__mt ai-error text-sm" role="alert">{error}</div>
      ) : (
        <div className="logs-console memory-logs-console">
          <section className="logs-left card">
            <div className="logs-filters">
              <div className="logs-filter-row">
                <select
                  className="logs-select"
                  value={windowLabel}
                  onChange={(e) => setWindowLabel(e.target.value)}
                  aria-label="Окно времени"
                >
                  {WINDOW_OPTIONS.map((w) => (
                    <option key={w.label} value={w.label}>{w.label}</option>
                  ))}
                </select>
                <select
                  className="logs-select"
                  value={modeFilter}
                  onChange={(e) => setModeFilter(e.target.value)}
                  aria-label="Режим сессии"
                >
                  {MODE_OPTIONS.map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
                <select
                  className="logs-select"
                  value={activeFilter}
                  onChange={(e) => setActiveFilter(e.target.value)}
                  aria-label="Статус активности"
                >
                  {ACTIVE_OPTIONS.map((a) => (
                    <option key={a.value} value={a.value}>{a.label}</option>
                  ))}
                </select>
              </div>
              <input
                type="text"
                className="logs-search memory-logs-search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Поиск: session_id, role, mode…"
                aria-label="Поиск сессий"
              />
              <div className="logs-filter-meta logs-filter-meta--with-refresh muted">
                <span>{listMetaLine}</span>
              </div>
              <div className="logs-page-controls">
                <button
                  type="button"
                  className="logs-page-btn"
                  onClick={goPrevPage}
                  disabled={safePageIdx <= 0 || list.total === 0}
                >
                  ← Предыдущая
                </button>
                <button
                  type="button"
                  className="logs-page-btn"
                  onClick={goNextPage}
                  disabled={safePageIdx >= totalPages - 1 || list.total === 0}
                >
                  Следующая →
                </button>
                <button
                  type="button"
                  className="logs-page-btn logs-page-btn--muted"
                  onClick={resetPagination}
                  disabled={
                    safePageIdx === 0 &&
                    !searchQuery.trim() &&
                    activeFilter === 'all' &&
                    modeFilter === 'all' &&
                    windowLabel === '24h'
                  }
                >
                  Сброс
                </button>
              </div>
            </div>

            <div className="logs-list" ref={listRef}>
              {loading && !list.items?.length ? (
                <div className="flex h-48 items-center justify-center text-ai-text-muted">
                  <span className="mr-2 inline-block animate-pulse">●</span>
                  Загрузка сессий…
                </div>
              ) : list.total === 0 ? (
                <div className="flex h-48 items-center justify-center text-ai-text-muted text-sm">
                  При пустой БД список пуст.
                </div>
              ) : (
                pageSessions.map((row) => {
                  const sid = row.session_id;
                  const routeKey = row.mode;
                  return (
                    <button
                      key={sid}
                      type="button"
                      data-session-id={sid}
                      className={`logs-item memory-logs-item ${selectedId === sid ? 'logs-item--selected' : ''}`}
                      onClick={() => {
                        pendingListFocusRef.current = true;
                        setSelectedId(sid);
                      }}
                    >
                      <div className="logs-item__row logs-item__row--tight">
                        <span className="mono logs-item__ts">
                          {row.last_message_at ? formatTimestampMsk(row.last_message_at) : '—'}
                        </span>
                        <OperationalModalityBadge modality={routeKey} />
                        <ActiveBadge active={row.is_active !== false} />
                      </div>
                      <div className="logs-item__preview memory-logs-item__user" title={sid}>
                        session: {shortId(sid, 12)}
                      </div>
                      <div className="logs-item__row logs-item__meta muted">
                        <span className="mono truncate" title={sid}>{shortId(sid, 12)}</span>
                        <span>{routeLabelRu(routeKey)}</span>
                        <span>msg {row.message_count ?? 0}</span>
                        <span>role {row.role || '—'}</span>
                        <span>course {row.course_id ?? '—'}</span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </section>

          <section className="logs-right card logs-right--conversations">
            {list.total === 0 ? (
              <div className="flex h-full items-center justify-center text-ai-text-muted text-sm">
                Нет диалогов для просмотра.
              </div>
            ) : detailLoading && !detail ? (
              <div className="flex h-full items-center justify-center text-ai-text-muted">
                <span className="mr-2 inline-block animate-pulse">●</span>
                Загрузка деталей…
              </div>
            ) : detailError ? (
              <div className="panel panel--error ai-error text-sm" role="alert">{detailError}</div>
            ) : detail && selectedId ? (
              <DialogDetail detail={detail} />
            ) : null}
          </section>
        </div>
      )}
    </div>
  );
}
