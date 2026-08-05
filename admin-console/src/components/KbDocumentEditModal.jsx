import { useEffect, useState } from 'react';
import { useDemo } from '../contexts/DemoContext';
import { updateKbDocument } from '../api/backend';

const DOCUMENT_TYPES = [
  { id: 'lecture', label: 'Лекция' },
  { id: 'methodical', label: 'Методичка' },
  { id: 'faq', label: 'FAQ' },
  { id: 'instruction', label: 'Инструкция' },
  { id: 'glossary', label: 'Глоссарий' },
  { id: 'example', label: 'Пример' },
  { id: 'external', label: 'Внешний ресурс' },
];

function KbDocumentEditModal({ document, onDone, onCancel }) {
  const { isDemo } = useDemo();
  const [form, setForm] = useState({
    title: '',
    document_type: 'lecture',
    course_id: '',
    module_id: '',
    topic_id: '',
    language: 'ru',
    description: '',
    source_url: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (document) {
      setForm({
        title: document.title || '',
        document_type: document.document_type || 'lecture',
        course_id: document.course_id || '',
        module_id: document.module_id || '',
        topic_id: document.topic_id || '',
        language: document.language || 'ru',
        description: document.description || '',
        source_url: document.source_url || '',
      });
    }
  }, [document]);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    if (isDemo) {
      setError('Демо-режим: изменения запрещены.');
      return;
    }

    const payload = {
      title: form.title,
      document_type: form.document_type,
      course_id: form.course_id ? parseInt(form.course_id, 10) : null,
      module_id: form.module_id ? parseInt(form.module_id, 10) : null,
      topic_id: form.topic_id ? parseInt(form.topic_id, 10) : null,
      language: form.language,
      description: form.description || null,
      source_url: form.source_url || null,
    };

    setLoading(true);
    try {
      await updateKbDocument(document.id, payload);
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="ai-modal-overlay"
      onClick={onCancel}
      role="presentation"
    >
      <div
        className="ai-modal"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="ai-modal__header">
          <h4 className="ai-modal__title">Редактирование метаданных</h4>
          <button
            onClick={onCancel}
            className="ai-modal__close"
            type="button"
            aria-label="Закрыть"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4">
          {error && (
            <div className="ai-error mb-4 text-sm">{error}</div>
          )}

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

          <div className="ai-modal__actions mt-4">
            <button
              type="button"
              onClick={onCancel}
              className="ai-btn-outline px-5 py-2"
              disabled={loading}
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={isDemo || loading}
              title={isDemo ? 'Демо-режим: изменения запрещены' : undefined}
              className="ai-btn px-5 py-2"
            >
              {loading ? 'Сохранение…' : 'Сохранить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default KbDocumentEditModal;
