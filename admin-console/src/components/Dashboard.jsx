import { useEffect, useState } from 'react';
import { getMonitoringStatus, getRecentErrors } from '../api/backend';

const STATUS_MAP = {
  ok: { variant: 'ok', label: 'НОРМА' },
  online: { variant: 'ok', label: 'НОРМА' },
  ready: { variant: 'ok', label: 'НОРМА' },
  norma: { variant: 'ok', label: 'НОРМА' },
  success: { variant: 'ok', label: 'НОРМА' },
  error: { variant: 'error', label: 'ОШИБКА' },
  warning: { variant: 'warning', label: 'ВНИМАНИЕ' },
  degraded: { variant: 'warning', label: 'ДЕГРАДАЦИЯ' },
  disabled: { variant: 'muted', label: 'ОТКЛ.' },
  unknown: { variant: 'muted', label: 'Н/Д' },
};

function StatusBadge({ status }) {
  const safeStatus = (status || 'unknown').toLowerCase();
  const mapped = STATUS_MAP[safeStatus] || STATUS_MAP.unknown;
  return (
    <span className={`ai-status ai-status--${mapped.variant}`}>
      {mapped.label}
    </span>
  );
}

function Metric({ label, value, note }) {
  return (
    <div className="ai-metric">
      <div className="ai-metric__label">{label}</div>
      <div className="ai-metric__value">{value}</div>
      {note && <div className="ai-metric__note">{note}</div>}
    </div>
  );
}

function Section({ title, subtitle, children, className = '' }) {
  return (
    <div className={`ai-card ai-section ${className}`.trim()}>
      <div>
        <h3 className="ai-section__title">{title}</h3>
        {subtitle && <p className="ai-section__subtitle">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

function Dashboard() {
  const [status, setStatus] = useState(null);
  const [errors, setErrors] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [monitoring, recentErrors] = await Promise.all([
        getMonitoringStatus(),
        getRecentErrors(10),
      ]);
      setStatus(monitoring);
      setErrors(recentErrors);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return (
      <div className="ai-loading flex items-center gap-2">
        <span className="inline-block animate-pulse">●</span>
        Загрузка состояния системы…
      </div>
    );
  }

  if (error) {
    return (
      <div className="ai-error">
        {error}
      </div>
    );
  }

  const components = status?.components || {};
  const ai = status?.ai_activity || {};
  const kb = status?.kb_status || {};

  return (
    <div className="flex flex-col gap-3">
      {/* Page header */}
      <div className="ai-page__header">
        <div>
          <h1 className="ai-page__title">Панель состояния</h1>
          <p className="ai-page__subtitle">Общий статус, зависимости, AI-активность, KB</p>
        </div>
        <button
          onClick={load}
          className="ai-btn ai-btn--small"
          type="button"
        >
          Обновить
        </button>
      </div>

      {/* System status */}
      <Section title="Состояние системы" subtitle="Runtime health, зависимости и оперативный статус.">
        <div className="ai-grid ai-grid--5">
          <Metric
            label="API"
            value={<StatusBadge status={components.api?.status} />}
            note={components.api?.latency_ms !== undefined ? `${components.api.latency_ms} мс` : undefined}
          />
          <Metric
            label="PostgreSQL"
            value={<StatusBadge status={components.database?.status} />}
            note={components.database?.latency_ms !== undefined ? `${components.database.latency_ms} мс` : undefined}
          />
          <Metric
            label="LMS"
            value={<StatusBadge status={components.lms?.status} />}
            note={components.lms?.latency_ms !== undefined ? `${components.lms.latency_ms} мс` : undefined}
          />
          <Metric
            label="Chroma"
            value={<StatusBadge status={components.chroma?.status} />}
            note={components.chroma?.latency_ms !== undefined ? `${components.chroma.latency_ms} мс` : undefined}
          />
          <Metric
            label="LLM"
            value={<StatusBadge status={components.llm?.status} />}
            note={components.llm?.detail}
          />
        </div>
      </Section>

      {/* Intent breakdown */}
      <Section title="Распределение по интентам" subtitle="Интенты запросов за последние 24 часа.">
        {ai.intent_breakdown?.length > 0 ? (
          <div className="ai-grid ai-grid--5">
            {ai.intent_breakdown.slice(0, 5).map((item) => (
              <Metric
                key={item.intent}
                label={item.intent || 'unknown'}
                value={item.count?.toLocaleString('ru-RU') ?? 0}
              />
            ))}
          </div>
        ) : (
          <div className="ai-empty">Нет данных за последние 24 часа.</div>
        )}
      </Section>

      {/* Bottom grid: left column (AI activity + KB), right column (errors) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 min-h-0 flex-1">
        {/* Left column */}
        <div className="flex flex-col gap-3">
          <Section title="AI-активность" subtitle="Запросы и метрики за последние 24 часа.">
            <div className="ai-grid ai-grid--2">
              <Metric label="Запросы" value={ai.total_requests?.toLocaleString('ru-RU') ?? 0} />
              <Metric label="Ответы" value={ai.total_answers?.toLocaleString('ru-RU') ?? 0} />
              <Metric label="Ср. latency" value={`${ai.average_latency_ms ?? 0} мс`} />
              <Metric label="Токены" value={ai.total_tokens?.toLocaleString('ru-RU') ?? 0} />
            </div>
          </Section>

          <Section title="Knowledge Base" subtitle="Состояние базы знаний.">
            <div className="ai-grid ai-grid--2">
              <Metric label="Документов" value={kb.total_documents ?? 0} />
              <Metric label="Опубликовано" value={kb.published_documents ?? 0} />
              <Metric label="Версий" value={kb.total_versions ?? 0} />
              <Metric label="Чанков" value={kb.indexed_chunks ?? 0} />
            </div>
          </Section>
        </div>

        {/* Right column: recent errors */}
        <Section title="Последние ошибки" subtitle="Недавние ошибки обработки запросов." className="flex-1 min-h-0">
          {errors.length === 0 ? (
            <div className="ai-empty">Ошибок не найдено.</div>
          ) : (
            <div className="overflow-auto flex-1 min-h-0">
              <table className="ai-table">
                <thead>
                  <tr>
                    <th>Время</th>
                    <th>Intent</th>
                    <th>Сообщение</th>
                  </tr>
                </thead>
                <tbody>
                  {errors.map((entry, idx) => (
                    <tr key={idx}>
                      <td className="ai-table__cell--nowrap">
                        {entry.created_at
                          ? new Date(entry.created_at).toLocaleString('ru-RU')
                          : '—'}
                      </td>
                      <td>{entry.intent || '—'}</td>
                      <td className="ai-table__cell--truncate" title={entry.error}>
                        {entry.error}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>
      </div>
    </div>
  );
}

export default Dashboard;
