import { useState } from 'react';
import { uploadKbDocument, uploadKbVersion } from '../api/backend';

const DOCUMENT_TYPES = [
  { id: 'lecture', label: 'Лекция' },
  { id: 'methodical', label: 'Методичка' },
  { id: 'faq', label: 'FAQ' },
  { id: 'instruction', label: 'Инструкция' },
  { id: 'glossary', label: 'Глоссарий' },
  { id: 'example', label: 'Пример' },
  { id: 'external', label: 'Внешний ресурс' },
];

function KbDocumentUpload({ mode = 'document', documentId, onDone }) {
  const isVersion = mode === 'version';
  const [form, setForm] = useState({
    title: '',
    document_type: 'lecture',
    course_id: 3,
    module_id: '',
    topic_id: '',
    language: 'ru',
    description: '',
    source_url: '',
  });
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    if (!file) {
      setError('Выберите файл.');
      return;
    }

    const formData = new FormData();

    if (isVersion) {
      formData.append('file', file);
    } else {
      formData.append('title', form.title);
      formData.append('document_type', form.document_type);
      formData.append('course_id', form.course_id || '');
      formData.append('module_id', form.module_id || '');
      formData.append('topic_id', form.topic_id || '');
      formData.append('language', form.language);
      formData.append('description', form.description);
      formData.append('source_url', form.source_url);
      formData.append('file', file);
    }

    setLoading(true);
    try {
      if (isVersion) {
        await uploadKbVersion(documentId, formData);
      } else {
        await uploadKbDocument(formData);
      }
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formContent = (
    <>
      {error && (
        <div className="mb-4 rounded-ai border border-ai-error/20 bg-red-500/10 p-4 text-sm text-ai-error">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {!isVersion && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm text-ai-text-secondary">Название</label>
              <input
                type="text"
                value={form.title}
                onChange={(event) => handleChange('title', event.target.value)}
                required
                className="ai-input w-full"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm text-ai-text-secondary">Тип документа</label>
              <select
                value={form.document_type}
                onChange={(event) => handleChange('document_type', event.target.value)}
                className="ai-input w-full"
              >
                {DOCUMENT_TYPES.map((type) => (
                  <option key={type.id} value={type.id}>{type.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm text-ai-text-secondary">ID курса</label>
              <input
                type="number"
                value={form.course_id}
                onChange={(event) => handleChange('course_id', event.target.value)}
                className="ai-input w-full"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm text-ai-text-secondary">ID модуля</label>
              <input
                type="number"
                value={form.module_id}
                onChange={(event) => handleChange('module_id', event.target.value)}
                className="ai-input w-full"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm text-ai-text-secondary">ID темы</label>
              <input
                type="number"
                value={form.topic_id}
                onChange={(event) => handleChange('topic_id', event.target.value)}
                className="ai-input w-full"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm text-ai-text-secondary">Язык</label>
              <input
                type="text"
                value={form.language}
                onChange={(event) => handleChange('language', event.target.value)}
                className="ai-input w-full"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm text-ai-text-secondary">Описание</label>
              <textarea
                value={form.description}
                onChange={(event) => handleChange('description', event.target.value)}
                rows={8}
                className="ai-textarea w-full"
                style={{ minHeight: '200px', resize: 'vertical' }}
              />
            </div>

            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm text-ai-text-secondary">URL источника</label>
              <input
                type="url"
                value={form.source_url}
                onChange={(event) => handleChange('source_url', event.target.value)}
                className="ai-input w-full"
              />
            </div>
          </div>
        )}

        <div>
          <label className="mb-1 block text-sm text-ai-text-secondary">Файл</label>
          <input
            type="file"
            accept=".md,.txt,.pdf"
            onChange={(event) => setFile(event.target.files[0])}
            required
            className="ai-input w-full text-sm"
          />
          <p className="mt-1 text-xs text-ai-text-muted">Поддерживаются Markdown, TXT, PDF.</p>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onDone}
            className="ai-btn-outline px-5 py-2"
            disabled={loading}
          >
            Отмена
          </button>
          <button
            type="submit"
            disabled={loading}
            className="ai-btn px-5 py-2"
          >
            {loading ? 'Загрузка…' : isVersion ? 'Загрузить версию' : 'Сохранить документ'}
          </button>
        </div>
      </form>
    </>
  );

  if (isVersion) {
    return (
      <div
        className="ai-modal-overlay"
        onClick={onDone}
        role="presentation"
      >
        <div
          className="ai-modal"
          onClick={(event) => event.stopPropagation()}
          role="dialog"
          aria-modal="true"
        >
          <div className="ai-modal__header">
            <h4 className="ai-modal__title">Загрузка новой версии</h4>
            <button
              onClick={onDone}
              className="ai-modal__close"
              type="button"
              aria-label="Закрыть"
            >
              ×
            </button>
          </div>
          <div className="p-4">{formContent}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="font-display text-xl font-bold text-ai-text">Загрузка документа</h2>
        <p className="text-sm text-ai-text-muted">Создайте карточку документа и загрузите файл.</p>
      </div>
      <div className="ai-card max-w-3xl p-5">{formContent}</div>
    </div>
  );
}

export default KbDocumentUpload;
