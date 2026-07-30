import { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import {
  getAnalyticsDashboard,
  getAnalyticsTopics,
  getAnalyticsUnanswered,
  getAnalyticsFeedback,
} from '../api/backend';

function Analytics() {
  const [dashboard, setDashboard] = useState(null);
  const [topics, setTopics] = useState([]);
  const [unanswered, setUnanswered] = useState([]);
  const [feedback, setFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const [dash, t, u, f] = await Promise.all([
          getAnalyticsDashboard(),
          getAnalyticsTopics(),
          getAnalyticsUnanswered(20),
          getAnalyticsFeedback(),
        ]);
        if (mounted) {
          setDashboard(dash);
          setTopics(t);
          setUnanswered(u);
          setFeedback(f);
        }
      } catch (err) {
        if (mounted) setError(err.message);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="p-8 text-ai-text-muted">
        <span className="mr-2 inline-block animate-pulse">●</span>
        Загрузка аналитики…
      </div>
    );
  }

  if (error) {
    return (
      <div className="m-6 rounded-ai border border-ai-error/20 bg-red-500/10 p-4 text-sm text-ai-error">
        {error}
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="font-display text-xl font-bold text-ai-text">Аналитика запросов</h2>
      </div>

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="ai-card p-5">
          <p className="text-xs text-ai-text-muted">Всего запросов</p>
          <p className="text-3xl font-semibold text-ai-text">{dashboard?.total_requests || 0}</p>
        </div>
        <div className="ai-card p-5">
          <p className="text-xs text-ai-text-muted">Ответов</p>
          <p className="text-3xl font-semibold text-ai-text">{dashboard?.total_answers || 0}</p>
        </div>
        <div className="ai-card p-5">
          <p className="text-xs text-ai-text-muted">Средняя задержка</p>
          <p className="text-3xl font-semibold text-ai-text">{dashboard?.average_latency_ms || 0} мс</p>
        </div>
        <div className="ai-card p-5">
          <p className="text-xs text-ai-text-muted">Без ответа</p>
          <p className="text-3xl font-semibold text-ai-error">{dashboard?.unanswered_count || 0}</p>
        </div>
      </div>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <div className="ai-card p-5">
          <h3 className="mb-4 font-display font-semibold text-ai-text">Распределение по темам</h3>
          {topics.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topics}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="intent" stroke="#94a3b8" />
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
        </div>

        <div className="ai-card p-5">
          <h3 className="mb-4 font-display font-semibold text-ai-text">Оценки полезности</h3>
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
            <p className="text-sm text-ai-text-muted">Нет данных.</p>
          )}
        </div>
      </div>

      <div className="ai-card p-5">
        <h3 className="mb-4 font-display font-semibold text-ai-text">Вопросы без ответа</h3>
        {unanswered.length > 0 ? (
          <div className="max-h-80 overflow-y-auto space-y-3">
            {unanswered.map((item) => (
              <div key={item.request_id} className="border-b border-ai-border-subtle pb-3">
                <p className="text-sm text-ai-text">{item.message}</p>
                <p className="text-xs text-ai-text-muted">
                  {item.intent} · курс {item.course_id || '—'} · {new Date(item.created_at).toLocaleString('ru-RU')}
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
