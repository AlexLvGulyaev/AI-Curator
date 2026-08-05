import { useEffect, useMemo, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip as ReTooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import {
  getReportsQuality,
  getReportsUnanswered,
  getReportsKbGaps,
  getReportsPopularTopics,
  getReportsKbCoverage,
  getReportsExpansionCandidates,
  exportReportsReport,
} from '../api/backend';

const INTENT_LABELS = {
  deadline: 'Дедлайн',
  progress: 'Прогресс',
  mixed: 'Смешанный',
  study: 'Учёба',
  organizational: 'Организационный',
  out_of_scope: 'Не распределено',
  error: 'Ошибка',
  unknown: 'Не определён',
};

const TABS = [
  { id: 'quality', label: 'Качество' },
  { id: 'unanswered', label: 'Без ответа' },
  { id: 'kb-gaps', label: 'Гэпы KB' },
  { id: 'popular-topics', label: 'Популярные темы' },
  { id: 'kb-coverage', label: 'Покрытие KB' },
  { id: 'expansion', label: 'Кандидаты' },
];

function formatDateInput(d) {
  const tzOffset = d.getTimezoneOffset() * 60000;
  const local = new Date(d.getTime() - tzOffset);
  return local.toISOString().split('T')[0];
}

function MetricCard({ label, value, variant = 'default', compact = false, suffix = '' }) {
  const valueClass =
    variant === 'error'
      ? 'text-ai-error'
      : variant === 'success'
      ? 'text-ai-success'
      : 'text-ai-text';
  return (
    <div className={`ai-card flex w-full flex-col justify-between ${compact ? 'p-3' : 'p-5'}`}>
      <p className={`text-ai-text-muted ${compact ? 'text-[0.65rem] uppercase tracking-wide' : 'text-xs'}`}>
        {label}
      </p>
      <p className={`font-semibold ${compact ? 'text-xl leading-tight' : 'text-3xl'} ${valueClass}`}>
        {value}
        {suffix && <span className="ml-1 text-sm font-normal text-ai-text-muted">{suffix}</span>}
      </p>
    </div>
  );
}

function FilterBar({ filters, onChange, onApply, loading, onExport, showIntent }) {
  return (
    <div className="ai-card flex flex-wrap items-end gap-2 p-2">
      <div className="flex flex-col gap-0.5">
        <label className="text-[0.65rem] uppercase tracking-wide text-ai-text-muted">С</label>
        <input
          type="date"
          value={filters.date_from}
          onChange={(e) => onChange({ ...filters, date_from: e.target.value })}
          className="ai-input px-2 py-1 text-xs"
        />
      </div>
      <div className="flex flex-col gap-0.5">
        <label className="text-[0.65rem] uppercase tracking-wide text-ai-text-muted">По</label>
        <input
          type="date"
          value={filters.date_to}
          onChange={(e) => onChange({ ...filters, date_to: e.target.value })}
          className="ai-input px-2 py-1 text-xs"
        />
      </div>
      <div className="flex flex-col gap-0.5">
        <label className="text-[0.65rem] uppercase tracking-wide text-ai-text-muted">Курс</label>
        <input
          type="number"
          min={1}
          placeholder="ID курса"
          value={filters.course_id}
          onChange={(e) => onChange({ ...filters, course_id: e.target.value })}
          className="ai-input px-2 py-1 text-xs"
        />
      </div>
      {showIntent && (
        <div className="flex flex-col gap-0.5">
          <label className="text-[0.65rem] uppercase tracking-wide text-ai-text-muted">Интент</label>
          <select
            value={filters.intent}
            onChange={(e) => onChange({ ...filters, intent: e.target.value })}
            className="ai-input px-2 py-1 text-xs"
          >
            <option value="">Все</option>
            {Object.entries(INTENT_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>
      )}
      <div className="flex flex-1 items-center justify-end gap-2">
        <button
          type="button"
          onClick={() =>
            onChange({
              date_from: formatDateInput(new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)),
              date_to: formatDateInput(new Date()),
              course_id: '',
              intent: '',
            })
          }
          className="ai-btn-outline rounded-ai px-2 py-1 text-xs"
        >
          7 дней
        </button>
        <button
          type="button"
          onClick={() =>
            onChange({
              date_from: formatDateInput(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)),
              date_to: formatDateInput(new Date()),
              course_id: '',
              intent: '',
            })
          }
          className="ai-btn-outline rounded-ai px-2 py-1 text-xs"
        >
          30 дней
        </button>
        <button
          type="button"
          onClick={onApply}
          disabled={loading}
          className="ai-btn rounded-ai px-3 py-1 text-xs"
        >
          {loading ? 'Загрузка…' : 'Применить'}
        </button>
        <button
          type="button"
          onClick={onExport}
          disabled={loading}
          className="ai-btn-outline rounded-ai px-3 py-1 text-xs"
        >
          CSV
        </button>
      </div>
    </div>
  );
}

function RequestList({ items, emptyText }) {
  if (items.length === 0) {
    return <p className="text-sm text-ai-text-muted">{emptyText}</p>;
  }
  return (
    <div className="min-h-0 flex-1 overflow-y-auto space-y-2 pr-1">
      {items.map((item) => (
        <div key={item.request_id} className="border-b border-ai-border-subtle pb-2 last:border-0">
          <p className="text-sm text-ai-text">{item.message}</p>
          <p className="text-xs text-ai-text-muted">
            {INTENT_LABELS[item.intent] || item.intent} · курс {item.course_id || '—'} ·{' '}
            {item.created_at ? new Date(item.created_at).toLocaleString('ru-RU') : '—'}
            {item.feedback_score !== null && (
              <span className="ml-2">★ {item.feedback_score}</span>
            )}
          </p>
        </div>
      ))}
    </div>
  );
}

function Paginator({ total, limit, offset, onChange }) {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit) || 1;
  return (
    <div className="mt-2 flex items-center justify-between text-xs text-ai-text-muted">
      <span>
        {offset + 1}–{Math.min(offset + limit, total)} из {total}
      </span>
      <div className="flex gap-1">
        <button
          type="button"
          disabled={offset === 0}
          onClick={() => onChange(Math.max(offset - limit, 0))}
          className="ai-btn-outline rounded-ai px-2 py-1 disabled:opacity-50"
        >
          Назад
        </button>
        <button
          type="button"
          disabled={offset + limit >= total}
          onClick={() => onChange(offset + limit)}
          className="ai-btn-outline rounded-ai px-2 py-1 disabled:opacity-50"
        >
          Вперёд
        </button>
      </div>
    </div>
  );
}

function Reports() {
  const [activeTab, setActiveTab] = useState('quality');
  const [filters, setFilters] = useState({
    date_from: formatDateInput(new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)),
    date_to: formatDateInput(new Date()),
    course_id: '',
    intent: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [quality, setQuality] = useState(null);
  const [unanswered, setUnanswered] = useState({ items: [], total: 0 });
  const [kbGaps, setKbGaps] = useState({ items: [], total: 0 });
  const [popularTopics, setPopularTopics] = useState([]);
  const [kbCoverage, setKbCoverage] = useState(null);
  const [expansion, setExpansion] = useState([]);
  const [offset, setOffset] = useState(0);

  const buildParams = useMemo(() => {
    const params = {};
    if (filters.date_from) params.date_from = filters.date_from;
    if (filters.date_to) params.date_to = filters.date_to;
    if (filters.course_id) params.course_id = filters.course_id;
    if (filters.intent) params.intent = filters.intent;
    return params;
  }, [filters]);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const params = buildParams;
      const listParams = { ...params, limit: 50, offset };
      const [
        qualityData,
        unansweredData,
        kbGapsData,
        popularData,
        coverageData,
        expansionData,
      ] = await Promise.all([
        getReportsQuality(params),
        activeTab === 'unanswered' || activeTab === 'quality'
          ? getReportsUnanswered(listParams)
          : Promise.resolve({ items: [], total: 0 }),
        activeTab === 'kb-gaps' || activeTab === 'expansion'
          ? getReportsKbGaps(listParams)
          : Promise.resolve({ items: [], total: 0 }),
        getReportsPopularTopics({ ...params, limit: 20 }),
        getReportsKbCoverage(),
        getReportsExpansionCandidates({ ...params, limit: 10 }),
      ]);
      setQuality(qualityData);
      setUnanswered(unansweredData);
      setKbGaps(kbGapsData);
      setPopularTopics(
        popularData.map((item) => ({
          ...item,
          label: INTENT_LABELS[item.intent] || item.intent,
        }))
      );
      setKbCoverage(coverageData);
      setExpansion(expansionData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleExport() {
    setLoading(true);
    try {
      const section = activeTab === 'unanswered' || activeTab === 'kb-gaps' ? activeTab : 'all';
      const blob = await exportReportsReport(buildParams, section);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ai_curator_reports_${section}_${filters.date_from || 'all'}_${filters.date_to || 'all'}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let mounted = true;
    loadData().then(() => {
      if (!mounted) return;
    });
    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, offset]);

  const chartTooltipStyle = {
    backgroundColor: '#1e293b',
    borderColor: '#334155',
    color: '#f8fafc',
    outline: 'none',
  };

  const renderQuality = () => {
    if (!quality) return <p className="text-sm text-ai-text-muted">Загрузка…</p>;
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-6">
          <MetricCard label="Всего запросов" value={quality.total_requests} />
          <MetricCard label="Отвеченно" value={`${quality.answered_rate}%`} variant={quality.answered_rate >= 90 ? 'success' : 'default'} />
          <MetricCard label="Ошибки" value={`${quality.error_rate}%`} variant={quality.error_rate > 5 ? 'error' : 'default'} />
          <MetricCard label="Fallback" value={`${quality.fallback_rate}%`} variant={quality.fallback_rate > 5 ? 'error' : 'default'} />
          <MetricCard label="Cache hit" value={`${quality.cache_hit_rate}%`} variant={quality.cache_hit_rate > 30 ? 'success' : 'default'} />
          <MetricCard
            label="Средняя оценка"
            value={quality.average_feedback_score ?? '—'}
            variant={quality.average_feedback_score && quality.average_feedback_score >= 7 ? 'success' : 'default'}
          />
        </div>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          <MetricCard compact label="RAG eligible" value={quality.rag_eligible_count} />
          <MetricCard compact label="RAG covered" value={quality.rag_covered_count} />
          <MetricCard compact label="RAG coverage" value={`${quality.rag_coverage_rate ?? 0}%`} suffix="" />
          <MetricCard compact label="Без ответа" value={quality.total_requests - quality.answered_count} />
        </div>
        <div className="ai-card p-3">
          <h3 className="mb-2 font-display text-sm font-semibold text-ai-text">Последние вопросы без ответа</h3>
          <RequestList items={unanswered.items.slice(0, 10)} emptyText="Нет данных." />
        </div>
      </div>
    );
  };

  const renderUnanswered = () => (
    <div className="ai-card flex flex-col p-3">
      <h3 className="mb-2 font-display text-sm font-semibold text-ai-text">
        Вопросы без ответа <span className="text-xs font-normal text-ai-text-muted">({unanswered.total})</span>
      </h3>
      <RequestList items={unanswered.items} emptyText="Вопросов без ответа не найдено." />
      <Paginator total={unanswered.total} limit={50} offset={offset} onChange={setOffset} />
    </div>
  );

  const renderKbGaps = () => (
    <div className="ai-card flex flex-col p-3">
      <h3 className="mb-2 font-display text-sm font-semibold text-ai-text">
        Гэпы Knowledge Base <span className="text-xs font-normal text-ai-text-muted">({kbGaps.total})</span>
      </h3>
      <p className="mb-2 text-xs text-ai-text-muted">
        Вопросы по учебным темам (study/mixed), где AI не смогла привести источник из KB.
      </p>
      <RequestList items={kbGaps.items} emptyText="Гэпов KB не найдено." />
      <Paginator total={kbGaps.total} limit={50} offset={offset} onChange={setOffset} />
    </div>
  );

  const renderPopularTopics = () => (
    <div className="ai-card p-3">
      <h3 className="mb-2 font-display text-sm font-semibold text-ai-text">Популярные темы</h3>
      {popularTopics.length > 0 ? (
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={popularTopics} margin={{ top: 4, right: 4, bottom: 4, left: -12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="label" stroke="#94a3b8" tick={{ fontSize: 10 }} />
              <YAxis stroke="#94a3b8" allowDecimals={false} tick={{ fontSize: 10 }} />
              <ReTooltip contentStyle={chartTooltipStyle} cursor={{ fill: 'rgba(148, 163, 184, 0.15)' }} />
              <Bar dataKey="count" fill="#2f7bff" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="text-sm text-ai-text-muted">Нет данных.</p>
      )}
    </div>
  );

  const renderKbCoverage = () => {
    if (!kbCoverage) return <p className="text-sm text-ai-text-muted">Загрузка…</p>;
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          <MetricCard label="Всего документов" value={kbCoverage.total_documents} />
          <MetricCard label="Типов документов" value={kbCoverage.documents_by_type.length} />
          <MetricCard label="Курсов в сводке" value={kbCoverage.coverage_by_course.length} />
          <MetricCard label="Всего чанков" value={kbCoverage.coverage_by_course.reduce((s, c) => s + c.chunk_count, 0)} />
        </div>
        <div className="ai-card overflow-x-auto p-3">
          <h3 className="mb-2 font-display text-sm font-semibold text-ai-text">Покрытие по курсам</h3>
          <table className="w-full text-left text-xs">
            <thead className="text-ai-text-muted uppercase">
              <tr>
                <th className="pb-2">Курс</th>
                <th className="pb-2">Документов</th>
                <th className="pb-2">Опубликовано</th>
                <th className="pb-2">Чанков</th>
              </tr>
            </thead>
            <tbody className="text-ai-text">
              {kbCoverage.coverage_by_course.map((row) => (
                <tr key={row.course_id ?? 'none'} className="border-t border-ai-border-subtle">
                  <td className="py-2">{row.course_id ?? 'Без курса'}</td>
                  <td className="py-2">{row.total_documents}</td>
                  <td className="py-2">{row.published_documents}</td>
                  <td className="py-2">{row.chunk_count}</td>
                </tr>
              ))}
              {kbCoverage.coverage_by_course.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-2 text-ai-text-muted">
                    Нет данных.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="ai-card overflow-x-auto p-3">
          <h3 className="mb-2 font-display text-sm font-semibold text-ai-text">Документы по типам</h3>
          <table className="w-full text-left text-xs">
            <thead className="text-ai-text-muted uppercase">
              <tr>
                <th className="pb-2">Тип</th>
                <th className="pb-2">Количество</th>
              </tr>
            </thead>
            <tbody className="text-ai-text">
              {kbCoverage.documents_by_type.map((row) => (
                <tr key={row.document_type} className="border-t border-ai-border-subtle">
                  <td className="py-2">{row.document_type}</td>
                  <td className="py-2">{row.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderExpansion = () => (
    <div className="ai-card overflow-x-auto p-3">
      <h3 className="mb-2 font-display text-sm font-semibold text-ai-text">Кандидаты на расширение KB</h3>
      <p className="mb-2 text-xs text-ai-text-muted">
        Темы с наибольшим числом гэпов Knowledge Base — приоритет для добавления материалов.
      </p>
      <table className="w-full text-left text-xs">
        <thead className="text-ai-text-muted uppercase">
          <tr>
            <th className="pb-2">Тема</th>
            <th className="pb-2">Гэпов</th>
            <th className="pb-2">Рекомендация</th>
          </tr>
        </thead>
        <tbody className="text-ai-text">
          {expansion.map((row) => (
            <tr key={row.intent} className="border-t border-ai-border-subtle">
              <td className="py-2">{INTENT_LABELS[row.intent] || row.intent}</td>
              <td className="py-2">{row.gap_count}</td>
              <td className="py-2">{row.recommendation}</td>
            </tr>
          ))}
          {expansion.length === 0 && (
            <tr>
              <td colSpan={3} className="py-2 text-ai-text-muted">
                Нет кандидатов.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'quality':
        return renderQuality();
      case 'unanswered':
        return renderUnanswered();
      case 'kb-gaps':
        return renderKbGaps();
      case 'popular-topics':
        return renderPopularTopics();
      case 'kb-coverage':
        return renderKbCoverage();
      case 'expansion':
        return renderExpansion();
      default:
        return null;
    }
  };

  if (error) {
    return (
      <div className="m-4 rounded-ai border border-ai-error/20 bg-red-500/10 p-4 text-sm text-ai-error">
        {error}
      </div>
    );
  }

  return (
    <div className="ai-config-page flex h-full flex-col">
      <div className="ai-page__header border-b border-ai-border">
        <div>
          <h1 className="ai-page__title">Business Reports</h1>
          <p className="ai-page__subtitle">Управленческая сводка по качеству и покрытию Knowledge Base</p>
        </div>
        <button
          type="button"
          onClick={loadData}
          className="ai-btn-outline rounded-ai px-3 py-1.5 text-sm"
          disabled={loading}
        >
          {loading ? '…' : 'Обновить'}
        </button>
      </div>

      <FilterBar
        filters={filters}
        onChange={setFilters}
        onApply={() => {
          setOffset(0);
          loadData();
        }}
        onExport={handleExport}
        loading={loading}
        showIntent={activeTab === 'unanswered' || activeTab === 'kb-gaps'}
      />

      <div className="mb-2 flex flex-wrap gap-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => {
              setActiveTab(tab.id);
              setOffset(0);
            }}
            className={`rounded-ai px-3 py-1 text-xs ${
              activeTab === tab.id
                ? 'bg-ai-primary text-white'
                : 'ai-btn-outline text-ai-text'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {renderTabContent()}
      </div>
    </div>
  );
}

export default Reports;
