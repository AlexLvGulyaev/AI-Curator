import { useEffect, useMemo, useRef, useState } from 'react';
import { exportAuditLog, getAuditEntry, getAuditLog } from '../api/backend';
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
    <div className="grid grid-cols-[7rem_1fr] items-baseline gap-2 text-xs leading-tight min-w-0">
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

function AuditDetail({ entry }) {
  return (
    <div className="ai-card flex h-full flex-col overflow-hidden p-2">
      <div className="mb-2 flex items-center justify-between border-b border-ai-border pb-2">
        <h3 className="ai-section__title">ДЕТАЛИЗАЦИЯ СОБЫТИЯ</h3>
        <span className="ai-status ai-status--ok">{entry.action}</span>
      </div>

      <div className="flex h-full min-h-0 flex-col gap-2 pr-1">
        <div className="grid grid-cols-2 gap-2 shrink-0">
          <SectionBox title="Параметры акции">
            <div className="space-y-1">
              <CompactRow label="ID акции" value={String(entry.id)} mono />
              <CompactRow label="Тип акции" value={entry.action} />
              <CompactRow label="ID ресурса" value={entry.resource_id} mono />
              <CompactRow label="Тип ресурса" value={entry.resource_type} />
            </div>
          </SectionBox>

          <SectionBox title="Параметры пользователя">
            <div className="space-y-1">
              <CompactRow label="ID пользователя" value={entry.user_id} mono />
              <CompactRow label="Имя пользователя" value={entry.user_name} />
              <CompactRow label="IP-адрес" value={entry.ip_address} mono />
              <CompactRow label="Дата события" value={formatTimestampMsk(entry.created_at)} />
            </div>
          </SectionBox>
        </div>

        <SectionBox title="Детали / metadata" className="min-h-0">
          <pre className="max-h-[200px] overflow-auto whitespace-pre-wrap break-words rounded-ai bg-black/20 p-2 text-xs text-ai-text">
            {formatDetailsJson(entry.details)}
          </pre>
        </SectionBox>

        <SessionJsonSnapshot
          className="shrink-0"
          body={entry}
          summaryLabel="Технический снимок события (JSON)"
        />
      </div>
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
  const [exporting, setExporting] = useState(false);

  const listRef = useRef(null);
  const pendingListFocusRef = useRef(false);
  const pendingPageSelectIndexRef = useRef(null);

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
    if (pendingPageSelectIndexRef.current == null) return;
    if (entries.length) {
      const idx = pendingPageSelectIndexRef.current;
      pendingPageSelectIndexRef.current = null;
      const target = entries[idx] || entries[entries.length - 1] || entries[0];
      if (target?.id) {
        pendingListFocusRef.current = true;
        setSelectedId(target.id);
      }
    }
  }, [entries]);

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

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const safePageIdx = Math.min(pageIndex, Math.max(0, totalPages - 1));

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
      const t = e.target;
      if (t && (t.closest('input') || t.closest('textarea') || t.closest('select') || t.isContentEditable)) {
        return;
      }
      const curIdx = selectedId ? entries.findIndex((s) => String(s.id) === String(selectedId)) : 0;
      if (curIdx < 0) return;
      if (e.key === 'ArrowDown') {
        if (curIdx + 1 < entries.length) {
          const next = entries[curIdx + 1];
          if (!next?.id) return;
          e.preventDefault();
          pendingListFocusRef.current = true;
          setSelectedId(next.id);
          return;
        }
        if (safePageIdx + 1 < totalPages) {
          e.preventDefault();
          pendingPageSelectIndexRef.current = 0;
          setPageIndex((p) => p + 1);
        }
        return;
      }
      if (e.key === 'ArrowUp') {
        if (curIdx > 0) {
          const next = entries[curIdx - 1];
          if (!next?.id) return;
          e.preventDefault();
          pendingListFocusRef.current = true;
          setSelectedId(next.id);
          return;
        }
        if (safePageIdx > 0) {
          e.preventDefault();
          pendingPageSelectIndexRef.current = PAGE_SIZE - 1;
          setPageIndex((p) => p - 1);
        }
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [entries, selectedId, safePageIdx, total, totalPages]);

  useEffect(() => {
    if (pageIndex !== safePageIdx) setPageIndex(safePageIdx);
  }, [pageIndex, safePageIdx]);

  const resetFilters = () => {
    pendingListFocusRef.current = true;
    setPageIndex(0);
    setActionFilter('');
    setResourceTypeFilter('');
    setUserFilter('');
    setWindowLabel('24h');
    const first = entries[0]?.id || null;
    if (first) setSelectedId(first);
  };

  async function handleExport() {
    if (exporting) return;
    setExporting(true);
    setError(null);
    try {
      const blob = await exportAuditLog({
        date_from: dateFrom || undefined,
        action: actionFilter.trim() || undefined,
        resource_type: resourceTypeFilter.trim() || undefined,
        user_id: userFilter.trim() || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ai_curator_audit_${windowLabel}_${new Date().toISOString().slice(0, 10)}.csv`;
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

  const pageEntries = entries;

  function renderList() {
    if (loading && entries.length === 0) {
      return (
        <div className="flex h-48 items-center justify-center text-ai-text-muted">
          <span className="mr-2 inline-block animate-pulse">●</span>
          Загрузка журнала аудита…
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
    if (entries.length === 0) {
      return (
        <div className="flex h-48 items-center justify-center text-ai-text-muted text-sm">
          За выбранный период записей не найдены.
        </div>
      );
    }
    return (
      <div className="flex-1 overflow-y-auto pr-1 min-h-0" ref={listRef}>
        <div className="flex flex-col gap-2">
          {pageEntries.map((entry) => {
            const eid = String(entry.id);
            const isSelected = selectedId === entry.id;
            return (
              <button
                key={eid}
                type="button"
                data-audit-id={eid}
                onClick={() => {
                  pendingListFocusRef.current = true;
                  setSelectedId(entry.id);
                }}
                className={`text-left rounded-ai border p-2 transition-colors ${
                  isSelected
                    ? 'border-ai-primary bg-ai-primary-light'
                    : 'border-ai-border bg-ai-surface hover:border-ai-primary'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-xs text-ai-text-muted">
                    {entry.created_at ? formatTimestampMsk(entry.created_at) : '—'}
                  </span>
                  <span className="ai-status ai-status--ok text-[0.65rem]">{entry.action}</span>
                </div>
                <div className="text-sm font-medium text-ai-text line-clamp-2 mb-1">
                  {entry.resource_type || '—'}
                </div>
                <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-ai-text-secondary">
                  <span className="mono">#{entry.id}</span>
                  <span>{entry.user_name || entry.user_id || '—'}</span>
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
          <div className="ai-empty">Выберите audit-запись для просмотра.</div>
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
    return <AuditDetail entry={detail} />;
  }

  return (
    <div className="ai-config-page flex h-full flex-col">
      <div className="ai-page__header border-b border-ai-border">
        <div>
          <h1 className="ai-page__title">Журнал аудита</h1>
          <p className="ai-page__subtitle">Административные действия и изменения</p>
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
            <input
              type="text"
              className="ai-input w-auto min-w-[120px] flex-1 text-sm"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              placeholder="action"
              aria-label="Фильтр действия"
            />
            <input
              type="text"
              className="ai-input w-auto min-w-[120px] flex-1 text-sm"
              value={resourceTypeFilter}
              onChange={(e) => setResourceTypeFilter(e.target.value)}
              placeholder="resource_type"
              aria-label="Фильтр типа ресурса"
            />
          </div>

          <input
            type="text"
            className="ai-input w-full mb-2 text-sm"
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            placeholder="Поиск по user_id или user_name"
            aria-label="Поиск по пользователю"
          />

          <div className="mb-2 flex items-center justify-between border-b border-ai-border pb-2 text-xs">
            <button
              type="button"
              onClick={() => setPageIndex((p) => Math.max(0, p - 1))}
              disabled={safePageIdx <= 0 || total === 0}
              className="ai-btn-outline rounded-ai px-2 py-1"
            >
              ← Назад
            </button>
            <span className="text-ai-text-secondary">
              Страница {safePageIdx + 1} из {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setPageIndex((p) => Math.min(totalPages - 1, p + 1))}
              disabled={safePageIdx >= totalPages - 1 || total === 0}
              className="ai-btn-outline rounded-ai px-2 py-1"
            >
              Вперёд →
            </button>
          </div>

          <div className="mb-2 flex items-center justify-between text-xs text-ai-text-secondary">
            <span>Всего {total}</span>
            <button
              type="button"
              onClick={resetFilters}
              disabled={
                safePageIdx === 0 &&
                !actionFilter.trim() &&
                !resourceTypeFilter.trim() &&
                !userFilter.trim() &&
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
