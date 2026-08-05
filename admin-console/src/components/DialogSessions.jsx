import { useEffect, useMemo, useRef, useState } from 'react';
import { exportDialogSessions, getDialogSession, getDialogSessions } from '../api/backend';
import OperationalModalityBadge from './OperationalModalityBadge';
import OperationalPipelineStageIcon from './OperationalPipelineStageIcon';
import SessionJsonSnapshot from './SessionJsonSnapshot';
import { formatDetailsJson } from '../utils/operationalConsoleUi';
import {
  formatDurationMs,
  formatTimeMsk,
  formatTimestampMsk,
  normalizeStatus,
  routeLabelRu,
  shortId,
  shortModelName,
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

function toTs(iso) {
  if (!iso) return null;
  const n = new Date(iso).getTime();
  return Number.isFinite(n) ? n : null;
}

function stripSourcesFromAnswer(answer) {
  if (!answer) return '';
  const marker = '### Источники';
  const idx = answer.indexOf(marker);
  if (idx === -1) return answer;
  return answer.slice(0, idx).trim();
}

function turnMode(turn, sessionMode) {
  const intent = String(turn.intent || '').trim().toLowerCase();
  const hasLms = Array.isArray(turn.lms_calls) && turn.lms_calls.length > 0;
  const hasRag = turn.rag_filters && Object.keys(turn.rag_filters).length > 0;
  if (hasLms && hasRag) return 'mixed';
  if (hasLms) return 'lms';
  if (hasRag) return 'rag';
  if (intent === 'organizational' || intent === 'progress' || intent === 'deadline') return 'lms';
  if (intent === 'study') return 'rag';
  if (intent === 'mixed') return 'mixed';
  return sessionMode || 'text';
}

function pairDialogRows(turns, executions, sessionMode) {
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
          mode: sessionMode || '—',
          model: t.llm_model || '—',
          created_at: pendingUser.created_at,
        });
      }
      pendingUser = { content: userMsg, created_at: ts, request_id: t.request_id };
    }
    if (assistantMsg != null) {
      const ex = findExecutionForRequest(executions, pendingUser?.request_id);
      rows.push({
        user: pendingUser?.content || '—',
        assistant: stripSourcesFromAnswer(assistantMsg),
        cache_hit: t.cache_hit ?? null,
        response_time_ms: t.latency_ms ?? ex?.duration_ms ?? null,
        execution_id: ex?.id ?? null,
        sources: t.sources,
        mode: turnMode(t, sessionMode),
        model: t.llm_model || ex?.model_name || '—',
        created_at: ts,
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
      mode: sessionMode || '—',
      model: '—',
      created_at: pendingUser.created_at,
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
    () => pairDialogRows(detail.turns || [], detail.execution_sessions || [], detail.mode),
    [detail.turns, detail.execution_sessions, detail.mode]
  );
  const latestExecution = detail.execution_sessions?.[detail.execution_sessions.length - 1] || null;
  const budget = detail.budget || {};
  const runtime = latestExecution || {};

  return (
    <div className="ai-card flex h-full flex-col overflow-hidden p-2">
      <div className="mb-2 flex items-center justify-between border-b border-ai-border pb-2">
        <h3 className="ai-section__title">ДЕТАЛИЗАЦИЯ ДИАЛОГА</h3>
        <ActiveBadge active={detail.is_active} />
      </div>

      <div className="flex h-full min-h-0 flex-col gap-2 pr-1">
        <div className="grid grid-cols-3 gap-2 shrink-0">
          <SectionBox title="Параметры сессии">
            <div className="space-y-1">
              <CompactRow label="Сессия" value={shortId(detail.session_id, 12)} mono />
              <CompactRow label="IP" value={runtime.client_ip} mono />
              <CompactRow label="Режим" value={routeLabelRu(detail.mode)} />
              <CompactRow label="Активна" value={detail.is_active ? 'да' : 'нет'} />
              <CompactRow label="Сообщений" value={String(detail.message_count ?? 0)} />
              <CompactRow label="Обменов" value={String(dialogRows.length)} />
              <CompactRow
                label="Обновлена"
                value={detail.last_message_at ? formatTimestampMsk(detail.last_message_at) : '—'}
              />
            </div>
          </SectionBox>

          <SectionBox title="Параметры исполнения">
            <div className="space-y-1">
              <CompactRow label="RAG" value={detail.mode === 'rag' || detail.mode === 'mixed' ? 'да' : 'нет'} />
              <CompactRow
                label="Провайдер / Модель"
                value={`${runtime.provider_key || '—'} / ${runtime.model_name || budget.model || '—'}`}
                mono
              />
              <CompactRow label="Время ответа" value={formatDurationMs(runtime.duration_ms)} />
              <CompactRow label="Источник" value={detail.memory_source || 'PostgreSQL'} mono />
              <CompactRow label="Маршрут" value={runtime.route || '—'} mono />
              <CompactRow label="Кэш" value={runtime.execution_metadata?.cache_hit ? 'да' : 'нет'} />
            </div>
          </SectionBox>

          <SectionBox title="Лимиты / политика">
            <div className="space-y-1">
              <CompactRow label="Модель" value={budget.model} mono />
              <CompactRow label="Max tokens" value={String(budget.max_tokens ?? '—')} />
              <CompactRow label="Temperature" value={budget.temperature != null ? String(budget.temperature) : '—'} />
            </div>
          </SectionBox>
        </div>

        <SectionBox title="Диалог сессии" className="flex-1 min-h-0">
          <p className="text-xs text-ai-text-secondary mb-1.5">
            Парные реплики по времени; последние события сверху.
          </p>
          <div className="memory-dialog-table-wrap">
            <table className="memory-dialog-table">
              <colgroup>
                <col className="memory-dialog-table__col--query" />
                <col className="memory-dialog-table__col--answer" />
                <col className="memory-dialog-table__col--mode" />
                <col className="memory-dialog-table__col--latency" />
                <col className="memory-dialog-table__col--cache" />
                <col className="memory-dialog-table__col--model" />
                <col className="memory-dialog-table__col--time" />
              </colgroup>
              <thead>
                <tr>
                  <th>Запрос пользователя</th>
                  <th>Ответ системы</th>
                  <th className="memory-dialog-table__col--narrow">Режим</th>
                  <th className="memory-dialog-table__col--narrow">Время ответа</th>
                  <th className="memory-dialog-table__col--narrow">Кэш</th>
                  <th className="memory-dialog-table__col--narrow">Модель</th>
                  <th className="memory-dialog-table__col--narrow">Время запроса</th>
                </tr>
              </thead>
              <tbody>
                {dialogRows.length ? (
                  dialogRows
                    .slice()
                    .reverse()
                    .map((row, i) => (
                      <tr key={i}>
                        <td className="memory-dialog-table__cell memory-dialog-table__cell--query memory-dialog-table__cell--user">{row.user}</td>
                        <td className="memory-dialog-table__cell memory-dialog-table__cell--answer memory-dialog-table__cell--assistant">
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
                          {routeLabelRu(row.mode)}
                        </td>
                        <td className="memory-dialog-table__cell memory-dialog-table__cell--runtime">
                          {formatDurationMs(row.response_time_ms)}
                        </td>
                        <td className="memory-dialog-table__cell memory-dialog-table__cell--runtime">
                          {row.cache_hit === null ? '—' : row.cache_hit ? 'hit' : 'miss'}
                        </td>
                        <td className="memory-dialog-table__cell memory-dialog-table__cell--runtime" title={row.model}>
                          {shortModelName(row.model)}
                        </td>
                        <td className="memory-dialog-table__cell memory-dialog-table__cell--runtime">
                          {row.created_at ? formatTimeMsk(row.created_at) : '—'}
                        </td>
                      </tr>
                    ))
                ) : (
                  <tr>
                    <td colSpan={7} className="muted memory-dialog-table__empty">
                      Нет user/assistant сообщений.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </SectionBox>

        {latestExecution ? (
          <details className="memory-timeline-fold shrink-0">
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
                      {delta != null && delta > 0 ? (
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
          className="shrink-0"
          body={detail}
          summaryLabel="Технический снимок диалога (JSON)"
        />
      </div>
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
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);
  const [exporting, setExporting] = useState(false);

  const listRef = useRef(null);
  const pendingListFocusRef = useRef(false);
  const pendingPageSelectIndexRef = useRef(null);

  const hours = useMemo(
    () => WINDOW_OPTIONS.find((w) => w.label === windowLabel)?.value ?? null,
    [windowLabel]
  );

  const filters = useMemo(
    () => {
      const params = {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      };
      if (hours != null) params.hours = hours;
      if (modeFilter !== 'all') params.mode = modeFilter;
      if (activeFilter === 'active') params.active_only = true;
      if (activeFilter === 'inactive') params.active_only = false;
      if (searchQuery.trim()) params.search = searchQuery.trim();
      return params;
    },
    [hours, modeFilter, activeFilter, searchQuery, page]
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getDialogSessions(filters)
      .then((data) => {
        if (cancelled) return;
        setList(data);
        if (pendingPageSelectIndexRef.current != null) {
          const idx = pendingPageSelectIndexRef.current;
          pendingPageSelectIndexRef.current = null;
          const target = data.items[idx] || data.items[data.items.length - 1] || data.items[0];
          if (target?.session_id) {
            pendingListFocusRef.current = true;
            setSelectedId(target.session_id);
            return;
          }
        }
        if (data.items.length && !selectedId) {
          setSelectedId(data.items[0].session_id);
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
  }, [filters, refreshNonce, selectedId]);

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
    setPage(0);
  }, [searchQuery, activeFilter, modeFilter, windowLabel]);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
      const t = e.target;
      if (t && (t.closest('input') || t.closest('textarea') || t.closest('select') || t.isContentEditable)) {
        return;
      }
      if (!list.items.length) return;
      const totalPages = Math.max(1, Math.ceil(list.total / PAGE_SIZE));
      const curIdx = selectedId ? list.items.findIndex((s) => s.session_id === selectedId) : 0;
      if (curIdx < 0) return;
      if (e.key === 'ArrowDown') {
        if (curIdx + 1 < list.items.length) {
          const next = list.items[curIdx + 1];
          if (!next?.session_id) return;
          e.preventDefault();
          pendingListFocusRef.current = true;
          setSelectedId(next.session_id);
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
          const next = list.items[curIdx - 1];
          if (!next?.session_id) return;
          e.preventDefault();
          pendingListFocusRef.current = true;
          setSelectedId(next.session_id);
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
  }, [list.items, selectedId, page, list.total]);

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
  }, [selectedId, page]);

  const totalPages = Math.max(1, Math.ceil(list.total / PAGE_SIZE));
  const safePageIdx = Math.min(page, Math.max(0, totalPages - 1));

  useEffect(() => {
    if (page !== safePageIdx) setPage(safePageIdx);
  }, [page, safePageIdx]);

  function resetFilters() {
    pendingListFocusRef.current = true;
    setPage(0);
    setSearchQuery('');
    setActiveFilter('all');
    setModeFilter('all');
    setWindowLabel('24h');
    const first = list.items[0]?.session_id || null;
    if (first) setSelectedId(first);
  }

  async function handleExport() {
    if (exporting) return;
    setExporting(true);
    setError(null);
    try {
      const params = {};
      if (hours != null) params.hours = hours;
      if (modeFilter !== 'all') params.mode = modeFilter;
      if (activeFilter === 'active') params.active_only = true;
      if (activeFilter === 'inactive') params.active_only = false;
      if (searchQuery.trim()) params.search = searchQuery.trim();
      const blob = await exportDialogSessions(params);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ai_curator_dialog_sessions_${windowLabel}_${new Date().toISOString().slice(0, 10)}.csv`;
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
    if (loading && list.items.length === 0) {
      return (
        <div className="flex h-48 items-center justify-center text-ai-text-muted">
          <span className="mr-2 inline-block animate-pulse">●</span>
          Загрузка сессий…
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
    if (list.items.length === 0) {
      return (
        <div className="flex h-48 items-center justify-center text-ai-text-muted">
          При пустой БД список пуст.
        </div>
      );
    }
    return (
      <div className="flex-1 overflow-y-auto pr-1 min-h-0" ref={listRef}>
        <div className="flex flex-col gap-2">
          {list.items.map((row) => {
            const sid = row.session_id;
            const isSelected = selectedId === sid;
            return (
              <button
                key={sid}
                type="button"
                data-session-id={sid}
                onClick={() => {
                  pendingListFocusRef.current = true;
                  setSelectedId(sid);
                }}
                className={`text-left rounded-ai border p-2 transition-colors ${
                  isSelected
                    ? 'border-ai-primary bg-ai-primary-light'
                    : 'border-ai-border bg-ai-surface hover:border-ai-primary'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-xs text-ai-text-muted">
                    {row.last_message_at ? formatTimestampMsk(row.last_message_at) : '—'}
                  </span>
                  <div className="flex items-center gap-1">
                    <OperationalModalityBadge modality={row.mode} />
                    <ActiveBadge active={row.is_active !== false} />
                  </div>
                </div>
                <div className="text-sm font-medium text-ai-text line-clamp-2 mb-1">session: {shortId(sid, 12)}</div>
                <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-ai-text-secondary">
                  {row.role ? <span>роль {row.role}</span> : null}
                  {row.course_id != null ? <span>курс {row.course_id}</span> : null}
                  <span>сообщений {row.message_count ?? 0}</span>
                  <span>{routeLabelRu(row.mode)}</span>
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
          <div className="ai-empty">Выберите сессию для просмотра деталей.</div>
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
    return <DialogDetail detail={detail} />;
  }

  return (
    <div className="ai-config-page flex h-full flex-col">
      <div className="ai-page__header border-b border-ai-border">
        <div>
          <h1 className="ai-page__title">Диалоги</h1>
          <p className="ai-page__subtitle">Операционная консоль диалоговых сессий</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleExport}
            disabled={exporting || loading}
            className="ai-btn-outline rounded-ai px-3 py-1.5 text-sm disabled:opacity-60"
          >
            {exporting ? 'Экспорт…' : 'Экспорт CSV'}
          </button>
          <button
            type="button"
            onClick={() => setRefreshNonce((n) => n + 1)}
            className="ai-btn-outline rounded-ai px-3 py-1.5 text-sm"
            disabled={loading}
          >
            {loading ? '…' : 'Обновить'}
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="ai-card flex h-full w-[420px] flex-col overflow-hidden p-3 pb-2">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <select
              className="ai-select w-auto min-w-[120px] flex-1 text-sm"
              value={windowLabel}
              onChange={(e) => setWindowLabel(e.target.value)}
              aria-label="Окно времени"
            >
              {WINDOW_OPTIONS.map((w) => (
                <option key={w.label} value={w.label}>{w.label}</option>
              ))}
            </select>
            <select
              className="ai-select w-auto min-w-[120px] flex-1 text-sm"
              value={modeFilter}
              onChange={(e) => setModeFilter(e.target.value)}
              aria-label="Режим сессии"
            >
              {MODE_OPTIONS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
            <select
              className="ai-select w-auto min-w-[120px] flex-1 text-sm"
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
            className="ai-input w-full mb-2 text-sm"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Поиск: session_id, role…"
            aria-label="Поиск сессий"
          />

          <div className="mb-2 flex items-center justify-between border-b border-ai-border pb-2 text-xs">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={safePageIdx <= 0 || list.total === 0}
              className="ai-btn-outline rounded-ai px-2 py-1"
            >
              ← Назад
            </button>
            <span className="text-ai-text-secondary">
              Страница {safePageIdx + 1} из {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={safePageIdx >= totalPages - 1 || list.total === 0}
              className="ai-btn-outline rounded-ai px-2 py-1"
            >
              Вперёд →
            </button>
          </div>

          <div className="mb-2 flex items-center justify-between text-xs text-ai-text-secondary">
            <span>Всего {list.total}</span>
            <button
              type="button"
              onClick={resetFilters}
              disabled={
                safePageIdx === 0 &&
                !searchQuery.trim() &&
                activeFilter === 'all' &&
                modeFilter === 'all' &&
                windowLabel === '24h'
              }
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
