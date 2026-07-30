import { useEffect, useState } from 'react';
import { getKbDocument, processKbDocument, publishKbDocument, uploadKbVersion, updateKbDocument } from '../api/backend';

const STATUSES = {
  draft: 'Черновик',
  pending: 'В ожидании',
  processing: 'Обработка',
  indexed: 'Индексирован',
  error: 'Ошибка',
  archived: 'Архив',
};

function KbDocumentDetail({ documentId, onBack }) {
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [form, setForm] = useState({});
  const [versionFile, setVersionFile] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getKbDocument(documentId);
      setDocument(data);
      setForm({
        title: data.title,
        document_type: data.document_type,
        course_id: data.course_id || '',
        module_id: data.module_id || '',
        topic_id: data.topic_id || '',
        difficulty: data.difficulty,
        language: data.language,
        description: data.description || '',
        source_url: data.source_url || '',
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [documentId]);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleUpdate = async (event) => {
    event.preventDefault();
    setActionLoading('update');
    try {
      const data = { ...form };
      if (data.course_id === '') data.course_id = null;
      if (data.module_id === '') data.module_id = null;
      if (data.topic_id === '') data.topic_id = null;
      await updateKbDocument(documentId, data);
      await load();
      setEditMode(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleProcess = async () => {
    setActionLoading('process');
    try {
      await processKbDocument(documentId);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handlePublish = async () => {
    setActionLoading('publish');
    try {
      await publishKbDocument(documentId, !document.is_published);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleUploadVersion = async (event) => {
    event.preventDefault();
    if (!versionFile) return;
    setActionLoading('version');
    const formData = new FormData();
    formData.append('file', versionFile);
    try {
      await uploadKbVersion(documentId, formData);
      await load();
      setVersionFile(null);
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
        Загрузка документа…
      </div>
    );
  }

  if (error && !document) {
    return (
      <div className="m-6 rounded-ai border border-ai-error/20 bg-red-500/10 p-4 text-sm text-ai-error">
        {error}
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="ai-btn-outline px-3 py-1.5 text-sm"
          >
            ← Назад
          </button>
          <h2 className="font-display text-xl font-bold text-ai-text">Карточка документа</h2>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setEditMode((prev) => !prev)}
            className="ai-btn-outline px-4 py-2"
          >
            {editMode ? 'Отменить редактирование' : 'Редактировать'}
          </button>
          <button
            onClick={handleProcess}
            disabled={actionLoading === 'process'}
            className="ai-btn-outline px-4 py-2"
          >
            {actionLoading === 'process' ? '…' : 'Обработать'}
          </button>
          <button
            onClick={handlePublish}
            disabled={actionLoading === 'publish'}
            className="ai-btn px-4 py-2"
          >
            {actionLoading === 'publish' ? '…' : document.is_published ? 'Снять с публикации' : 'Опубликовать'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-ai border border-ai-error/20 bg-red-500/10 p-4 text-sm text-ai-error">
          {error}
        </div>
      )}

      {editMode ? (
        <form onSubmit={handleUpdate} className="ai-card mb-6 space-y-4 p-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm text-ai-text-secondary">Название</label>
              <input
                type="text"
                value={form.title}
                onChange={(event) => handleChange('title', event.target.value)}
                required
                className="ai-input w-full px-4 py-2"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-ai-text-secondary">Тип</label>
              <input
                type="text"
                value={form.document_type}
                onChange={(event) => handleChange('document_type', event.target.value)}
                className="ai-input w-full px-4 py-2"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-ai-text-secondary">Сложность</label>
              <input
                type="text"
                value={form.difficulty}
                onChange={(event) => handleChange('difficulty', event.target.value)}
                className="ai-input w-full px-4 py-2"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-ai-text-secondary">ID курса</label>
              <input
                type="number"
                value={form.course_id}
                onChange={(event) => handleChange('course_id', event.target.value)}
                className="ai-input w-full px-4 py-2"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-ai-text-secondary">ID модуля</label>
              <input
                type="number"
                value={form.module_id}
                onChange={(event) => handleChange('module_id', event.target.value)}
                className="ai-input w-full px-4 py-2"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-ai-text-secondary">ID темы</label>
              <input
                type="number"
                value={form.topic_id}
                onChange={(event) => handleChange('topic_id', event.target.value)}
                className="ai-input w-full px-4 py-2"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-ai-text-secondary">Язык</label>
              <input
                type="text"
                value={form.language}
                onChange={(event) => handleChange('language', event.target.value)}
                className="ai-input w-full px-4 py-2"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm text-ai-text-secondary">Описание</label>
              <textarea
                value={form.description}
                onChange={(event) => handleChange('description', event.target.value)}
                rows={3}
                className="ai-textarea w-full px-4 py-2"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm text-ai-text-secondary">URL источника</label>
              <input
                type="url"
                value={form.source_url}
                onChange={(event) => handleChange('source_url', event.target.value)}
                className="ai-input w-full px-4 py-2"
              />
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={() => setEditMode(false)}
              className="ai-btn-outline px-5 py-2"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={actionLoading === 'update'}
              className="ai-btn px-5 py-2"
            >
              {actionLoading === 'update' ? 'Сохранение…' : 'Сохранить'}
            </button>
          </div>
        </form>
      ) : (
        <div className="ai-card mb-6 p-5">
          <div className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <p className="text-xs text-ai-text-muted">ID</p>
              <p className="text-sm text-ai-text">{document.id}</p>
            </div>
            <div>
              <p className="text-xs text-ai-text-muted">Статус</p>
              <p className="text-sm text-ai-text">{STATUSES[document.status] || document.status}</p>
            </div>
            <div>
              <p className="text-xs text-ai-text-muted">Публикация</p>
              <p className={`text-sm ${document.is_published ? 'text-ai-success' : 'text-ai-text-muted'}`}>
                {document.is_published ? 'Опубликован' : 'Не опубликован'}
              </p>
            </div>
            <div>
              <p className="text-xs text-ai-text-muted">Тип</p>
              <p className="text-sm text-ai-text">{document.document_type}</p>
            </div>
            <div>
              <p className="text-xs text-ai-text-muted">Сложность</p>
              <p className="text-sm text-ai-text capitalize">{document.difficulty}</p>
            </div>
            <div>
              <p className="text-xs text-ai-text-muted">Курс / Модуль / Тема</p>
              <p className="text-sm text-ai-text">{document.course_id || '—'} / {document.module_id || '—'} / {document.topic_id || '—'}</p>
            </div>
          </div>
          {document.description && (
            <div className="mb-4">
              <p className="text-xs text-ai-text-muted">Описание</p>
              <p className="text-sm text-ai-text-secondary">{document.description}</p>
            </div>
          )}
          {document.last_error && (
            <div className="rounded-ai border border-ai-error/20 bg-red-500/10 p-3 text-sm text-ai-error">
              {document.last_error}
            </div>
          )}
        </div>
      )}

      <div className="ai-card p-5">
        <h3 className="mb-4 font-display font-semibold text-ai-text">Версии</h3>
        <div className="mb-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-ai-border text-ai-text-muted">
                <th className="pb-2 pr-4">№</th>
                <th className="pb-2 pr-4">Имя файла</th>
                <th className="pb-2 pr-4">Размер</th>
                <th className="pb-2 pr-4">Статус</th>
                <th className="pb-2 pr-4">Фрагментов</th>
                <th className="pb-2 pr-4">Активна</th>
                <th className="pb-2">Создана</th>
              </tr>
            </thead>
            <tbody className="text-ai-text-secondary">
              {document.versions.map((version) => (
                <tr key={version.id} className="border-b border-ai-border-subtle">
                  <td className="py-3 pr-4">{version.version_number}</td>
                  <td className="py-3 pr-4">{version.original_filename}</td>
                  <td className="py-3 pr-4">{version.file_size ? `${Math.round(version.file_size / 1024)} KB` : '—'}</td>
                  <td className="py-3 pr-4">{version.status}</td>
                  <td className="py-3 pr-4">{version.chunk_count ?? '—'}</td>
                  <td className="py-3 pr-4">{version.is_active ? '✅' : '—'}</td>
                  <td className="py-3">{new Date(version.created_at).toLocaleString('ru-RU')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <form onSubmit={handleUploadVersion} className="flex items-end gap-3">
          <div className="flex-1">
            <label className="mb-1 block text-sm text-ai-text-secondary">Новая версия</label>
            <input
              type="file"
              accept=".md,.txt,.pdf"
              onChange={(event) => setVersionFile(event.target.files[0])}
              className="ai-input w-full px-4 py-2 text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={!versionFile || actionLoading === 'version'}
            className="ai-btn px-4 py-2"
          >
            {actionLoading === 'version' ? '…' : 'Загрузить версию'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default KbDocumentDetail;
