import { useEffect, useState } from 'react';
import { getMonitoringStatus, getKbStatus } from '../api/backend';

function StatusCard({ title, status, latency, detail }) {
  let dotClass = 'status-dot';
  if (status === 'ok') dotClass += ' online';
  else if (status === 'error') dotClass += ' error';
  else dotClass += ' warning';

  return (
    <div className="ai-card p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-display font-semibold text-ai-text">{title}</h3>
        <span className={dotClass} />
      </div>
      <p className="text-sm capitalize text-ai-text-secondary">{status}</p>
      {latency !== undefined && latency !== null && (
        <p className="mt-1 text-xs text-ai-text-muted">{latency} мс</p>
      )}
      {detail && (
        <p className="mt-1 text-xs text-ai-text-muted">{detail}</p>
      )}
    </div>
  );
}

function Dashboard() {
  const [status, setStatus] = useState(null);
  const [kbStatus, setKbStatus] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const [monitoring, kb] = await Promise.all([
          getMonitoringStatus(),
          getKbStatus(),
        ]);
        if (mounted) {
          setStatus(monitoring);
          setKbStatus(kb);
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
        Загрузка состояния системы…
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

  const components = status?.components || {};

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="font-display text-xl font-bold text-ai-text">Панель состояния</h2>
        <p className="text-sm text-ai-text-muted">
          Общий статус: {status?.overall === 'ok' ? '✅ Работает нормально' : '⚠️ Есть проблемы'}
        </p>
      </div>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatusCard
          title="База данных"
          status={components.database?.status}
          latency={components.database?.latency_ms}
          detail={components.database?.detail}
        />
        <StatusCard
          title="LMS"
          status={components.lms?.status}
          latency={components.lms?.latency_ms}
          detail={components.lms?.detail}
        />
        <StatusCard
          title="Chroma"
          status={components.chroma?.status}
          latency={components.chroma?.latency_ms}
          detail={components.chroma?.detail}
        />
        <StatusCard
          title="LLM"
          status={components.llm?.status}
          detail={components.llm?.detail}
        />
      </div>

      {kbStatus && (
        <div className="ai-card p-5">
          <h3 className="mb-4 font-display font-semibold text-ai-text">Knowledge Base</h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <p className="text-xs text-ai-text-muted">Всего документов</p>
              <p className="text-2xl font-semibold text-ai-text">{kbStatus.total_documents}</p>
            </div>
            <div>
              <p className="text-xs text-ai-text-muted">Опубликовано</p>
              <p className="text-2xl font-semibold text-ai-success">{kbStatus.published_documents}</p>
            </div>
            <div>
              <p className="text-xs text-ai-text-muted">Версий</p>
              <p className="text-2xl font-semibold text-ai-text">{kbStatus.total_versions}</p>
            </div>
            <div>
              <p className="text-xs text-ai-text-muted">Индексировано фрагментов</p>
              <p className="text-2xl font-semibold text-ai-primary">{kbStatus.indexed_chunks}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
