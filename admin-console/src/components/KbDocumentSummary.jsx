import { useEffect, useMemo, useState } from 'react';
import {
  getKbDocumentDetail,
  getKbVersionText,
  getKbVersionChunks,
  publishKbDocument,
  processKbDocument,
  deleteKbDocument,
  reindexKbVersion,
  activateKbVersion,
} from '../api/backend';

const STATUSES = {
  draft: 'Черновик',
  pending: 'В ожидании',
  processing: 'Обработка',
  indexed: 'Индексирован',
  error: 'Ошибка',
  archived: 'Архив',
};

const STATUS_VARIANTS = {
  draft: 'muted',
  pending: 'info',
  processing: 'warning',
  indexed: 'ok',
  error: 'error',
  archived: 'muted',
};

function StatusBadge({ status }) {
  const variant = STATUS_VARIANTS[status] || 'muted';
  const label = STATUSES[status] || status;
  return <span className={`ai-status ai-status--${variant}`}>{label}</span>;
}

function SectionBox({ title, children, className = '' }) {
  return (
    <div className={`rounded-ai border border-ai-border bg-ai-surface p-3 ${className}`}>
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ai-text-muted">
        {title}
      </h4>
      {children}
    </div>
  );
}

function KbDocumentSummary({ documentId, onAction }) {
  const [bundle, setBundle] = useState(null);
  const [textPreview, setTextPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [selectedVersionId, setSelectedVersionId] = useState(null);

  const document = bundle?.document;
  const activeVersion = bundle?.active_version;
  const chunks = bundle?.chunks || [];

  const effectiveVersionId = selectedVersionId || activeVersion?.id;

  async function load() {
    if (!documentId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getKbDocumentDetail(documentId);
      setBundle(data);
      setSelectedVersionId((prev) => prev || data.active_version?.id);
      if (data.active_version?.id) {
        const text = await getKbVersionText(documentId, data.active_version.id);
        setTextPreview(text);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  const handleVersionSelect = async (versionId) => {
    setSelectedVersionId(versionId);
    try {
      const text = await getKbVersionText(documentId, versionId);
      setTextPreview(text);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleAction = async (key, fn) => {
    setActionLoading(key);
    setError(null);
    try {
      await fn();
      await load();
      onAction?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const versionChunks = useMemo(() => {
    return chunks.filter((chunk) => chunk.version_id === effectiveVersionId);
  }, [chunks, effectiveVersionId]);

  if (loading) {
    return (
      <div className="ai-card flex h-full items-center justify-center p-4">
        <span className="mr-2 inline-block animate-pulse">●</span>
        Загрузка сводки…
      </div>
    );
  }

  if (error) {
    return (
      <div className="ai-card h-full p-4">
        <div className="ai-error text-sm">{error}</div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="ai-card flex h-full items-center justify-center p-4">
        <div className="ai-empty">Выберите документ из списка.</div>
      </div>
    );
  }

  return (
    <div className="ai-card flex h-full flex-col overflow-hidden">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="ai-section__title">СВОДКА ДОКУМЕНТА</h3>
            <StatusBadge status={document.status} />
            {document.is_published && (
              <span className="ai-status ai-status--ok">Опубликован</span>
            )}
          </div>
          <p className="ai-section__subtitle mt-1">{document.title}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => handleAction('process', () => processKbDocument(document.id))}
            disabled={actionLoading === 'process'}
            className="ai-btn-outline px-2 py-1 text-xs"
            type="button"
          >
            {actionLoading === 'process' ? '…' : 'Обработать'}
          </button>
          <button
            onClick={() =>
              handleAction('publish', () => publishKbDocument(document.id, !document.is_published))
            }
            disabled={actionLoading === 'publish'}
            className="ai-btn-outline px-2 py-1 text-xs"
            type="button"
          >
            {actionLoading === 'publish' ? '…' : document.is_published ? 'Снять' : 'Опубликовать'}
          </button>
          <button
            onClick={() => {
              if (window.confirm('Удалить документ? Это действие необратимо.')) {
                handleAction('delete', () => deleteKbDocument(document.id));
              }
            }}
            disabled={actionLoading === 'delete'}
            className="ai-btn-outline px-2 py-1 text-xs text-ai-error"
            type="button"
          >
            {actionLoading === 'delete' ? '…' : 'Удалить'}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto pr-1">
        {/* Metadata */}
        <SectionBox title="Метаданные" className="mb-3">
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <div>
              <span className="text-ai-text-muted">ID:</span>{' '}
              <span className="text-ai-text-secondary">{document.id}</span>
            </div>
            <div>
              <span className="text-ai-text-muted">Тип:</span>{' '}
              <span className="text-ai-text-secondary capitalize">{document.document_type}</span>
            </div>
            <div>
              <span className="text-ai-text-muted">Сложность:</span>{' '}
              <span className="text-ai-text-secondary">{document.difficulty}</span>
            </div>
            <div>
              <span className="text-ai-text-muted">Язык:</span>{' '}
              <span className="text-ai-text-secondary">{document.language}</span>
            </div>
            <div>
              <span className="text-ai-text-muted">Курс / Модуль / Тема:</span>{' '}
              <span className="text-ai-text-secondary">
                {document.course_id || '—'} / {document.module_id || '—'} / {document.topic_id || '—'}
              </span>
            </div>
            <div>
              <span className="text-ai-text-muted">Активная версия:</span>{' '}
              <span className="text-ai-text-secondary">
                v{activeVersion?.version_number || '—'} (ID {activeVersion?.id || '—'})
              </span>
            </div>
          </div>
          {document.description && (
            <p className="mt-2 text-sm text-ai-text-secondary">{document.description}</p>
          )}
          {document.last_error && (
            <div className="mt-2 text-xs text-ai-error">Ошибка: {document.last_error}</div>
          )}
        </SectionBox>

        {/* Versions table */}
        <SectionBox title="Версии" className="mb-3">
          <div className="overflow-x-auto">
            <table className="ai-table text-xs">
              <thead>
                <tr>
                  <th>Версия</th>
                  <th>Файл</th>
                  <th>Статус</th>
                  <th>Чанков</th>
                  <th>Активна</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {document.versions?.map((version) => (
                  <tr key={version.id}>
                    <td>v{version.version_number}</td>
                    <td className="max-w-[160px] truncate" title={version.original_filename}>
                      {version.original_filename}
                    </td>
                    <td>
                      <StatusBadge status={version.status} />
                    </td>
                    <td>{version.chunk_count || 0}</td>
                    <td>{version.id === activeVersion?.id ? 'Да' : '—'}</td>
                    <td>
                      <div className="flex gap-1">
                        <button
                          onClick={() =>
                            handleAction('activate-version', () =>
                              activateKbVersion(document.id, version.id)
                            )
                          }
                          disabled={
                            actionLoading === 'activate-version' || version.id === activeVersion?.id
                          }
                          className="ai-btn-outline px-2 py-0.5 text-xs"
                          type="button"
                        >
                          {actionLoading === 'activate-version' ? '…' : 'Активировать'}
                        </button>
                        <button
                          onClick={() =>
                            handleAction('reindex-version', () =>
                              reindexKbVersion(document.id, version.id)
                            )
                          }
                          disabled={actionLoading === 'reindex-version'}
                          className="ai-btn-outline px-2 py-0.5 text-xs"
                          type="button"
                        >
                          {actionLoading === 'reindex-version' ? '…' : 'Переиндексировать'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionBox>

        {/* Text preview */}
        {textPreview && (
          <SectionBox title={`Preview текста (v${textPreview.version_number})`} className="mb-3">
            <div className="text-xs text-ai-text-muted mb-1">
              {textPreview.preview_length} / {textPreview.total_length} символов
            </div>
            <pre className="ai-text-preview__box max-h-[200px] overflow-auto rounded-ai bg-black/20 p-2 text-xs">
              {textPreview.preview}
            </pre>
          </SectionBox>
        )}

        {/* Chunks preview */}
        <SectionBox title={`Чанки выбранной версии (${versionChunks.length})`}>
          {versionChunks.length === 0 ? (
            <div className="ai-empty py-4">Нет чанков для выбранной версии.</div>
          ) : (
            <div className="flex flex-col gap-2 max-h-[200px] overflow-auto pr-1">
              {versionChunks.map((chunk) => (
                <div
                  key={chunk.id}
                  className="rounded-ai border border-ai-border-subtle bg-black/10 p-2 text-xs"
                >
                  <div className="mb-1 flex items-center gap-2 text-ai-text-muted">
                    <span>#{chunk.chunk_index}</span>
                    <span>·</span>
                    <span>{chunk.token_count || 0} токенов</span>
                  </div>
                  <div className="line-clamp-3 text-ai-text-secondary">
                    {chunk.content_preview || '(нет preview)'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionBox>
      </div>
    </div>
  );
}

export default KbDocumentSummary;
