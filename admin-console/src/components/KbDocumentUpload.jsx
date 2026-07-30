import { useState } from 'react';
import { uploadKbDocument } from '../api/backend';

const DOCUMENT_TYPES = [
  { id: 'lecture', label: 'Лекция' },
  { id: 'methodical', label: 'Методичка' },
  { id: 'faq', label: 'FAQ' },
  { id: 'instruction', label: 'Инструкция' },
  { id: 'glossary', label: 'Глоссарий' },
  { id: 'example', label: 'Пример' },
  { id: 'external', label: 'Внешний ресурс' },
];

const DIFFICULTIES = [
  { id: 'beginner', label: 'Базовый' },
  { id: 'intermediate', label: 'Средний' },
  { id: 'advanced', label: 'Углублённый' },
];

function KbDocumentUpload({ onDone }) {
  const [form, setForm] = useState({
    title: '',
    document_type: 'lecture',
    course_id: 3,
    module_id: '',
    topic_id: '',
    difficulty: 'beginner',
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
    formData.append('title', form.title);
    formData.append('document_type', form.document_type);
    formData.append('course_id', form.course_id || '');
    formData.append('module_id', form.module_id || '');
    formData.append('topic_id', form.topic_id || '');
    formData.append('difficulty', form.difficulty);
    formData.append('language', form.language);
    formData.append('description', form.description);
    formData.append('source_url', form.source_url);
    formData.append('file', file);

    setLoading(true);
    try {
      await uploadKbDocument(formData);
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="font-display text-xl font-bold text-ai-text">Загрузка документа</h2>
        <p className="text-sm text-ai-text-muted">Создайте карточку документа и загрузите файл.</p>
      </div>

      {error && (
        <div className="mb-4 rounded-ai border border-ai-error/20 bg-red-500/10 p-4 text-sm text-ai-error">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="ai-card max-w-3xl space-y-4 p-5">
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
            <label className="mb-1 block text-sm text-ai-text-secondary">Тип документа</label>
            <select
              value={form.document_type}
              onChange={(event) => handleChange('document_type', event.target.value)}
              className="ai-input w-full px-4 py-2"
            >
              {DOCUMENT_TYPES.map((type) => (
                <option key={type.id} value={type.id}>{type.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm text-ai-text-secondary">Сложность</label>
            <select
              value={form.difficulty}
              onChange={(event) => handleChange('difficulty', event.target.value)}
              className="ai-input w-full px-4 py-2"
            >
              {DIFFICULTIES.map((level) => (
                <option key={level.id} value={level.id}>{level.label}</option>
              ))}
            </select>
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

          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm text-ai-text-secondary">Файл</label>
            <input
              type="file"
              accept=".md,.txt,.pdf"
              onChange={(event) => setFile(event.target.files[0])}
              required
              className="ai-input w-full px-4 py-2 text-sm"
            />
            <p className="mt-1 text-xs text-ai-text-muted">Поддерживаются Markdown, TXT, PDF.</p>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onDone}
            className="ai-btn-outline px-5 py-2"
          >
            Отмена
          </button>
          <button
            type="submit"
            disabled={loading}
            className="ai-btn px-5 py-2"
          >
            {loading ? 'Загрузка…' : 'Сохранить документ'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default KbDocumentUpload;
