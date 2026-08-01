import { useEffect, useMemo, useRef, useState } from 'react';
import { getAuditEntry, getAuditLog } from '../api/backend';
import SessionJsonSnapshot from './SessionJsonSnapshot';
import { formatDetailsJson } from '../utils/operationalConsoleUi';
import { formatTimestampMsk, shortId } from '../utils/operationalLabels';

const PAGE_SIZE = 7;
const WINDOW_OPTIONS = [
  { label: '24h', value: 24 },
  { label: '7d', value: 168 },
  { label: '30d', value: 720 },
  { label: 'все', value: null },
];

function isoDate(offsetHours) {
  if (offsetHours == null) return '';
  const d = new Date();
  d.setHours(d.getHours() - offsetHours);
  return d.toISOString().slice(0, 10);
}

function OpsRow({ label, value }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </>
  );
}

function AuditDetail({ entry }) {
  return (
    <div className="logs-detail">
      <div className="logs-detail__head">
        <div>
          <h2 className="logs-detail__title">Audit-запись</h2>
          <p className="logs-detail__sub muted">{shortId(String(entry.id), 16)}</p>
        </div>
        <span className="ai-status ai-status--ok">OK</span>
      </div>

      <div className="logs-summary-grid">
        <div className="logs-summary-col">
          <dl className="kv logs-detail-kv">
            <OpsRow label="action" value={<span className="mono">{entry.action}</span>} />
            <OpsRow label="resource_type" value={<span className="mono">{entry.resource_type}</span>} />
            <OpsRow label="resource_id" value={<span className="mono break-all">{entry.resource_id || '—'}</span>} />
            <OpsRow label="user_id" value={<span className="mono">{entry.user_id || '—'}</span>} />
          </dl>
        </div>
        <div className="logs-summary-col">
          <dl className="kv logs-detail-kv">
            <OpsRow label="user_name" value={<span className="mono">{entry.user_name || '—'}</span>} />
            <OpsRow label="ip_address" value={<span className="mono">{entry.ip_address || '—'}</span>} />
            <OpsRow
              label="Создано"
              value={
                entry.created_at ? (
                  <span className="mono">{formatTimestampMsk(entry.created_at)}</span>
                ) : (
                  '—'
                )
              }
            />
          </dl>
        </div>
      </div>

      <div className="logs-detail-block page__mt">
        <h3 className="logs-detail-block__title">Metadata / details</h3>
        <pre className="logs-pre mono">{formatDetailsJson(entry.details)}</pre>
      </div>

      <SessionJsonSnapshot
        className="page__mt"
        body={entry}
        summaryLabel="Технический снимок audit-записи (JSON)"
      />
    </div>
  );
}

export default function AuditLog() {
  const [entries, setEntries] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [windowLabel, setWindowLabel] = useState('24h');
  const [actionFilter, setActionFilter] = useState('');
  const [resourceTypeFilter, setResourceTypeFilter] = useState('');
  const [userFilter, setUserFilter] = useState('');
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
  const dateFrom = useMemo(() => isoDate(hours), [hours, refreshNonce]);

  const loadList = useMemo(
    () => async () => {
      setLoading(true);
      setError(null);
      try {
        const params = {
          limit: PAGE_SIZE,
          offset: pageIndex * PAGE_SIZE,
        };
        if (dateFrom) params.date_from = dateFrom;
        if (actionFilter.trim()) params.action = actionFilter.trim();
        if (resourceTypeFilter.trim()) params.resource_type = resourceTypeFilter.trim();
        if (userFilter.trim()) params.user_id = userFilter.trim();
        const data = await getAuditLog(params);
        const items = Array.isArray(data) ? data : data.items || [];
        const t = Array.isArray(data) ? items.length : data.total || 0;
        setEntries(items);
        setTotal(t);
      } catch (e) {
        setEntries([]);
        setTotal(0);
        setError(e instanceof Error ? e.message : 'Ошибка загрузки журнала аудита');
      } finally {
        setLoading(false);
      }
    },
    [dateFrom, actionFilter, resourceTypeFilter, userFilter, pageIndex, refreshNonce]
  );

  useEffect(() => {
    loadList();
  }, [loadList]);

  useEffect(() => {
    setPageIndex(0);
  }, [windowLabel, actionFilter, resourceTypeFilter, userFilter, refreshNonce]);

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
        const d = await getAuditEntry(selectedId);
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
    if (entries.length === 0) {
      if (selectedId) setSelectedId(null);
      return;
    }
    const inList = selectedId ? entries.some((e) => String(e.id) === String(selectedId)) : false;
    if (!selectedId || !inList) {
      setSelectedId(entries[0].id);
    }
  }, [loading, error, entries, selectedId]);

  useEffect(() => {
    if (!selectedId) return;
    const listEl = listRef.current;
    if (!listEl) return;
    const safeId =
      typeof CSS !== 'undefined' && typeof CSS.escape === 'function'
        ? CSS.escape(String(selectedId))
        : String(selectedId).replace(/"/g, '\\"');
    const row = listEl.querySelector(`[data-audit-id="${safeId}"]`);
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
      if (!entries.length) return;
      const curIdx = selectedId ? entries.findIndex((s) => String(s.id) === String(selectedId)) : 0;
      if (curIdx < 0) return;
      const nextIdx =
        e.key === 'ArrowDown'
          ? Math.min(entries.length - 1, curIdx + 1)
          : Math.max(0, curIdx - 1);
      if (nextIdx === curIdx) return;
      e.preventDefault();
      const next = entries[nextIdx];
      if (!next?.id) return;
      pendingListFocusRef.current = true;
      setPageIndex(Math.floor(nextIdx / PAGE_SIZE));
      setSelectedId(next.id);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [entries, selectedId]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const safePageIdx = Math.min(pageIndex, Math.max(0, totalPages - 1));

  useEffect(() => {
    if (pageIndex !== safePageIdx) setPageIndex(safePageIdx);
  }, [pageIndex, safePageIdx]);

  const pageEntries = useMemo(() => {
    const start = safePageIdx * PAGE_SIZE;
    return entries.slice(start, start + PAGE_SIZE);
  }, [entries, safePageIdx]);

  const goPrevPage = () => {
    pendingListFocusRef.current = true;
    const np = Math.max(0, safePageIdx - 1);
    setPageIndex(np);
    const pick = entries[np * PAGE_SIZE]?.id || null;
    if (pick) setSelectedId(pick);
  };

  const goNextPage = () => {
    pendingListFocusRef.current = true;
    const np = Math.min(totalPages - 1, safePageIdx + 1);
    setPageIndex(np);
    const pick = entries[np * PAGE_SIZE]?.id || null;
    if (pick) setSelectedId(pick);
  };

  const resetPagination = () => {
    pendingListFocusRef.current = true;
    setPageIndex(0);
    setActionFilter('');
    setResourceTypeFilter('');
    setUserFilter('');
    setWindowLabel('24h');
    const first = entries[0]?.id || null;
    if (first) setSelectedId(first);
  };

  const listMetaLine = `Страница ${safePageIdx + 1} из ${totalPages} · записей: ${total} · показано: ${pageEntries.length}`;

  return (
    <div className="page logs-page">
      <div className="flex items-start justify-between border-b border-ai-border pb-3 mb-3">
        <div>
          <h1 className="font-display text-xl font-bold text-ai-text">Журнал аудита</h1>
          <p className="page__lead muted text-sm">Административные действия и изменения</p>
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
        <div className="logs-console">
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
                <input
                  type="text"
                  className="logs-select"
                  value={actionFilter}
                  onChange={(e) => setActionFilter(e.target.value)}
                  placeholder="action"
                  aria-label="Фильтр действия"
                />
                <input
                  type="text"
                  className="logs-select"
                  value={resourceTypeFilter}
                  onChange={(e) => setResourceTypeFilter(e.target.value)}
                  placeholder="resource_type"
                  aria-label="Фильтр типа ресурса"
                />
              </div>
              <input
                type="text"
                className="logs-search"
                value={userFilter}
                onChange={(e) => setUserFilter(e.target.value)}
                placeholder="Поиск по user_id или user_name"
                aria-label="Поиск по пользователю"
              />
              <div className="logs-filter-meta logs-filter-meta--with-refresh muted">
                <span>{listMetaLine}</span>
              </div>
              <div className="logs-page-controls">
                <button
                  type="button"
                  className="logs-page-btn"
                  onClick={goPrevPage}
                  disabled={safePageIdx <= 0 || total === 0}
                >
                  ← Предыдущая
                </button>
                <button
                  type="button"
                  className="logs-page-btn"
                  onClick={goNextPage}
                  disabled={safePageIdx >= totalPages - 1 || total === 0}
                >
                  Следующая →
                </button>
                <button
                  type="button"
                  className="logs-page-btn logs-page-btn--muted"
                  onClick={resetPagination}
                  disabled={
                    safePageIdx === 0 &&
                    !actionFilter.trim() &&
                    !resourceTypeFilter.trim() &&
                    !userFilter.trim() &&
                    windowLabel === '24h'
                  }
                >
                  Сброс
                </button>
              </div>
            </div>

            <div className="logs-list" ref={listRef}>
              {loading && entries.length === 0 ? (
                <div className="flex h-48 items-center justify-center text-ai-text-muted">
                  <span className="mr-2 inline-block animate-pulse">●</span>
                  Загрузка журнала аудита…
                </div>
              ) : entries.length === 0 ? (
                <div className="flex h-48 items-center justify-center text-ai-text-muted text-sm">
                  За выбранный период записей не найдены.
                </div>
              ) : (
                pageEntries.map((entry) => {
                  const eid = String(entry.id);
                  const preview = entry.details
                    ? formatDetailsJson(entry.details).slice(0, 60)
                    : '—';
                  return (
                    <button
                      key={eid}
                      type="button"
                      data-audit-id={eid}
                      className={`logs-item ${selectedId === entry.id ? 'logs-item--selected' : ''}`}
                      onClick={() => {
                        pendingListFocusRef.current = true;
                        setSelectedId(entry.id);
                      }}
                    >
                      <div className="logs-item__row logs-item__row--tight">
                        <span className="mono logs-item__ts">
                          {entry.created_at ? formatTimestampMsk(entry.created_at) : '—'}
                        </span>
                        <span className="ai-status ai-status--ok text-[0.65rem]">{entry.action}</span>
                      </div>
                      <div className="logs-item__preview">
                        {entry.resource_type}
                        {entry.resource_id ? ` · ${shortId(entry.resource_id, 24)}` : ''}
                      </div>
                      <div className="logs-item__row logs-item__meta muted">
                        <span className="mono">#{entry.id}</span>
                        <span>{entry.user_name || entry.user_id || '—'}</span>
                        <span className="truncate max-w-[180px]" title={preview}>{preview}</span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </section>

          <section className="logs-right card">
            {entries.length === 0 ? (
              <div className="flex h-full items-center justify-center text-ai-text-muted text-sm">
                Выберите audit-запись для просмотра.
              </div>
            ) : detailLoading && !detail ? (
              <div className="flex h-full items-center justify-center text-ai-text-muted">
                <span className="mr-2 inline-block animate-pulse">●</span>
                Загрузка деталей…
              </div>
            ) : detailError ? (
              <div className="panel panel--error ai-error text-sm" role="alert">{detailError}</div>
            ) : detail && selectedId ? (
              <AuditDetail entry={detail} />
            ) : null}
          </section>
        </div>
      )}
    </div>
  );
}
