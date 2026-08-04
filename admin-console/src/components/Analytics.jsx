import { useEffect, useMemo, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts';
import {
  getAnalyticsDashboard,
  getAnalyticsTopics,
  getAnalyticsUnanswered,
  getAnalyticsFeedback,
  getAnalyticsLatency,
  getAnalyticsSources,
  getAnalyticsErrors,
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
  rag: 'Knowledge Base',
  both: 'LMS + KB',
  none: 'Без источников',
};

const SOURCE_COLORS = {
  lms: '#2f7bff',
  rag: '#7c3aed',
  both: '#14b8a6',
  none: '#64748b',
};

const HISTOGRAM_COLORS = ['#14b8a6', '#2f7bff', '#f59e0b', '#f97316', '#ef4444'];

function formatDateInput(d) {
  const tzOffset = d.getTimezoneOffset() * 60000;
  const local = new Date(d.getTime() - tzOffset);
  return local.toISOString().split('T')[0];
}

function MetricCard({ label, value, note, variant = 'default' }) {
  const valueClass =
    variant === 'error'
      ? 'text-ai-error'
      : variant === 'success'
      ? 'text-ai-success'
      : 'text-ai-text';
  return (
    <div className="ai-card p-5">
      <p className="text-xs text-ai-text-muted">{label}</p>
      <p className={`text-3xl font-semibold ${valueClass}`}>{value}</p>
      {note && <p className="mt-1 text-xs text-ai-text-muted">{note}</p>}
    </div>
  );
}

function ChartCard({ title, subtitle, children, className = '' }) {
  return (
    <div className={`ai-card p-5 ${className}`.trim()}>
      <h3 className="font-display font-semibold text-ai-text">{title}</h3>
      {subtitle && <p className="mb-4 text-xs text-ai-text-muted">{subtitle}</p>}
      {children}
    </div>
  );
}

function FilterBar({ filters, onChange, onApply, loading }) {
  return (
    <div className="ai-card mb-6 flex flex-wrap items-end gap-4 p-4">
      <div className="flex flex-col gap-1">
        <label className="text-xs text-ai-text-muted">С</label>
        <input
          type="date"
          value={filters.date_from}
          onChange={(e) => onChange({ ...filters, date_from: e.target.value })}
          className="ai-input px-3 py-1.5 text-sm"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-ai-text-muted">По</label>
        <input
          type="date"
          value={filters.date_to}
          onChange={(e) => onChange({ ...filters, date_to: e.target.value })}
          className="ai-input px-3 py-1.5 text-sm"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-ai-text-muted">Курс</label>
        <input
          type="number"
          min={1}
          placeholder="ID курса"
          value={filters.course_id}
          onChange={(e) => onChange({ ...filters, course_id: e.target.value })}
          className="ai-input px-3 py-1.5 text-sm"
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
          className="ai-btn-outline rounded-ai px-3 py-1.5 text-sm"
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
          className="ai-btn-outline rounded-ai px-3 py-1.5 text-sm"
        >
          30 дней
        </button>
        <button
          type="button"
          onClick={onApply}
          disabled={loading}
          className="ai-btn rounded-ai px-4 py-1.5 text-sm"
        >
          {loading ? 'Загрузка…' : 'Применить'}
        </button>
      </div>
    </div>
  );
}

function Analytics() {
  const [dashboard, setDashboard] = useState(null);
  const [topics, setTopics] = useState([]);
  const [unanswered, setUnanswered] = useState([]);
  const [feedback, setFeedback] = useState([]);
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

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const params = buildParams;
      const [dash, t, u, f, lat, src, err] = await Promise.all([
        getAnalyticsDashboard(params),
        getAnalyticsTopics({ ...params, limit: 20 }),
        getAnalyticsUnanswered({ ...params, limit: 20 }),
        getAnalyticsFeedback(params),
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
      setFeedback(f);
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
      <div className="m-6 rounded-ai border border-ai-error/20 bg-red-500/10 p-4 text-sm text-ai-error">
        {error}
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="font-display text-xl font-bold text-ai-text">Аналитика запросов</h2>
          <p className="text-sm text-ai-text-muted">Ключевые метрики, распределения и качество ответов</p>
        </div>
      </div>

      <FilterBar
        filters={filters}
        onChange={setFilters}
        onApply={loadData}
        loading={loading}
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <MetricCard
          label="Всего запросов"
          value={dashboard?.total_requests ?? '—'}
          note={loading ? '…' : undefined}
        />
        <MetricCard
          label="Ответов"
          value={dashboard?.total_answers ?? '—'}
        />
        <MetricCard
          label="Средняя задержка"
          value={`${dashboard?.average_latency_ms ?? 0} мс`}
        />
        <MetricCard
          label="Оценка полезности"
          value={dashboard?.average_feedback_score ?? '—'}
        />
        <MetricCard
          label="Без ответа"
          value={dashboard?.unanswered_count ?? 0}
          variant={dashboard?.unanswered_count ? 'error' : 'success'}
        />
      </div>

      <div className="mb-6 grid gap-6 lg:grid-cols-3">
        <ChartCard title="Распределение по темам" className="lg:col-span-2">
          {topics.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topics}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="label" stroke="#94a3b8" tick={{ fontSize: 12 }} />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      borderColor: '#334155',
                      color: '#f8fafc',
                    }}
                  />
                  <Bar dataKey="count" fill="#7c3aed" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-ai-text-muted">Нет данных.</p>
          )}
        </ChartCard>

        <ChartCard title="Источники ответов">
          {sources && sources.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={sources}
                    dataKey="count"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label
                  >
                    {sources.map((entry) => (
                      <Cell key={entry.source} fill={SOURCE_COLORS[entry.source] || '#64748b'} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      borderColor: '#334155',
                      color: '#f8fafc',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-ai-text-muted">Нет данных.</p>
          )}
        </ChartCard>
      </div>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <ChartCard title="Распределение задержек" subtitle="Latency histogram, мс">
          {latency && latency.count > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={latency.histogram}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="bucket" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      borderColor: '#334155',
                      color: '#f8fafc',
                    }}
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

        <ChartCard title="Оценки полезности" subtitle="Распределение feedback_score">
          {feedback.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={feedback}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="score" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      borderColor: '#334155',
                      color: '#f8fafc',
                    }}
                  />
                  <Bar dataKey="count" fill="#14b8a6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-ai-text-muted">Нет оценок.</p>
          )}
        </ChartCard>
      </div>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <ChartCard title="Сводка по задержкам">
          <div className="grid grid-cols-2 gap-4">
            <MetricCard label="Среднее" value={`${latency?.average_ms ?? 0} мс`} />
            <MetricCard label="Медиана (p50)" value={`${latency?.p50_ms ?? 0} мс`} />
            <MetricCard label="p95" value={`${latency?.p95_ms ?? 0} мс`} />
            <MetricCard label="p99" value={`${latency?.p99_ms ?? 0} мс`} />
          </div>
        </ChartCard>

        <ChartCard
          title="Ошибки"
          subtitle={`Error rate: ${errors?.error_rate ?? 0}%`}
        >
          <div className="grid grid-cols-2 gap-4">
            <MetricCard label="Ошибки чата" value={errors?.chat_errors ?? 0} variant="error" />
            <MetricCard label="Ошибки LLM" value={errors?.llm_errors ?? 0} variant="error" />
          </div>
          {errors?.recent_errors?.length > 0 && (
            <div className="mt-4 max-h-40 overflow-y-auto space-y-2">
              {errors.recent_errors.map((item) => (
                <div
                  key={item.request_id}
                  className="rounded-ai border border-ai-error/20 bg-red-500/10 p-2 text-xs text-ai-error"
                >
                  <p className="font-medium">{item.message}</p>
                  <p className="text-ai-text-muted">{item.error}</p>
                </div>
              ))}
            </div>
          )}
        </ChartCard>
      </div>

      <div className="ai-card p-5">
        <h3 className="mb-4 font-display font-semibold text-ai-text">Вопросы без ответа</h3>
        {unanswered.length > 0 ? (
          <div className="max-h-80 overflow-y-auto space-y-3">
            {unanswered.map((item) => (
              <div key={item.request_id} className="border-b border-ai-border-subtle pb-3">
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
  );
}

export default Analytics;
