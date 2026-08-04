import { useEffect, useMemo, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip as ReTooltip,
  ResponsiveContainer,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  getAnalyticsDashboard,
  getAnalyticsTopics,
  getAnalyticsUnanswered,
  getAnalyticsLatency,
  getAnalyticsSources,
  getAnalyticsErrors,
  exportAnalyticsReport,
} from '../api/backend';

const INTENT_LABELS = {
  deadline: 'Дедлайн',
  progress: 'Прогресс',
  mixed: 'Смешанный',
  study: 'Учёба',
  organizational: 'Организационный',
  unknown: 'Не определён',
};

const SOURCE_LABELS = {
  lms: 'LMS',
  rag: 'База знаний',
  both: 'LMS + База знаний',
  cache: 'Кэш',
  fallback: 'Fallback бэкенда',
  error: 'Ошибка',
};

const SOURCE_COLORS = {
  lms: '#2f7bff',
  rag: '#7c3aed',
  both: '#14b8a6',
  cache: '#f59e0b',
  fallback: '#64748b',
  error: '#ef4444',
};

const HISTOGRAM_COLORS = ['#14b8a6', '#2f7bff', '#f59e0b', '#f97316', '#ef4444'];

const KPI_TOOLTIPS = {
  'Всего запросов': 'Общее количество сообщений студентов за выбранный период.',
  'Ответов': 'Запросы, по которым система сформировала ответ.',
  'Средняя задержка': 'Среднее время от отправки запроса до получения ответа.',
  '% отвеченных': 'Доля запросов, по которым получен ответ.',
  'Без ответа': 'Запросы, по которым система не смогла сформировать ответ.',
  'Ошибки чата': 'Доля запросов, завершившихся ошибкой в ChatLog.',
};

const LATENCY_TOOLTIPS = {
  'Среднее': 'Среднее арифметическое всех задержек. Может быть сильно выше медианы из-за нескольких медленных запросов.',
  'Медиана': 'p50 — 50% запросов отвечали быстрее этого значения.',
  'p95': '95% запросов отвечали быстрее этого значения. Хвост распределения.',
  'p99': '99% запросов отвечали быстрее этого значения. Экстремальный хвост.',
};

const CHART_TOOLTIPS = {
  'Распределение по темам': 'Распределение запросов по intent-классификации: учёба, дедлайн, прогресс, организационные, вне курса (out_of_scope) и ошибки.',
  'Источники ответов': 'Откуда взялся ответ: LMS, База знаний, Кэш, Fallback бэкенда (например, out_of_scope) или технические ошибки.',
  'Распределение задержек': 'Распределение времени ответа по диапазонам.',
  'Сводка по задержкам': 'Ключевые перцентили задержки: среднее, медиана, p95, p99.',
  'Вопросы без ответа': 'Запросы, по которым не был получен ответ.',
};

function formatDateInput(d) {
  const tzOffset = d.getTimezoneOffset() * 60000;
  const local = new Date(d.getTime() - tzOffset);
  return local.toISOString().split('T')[0];
}

function Tooltip({ children, text, placement = 'top' }) {
  const placementClasses =
    placement === 'bottom'
      ? 'left-1/2 top-full mt-2 -translate-x-1/2'
      : 'left-1/2 bottom-full mb-2 -translate-x-1/2';
  return (
    <div className="group relative inline-flex items-center gap-1">
      {children}
      <span
        className={`pointer-events-none absolute z-50 hidden max-w-xs whitespace-normal rounded-ai border border-ai-border bg-ai-surface p-2 text-xs text-ai-text shadow-lg ${placementClasses} group-hover:block`}
      >
        {text}
      </span>
    </div>
  );
}

function MetricCard({ label, value, variant = 'default', compact = false, tooltip = '' }) {
  const valueClass =
    variant === 'error'
      ? 'text-ai-error'
      : variant === 'success'
      ? 'text-ai-success'
      : 'text-ai-text';
  const card = (
    <div className={`ai-card flex w-full cursor-help flex-col justify-between ${compact ? 'p-2' : 'p-5'}`}>
      <p className={`text-ai-text-muted ${compact ? 'text-[0.65rem] uppercase tracking-wide' : 'text-xs'}`}>{label}</p>
      <p className={`font-semibold ${compact ? 'text-xl leading-tight' : 'text-3xl'} ${valueClass}`}>{value}</p>
    </div>
  );
  const tip = tooltip || KPI_TOOLTIPS[label] || '';
  if (!tip) return card;
  return <Tooltip text={tip}>{card}</Tooltip>;
}

function ChartCard({ title, subtitle, children, className = '', legend }) {
  return (
    <div className={`ai-card p-3 ${className}`.trim()}>
      <div className="mb-1 flex items-center gap-1">
        <h3 className="font-display text-sm font-semibold text-ai-text">{title}</h3>
        {CHART_TOOLTIPS[title] && (
          <Tooltip text={CHART_TOOLTIPS[title]} placement="top">
            <svg
              className="h-3.5 w-3.5 cursor-help text-ai-text-muted"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </Tooltip>
        )}
      </div>
      {subtitle && <p className="mb-2 text-xs text-ai-text-muted">{subtitle}</p>}
      {children}
      {legend && <div className="mt-2">{legend}</div>}
    </div>
  );
}

function SourceLegend({ items }) {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 text-[0.65rem] leading-tight text-ai-text-muted">
      {items.map((item) => (
        <div key={item.source} className="flex items-center gap-1">
          <span
            className="inline-block h-2 w-2 rounded-sm"
            style={{ backgroundColor: SOURCE_COLORS[item.source] || '#64748b' }}
          />
          <span>{SOURCE_LABELS[item.source] || item.source}</span>
          <span className="text-ai-text">({item.count})</span>
        </div>
      ))}
    </div>
  );
}

function FilterBar({ filters, onChange, onApply, loading, onExport }) {
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
      <div className="flex flex-1 items-center justify-end gap-2">
        <button
          type="button"
          onClick={() =>
            onChange({
              date_from: formatDateInput(new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)),
              date_to: formatDateInput(new Date()),
              course_id: '',
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

function Analytics() {
  const [dashboard, setDashboard] = useState(null);
  const [topics, setTopics] = useState([]);
  const [unanswered, setUnanswered] = useState([]);
  const [latency, setLatency] = useState(null);
  const [sources, setSources] = useState(null);
  const [errors, setErrors] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    date_from: formatDateInput(new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)),
    date_to: formatDateInput(new Date()),
    course_id: '',
  });

  const buildParams = useMemo(() => {
    const params = {};
    if (filters.date_from) params.date_from = filters.date_from;
    if (filters.date_to) params.date_to = filters.date_to;
    if (filters.course_id) params.course_id = filters.course_id;
    return params;
  }, [filters]);

  const answeredRate = useMemo(() => {
    const total = dashboard?.total_requests ?? 0;
    const answered = dashboard?.total_answers ?? 0;
    if (!total) return 0;
    return Math.round((answered / total) * 100);
  }, [dashboard]);

  const errorRate = useMemo(() => {
    const total = dashboard?.total_requests ?? 0;
    const chatErrors = errors?.chat_errors ?? 0;
    if (!total) return 0;
    return Math.round((chatErrors / total) * 100);
  }, [dashboard, errors]);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const params = buildParams;
      const [dash, t, u, lat, src, err] = await Promise.all([
        getAnalyticsDashboard(params),
        getAnalyticsTopics({ ...params, limit: 20 }),
        getAnalyticsUnanswered({ ...params, limit: 20 }),
        getAnalyticsLatency(params),
        getAnalyticsSources(params),
        getAnalyticsErrors({ ...params, limit: 20 }),
      ]);
      setDashboard(dash);
      setTopics(
        t.map((item) => ({
          ...item,
          label: INTENT_LABELS[item.intent] || item.intent,
        }))
      );
      setUnanswered(u);
      setLatency(lat);
      setSources(
        (src?.breakdown || []).map((item) => ({
          ...item,
          label: SOURCE_LABELS[item.source] || item.source,
        }))
      );
      setErrors(err);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleExport() {
    setLoading(true);
    try {
      const blob = await exportAnalyticsReport(buildParams);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ai_curator_analytics_${filters.date_from || 'all'}_${filters.date_to || 'all'}.csv`;
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
  }, []);

  if (error) {
    return (
      <div className="m-4 rounded-ai border border-ai-error/20 bg-red-500/10 p-4 text-sm text-ai-error">
        {error}
      </div>
    );
  }

  const chartTooltipStyle = {
    backgroundColor: '#1e293b',
    borderColor: '#334155',
    color: '#f8fafc',
    outline: 'none',
  };

  return (
    <div className="ai-config-page flex h-full flex-col">
      <div className="ai-page__header border-b border-ai-border">
        <div>
          <h1 className="ai-page__title">Аналитика запросов</h1>
          <p className="ai-page__subtitle">Ключевые метрики, распределения и качество ответов</p>
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
        onApply={loadData}
        onExport={handleExport}
        loading={loading}
      />

      <div className="grid shrink-0 grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-6">
        <MetricCard label="Всего запросов" value={dashboard?.total_requests ?? '—'} />
        <MetricCard label="Ответов" value={dashboard?.total_answers ?? '—'} />
        <MetricCard
          label="Средняя задержка"
          value={`${Math.round(dashboard?.average_latency_ms ?? 0)} мс`}
        />
        <MetricCard
          label="% отвеченных"
          value={`${answeredRate}%`}
          variant={answeredRate >= 90 ? 'success' : answeredRate >= 70 ? 'default' : 'error'}
        />
        <MetricCard
          label="Без ответа"
          value={dashboard?.unanswered_count ?? 0}
          variant={dashboard?.unanswered_count ? 'error' : 'success'}
        />
        <MetricCard
          label="Ошибки чата"
          value={`${errorRate}%`}
          variant={errorRate > 5 ? 'error' : errorRate > 0 ? 'default' : 'success'}
        />
      </div>

      <div className="grid min-h-0 flex-[1.1] gap-2 lg:grid-cols-3">
        <ChartCard title="Распределение по темам" className="lg:col-span-2 flex flex-col">
          {topics.length > 0 ? (
            <div className="min-h-0 flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topics} margin={{ top: 4, right: 4, bottom: 4, left: -12 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="label" stroke="#94a3b8" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#94a3b8" allowDecimals={false} tick={{ fontSize: 10 }} />
                  <ReTooltip
                    contentStyle={chartTooltipStyle}
                    cursor={{ fill: 'rgba(148, 163, 184, 0.15)' }}
                  />
                  <Bar dataKey="count" fill="#7c3aed" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-ai-text-muted">Нет данных.</p>
          )}
        </ChartCard>

        <ChartCard
          title="Источники ответов"
          className="flex flex-col"
          legend={sources && sources.length > 0 ? <SourceLegend items={sources} /> : null}
        >
          {sources && sources.length > 0 ? (
            <div className="min-h-0 flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={sources}
                    dataKey="count"
                    nameKey="label"
                    cx="50%"
                    cy="45%"
                    outerRadius="65%"
                    label={({ percent }) => `${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {sources.map((entry) => (
                      <Cell key={entry.source} fill={SOURCE_COLORS[entry.source] || '#64748b'} />
                    ))}
                  </Pie>
                  <ReTooltip
                    contentStyle={chartTooltipStyle}
                    formatter={(value, name) => [value, name]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-ai-text-muted">Нет данных.</p>
          )}
        </ChartCard>
      </div>

      <div className="mt-2 grid min-h-0 flex-1 gap-2 lg:grid-cols-12">
        <ChartCard
          title="Распределение задержек"
          subtitle="Latency histogram, мс"
          className="lg:col-span-5 flex flex-col"
        >
          {latency && latency.count > 0 ? (
            <div className="min-h-0 flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={latency.histogram} margin={{ top: 4, right: 4, bottom: 4, left: -12 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="bucket" stroke="#94a3b8" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#94a3b8" allowDecimals={false} tick={{ fontSize: 10 }} />
                  <ReTooltip
                    contentStyle={chartTooltipStyle}
                    cursor={{ fill: 'rgba(148, 163, 184, 0.15)' }}
                  />
                  <Bar dataKey="count">
                    {latency.histogram.map((entry, index) => (
                      <Cell key={entry.bucket} fill={HISTOGRAM_COLORS[index % HISTOGRAM_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-ai-text-muted">Нет данных.</p>
          )}
        </ChartCard>

        <ChartCard title="Сводка по задержкам" className="lg:col-span-3 flex flex-col">
          <div className="flex min-h-0 flex-1 flex-col gap-2">
            <MetricCard compact label="Среднее" value={`${Math.round(latency?.average_ms ?? 0)} мс`} tooltip={LATENCY_TOOLTIPS['Среднее']} />
            <MetricCard compact label="Медиана" value={`${Math.round(latency?.p50_ms ?? 0)} мс`} tooltip={LATENCY_TOOLTIPS['Медиана']} />
            <MetricCard compact label="p95" value={`${Math.round(latency?.p95_ms ?? 0)} мс`} tooltip={LATENCY_TOOLTIPS['p95']} />
            <MetricCard compact label="p99" value={`${Math.round(latency?.p99_ms ?? 0)} мс`} tooltip={LATENCY_TOOLTIPS['p99']} />
          </div>
        </ChartCard>

        <div className="ai-card flex flex-col p-3 lg:col-span-4">
          <div className="mb-2 flex items-center gap-1">
            <h3 className="font-display text-sm font-semibold text-ai-text">
              Вопросы без ответа{' '}
              <span className="text-xs font-normal text-ai-text-muted">({unanswered.length})</span>
            </h3>
            {CHART_TOOLTIPS['Вопросы без ответа'] && (
              <Tooltip text={CHART_TOOLTIPS['Вопросы без ответа']} placement="top">
                <svg
                  className="h-3.5 w-3.5 cursor-help text-ai-text-muted"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </Tooltip>
            )}
          </div>
          {unanswered.length > 0 ? (
            <div className="min-h-0 flex-1 overflow-y-auto space-y-2 pr-1">
              {unanswered.map((item) => (
                <div key={item.request_id} className="border-b border-ai-border-subtle pb-2 last:border-0">
                  <p className="text-sm text-ai-text">{item.message}</p>
                  <p className="text-xs text-ai-text-muted">
                    {INTENT_LABELS[item.intent] || item.intent} · курс {item.course_id || '—'} ·{' '}
                    {item.created_at ? new Date(item.created_at).toLocaleString('ru-RU') : '—'}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-ai-text-muted">Вопросов без ответа не найдено.</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default Analytics;
