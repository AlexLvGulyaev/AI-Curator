import { useEffect, useState } from 'react';
import { listKbDocuments, publishKbDocument, processKbDocument, deleteKbDocument } from '../api/backend';

const STATUSES = {
  draft: 'Черновик',
  pending: 'В ожидании',
  processing: 'Обработка',
  indexed: 'Индексирован',
  error: 'Ошибка',
  archived: 'Архив',
};

function KbDocuments({ onSelectDocument, onUploadNew }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await listKbDocuments({ limit: 200 });
      setDocuments(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const handlePublish = async (doc) => {
    setActionLoading(`publish-${doc.id}`);
    try {
      await publishKbDocument(doc.id, !doc.is_published);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleProcess = async (id) => {
    setActionLoading(`process-${id}`);
    try {
      await processKbDocument(id);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Удалить документ? Это действие необратимо.')) return;
    setActionLoading(`delete-${id}`);
    try {
      await deleteKbDocument(id);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-ai-text-muted">
        <span className="mr-2 inline-block animate-pulse">●</span>
        Загрузка документов…
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="font-display text-xl font-bold text-ai-text">Knowledge Base</h2>
          <p className="text-sm text-ai-text-muted">Управление учебными материалами.</p>
        </div>
        <button
          onClick={onUploadNew}
          className="ai-btn px-4 py-2"
        >
          + Загрузить документ
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-ai border border-ai-error/20 bg-red-500/10 p-4 text-sm text-ai-error">
          {error}
        </div>
      )}

      <div className="ai-card overflow-hidden">
        <div className="max-h-[calc(100vh-220px)] overflow-auto">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 bg-ai-surface">
              <tr className="border-b border-ai-border text-ai-text-muted">
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Название</th>
                <th className="px-4 py-3">Тип</th>
                <th className="px-4 py-3">Курс/Модуль</th>
                <th className="px-4 py-3">Сложность</th>
                <th className="px-4 py-3">Статус</th>
                <th className="px-4 py-3">Публикация</th>
                <th className="px-4 py-3">Действия</th>
              </tr>
            </thead>
            <tbody className="text-ai-text-secondary">
              {documents.map((doc) => (
                <tr key={doc.id} className="border-b border-ai-border-subtle">
                  <td className="px-4 py-3">{doc.id}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => onSelectDocument(doc)}
                      className="text-left font-medium text-ai-text hover:text-ai-primary"
                    >
                      {doc.title}
                    </button>
                  </td>
                  <td className="px-4 py-3">{doc.document_type}</td>
                  <td className="px-4 py-3">{doc.course_id || '—'} / {doc.module_id || '—'}</td>
                  <td className="px-4 py-3 capitalize">{doc.difficulty}</td>
                  <td className="px-4 py-3">
                    {STATUSES[doc.status] || doc.status}
                    {doc.last_error && (
                      <span className="ml-2 text-xs text-ai-error">({doc.last_error})</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={doc.is_published ? 'text-ai-success' : 'text-ai-text-muted'}>
                      {doc.is_published ? 'Опубликован' : 'Не опубликован'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => handleProcess(doc.id)}
                        disabled={actionLoading === `process-${doc.id}`}
                        className="ai-btn-outline px-2 py-1 text-xs"
                      >
                        {actionLoading === `process-${doc.id}` ? '…' : 'Обработать'}
                      </button>
                      <button
                        onClick={() => handlePublish(doc)}
                        disabled={actionLoading === `publish-${doc.id}`}
                        className="ai-btn-outline px-2 py-1 text-xs"
                      >
                        {actionLoading === `publish-${doc.id}` ? '…' : doc.is_published ? 'Снять' : 'Опубликовать'}
                      </button>
                      <button
                        onClick={() => handleDelete(doc.id)}
                        disabled={actionLoading === `delete-${doc.id}`}
                        className="ai-btn-outline px-2 py-1 text-xs text-ai-error hover:text-ai-error"
                      >
                        {actionLoading === `delete-${doc.id}` ? '…' : 'Удалить'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default KbDocuments;
