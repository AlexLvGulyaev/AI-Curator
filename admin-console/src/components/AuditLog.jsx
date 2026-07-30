import { useEffect, useState } from 'react';
import { getAuditLog } from '../api/backend';

function AuditLog() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const data = await getAuditLog({ limit: 200 });
        if (mounted) setEntries(data);
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
        Загрузка журнала аудита…
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
        <h2 className="font-display text-xl font-bold text-ai-text">Журнал аудита</h2>
        <p className="text-sm text-ai-text-muted">
          Последние административные действия.
        </p>
      </div>

      <div className="ai-card overflow-hidden">
        <div className="max-h-[calc(100vh-220px)] overflow-auto">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 bg-ai-surface">
              <tr className="border-b border-ai-border text-ai-text-muted">
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Время</th>
                <th className="px-4 py-3">Пользователь</th>
                <th className="px-4 py-3">Действие</th>
                <th className="px-4 py-3">Ресурс</th>
                <th className="px-4 py-3">ID ресурса</th>
                <th className="px-4 py-3">Детали</th>
              </tr>
            </thead>
            <tbody className="text-ai-text-secondary">
              {entries.map((entry) => (
                <tr key={entry.id} className="border-b border-ai-border-subtle">
                  <td className="px-4 py-3">{entry.id}</td>
                  <td className="px-4 py-3 whitespace-nowrap">{new Date(entry.created_at).toLocaleString('ru-RU')}</td>
                  <td className="px-4 py-3">{entry.user_id}</td>
                  <td className="px-4 py-3">{entry.action}</td>
                  <td className="px-4 py-3">{entry.resource_type}</td>
                  <td className="px-4 py-3">{entry.resource_id || '—'}</td>
                  <td className="px-4 py-3 max-w-xs truncate">{entry.details ? JSON.stringify(entry.details) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default AuditLog;
