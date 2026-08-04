import { useEffect, useMemo, useState } from 'react';
import {
  getKbDocumentDetail,
  getKbVersionText,
  getKbVersionChunks,
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

function SectionBox({ title, children, className = '', right = null }) {
  return (
    <div className={`rounded-ai border border-ai-border bg-ai-surface p-2 flex flex-col ${className}`}>
      <div className="flex items-center justify-between gap-2 mb-1.5">
        {title && (
          <h4 className="text-[0.75rem] font-semibold uppercase tracking-wide text-ai-text-muted">
            {title}
          </h4>
        )}
        {right}
      </div>
      {children}
    </div>
  );
}

function CompactRow({ label, value, mono = false }) {
  return (
    <div className="grid grid-cols-[7.5rem_1fr] items-baseline gap-2 text-xs leading-tight min-w-0">
      <span className="text-ai-text-muted">{label}:</span>
      <span
        className={`text-ai-text truncate ${mono ? 'font-mono' : ''}`}
        title={value}
      >
        {value || '—'}</span>
    </div>
  );
}

function KbDocumentSummary({ documentId, onAction, onOpenTextEditor }) {
  const [bundle, setBundle] = useState(null);
  const [textStage, setTextStage] = useState('cleaned');
  const [textPreview, setTextPreview] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [expandedChunkId, setExpandedChunkId] = useState(null);

  const document = bundle?.document;
  const activeVersion = bundle?.active_version;
  const execution = bundle?.execution;

  async function loadTextPreview(versionId, stage) {
    if (!documentId || !versionId) return;
    try {
      const text = await getKbVersionText(documentId, versionId, false, stage);
      setTextPreview(text);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadChunks(versionId) {
    if (!documentId || !versionId) return;
    try {
      const data = await getKbVersionChunks(documentId, versionId);
      setChunks(data);
    } catch (err) {
      setError(err.message);
    }
  }

  async function load() {
    if (!documentId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getKbDocumentDetail(documentId);
      setBundle(data);
      const versionId = data.active_version?.id;
      if (versionId) {
        await loadTextPreview(versionId, textStage);
        await loadChunks(versionId);
      } else {
        setTextPreview(null);
        setChunks([]);
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

  useEffect(() => {
    if (activeVersion?.id) {
      loadTextPreview(activeVersion.id, textStage);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [textStage, activeVersion?.id]);

  const versionChunks = useMemo(() => chunks, [chunks]);

  const handleVersionAction = async (key, fn) => {
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
    <div className="ai-card flex h-full flex-col overflow-hidden p-2">
      {/* Header */}
      <div className="mb-2 flex items-center gap-2 border-b border-ai-border pb-2">
        <h3 className="ai-section__title">СВОДКА ДОКУМЕНТА</h3>
        <StatusBadge status={document.status} />
        {document.is_published && <span className="ai-status ai-status--ok">Опубликован</span>}
      </div>

      <div className="flex-1 overflow-y-auto pr-1 space-y-2 min-h-0">
        {/* Passport + Operation */}
        <div className="grid grid-cols-2 gap-2">
          <SectionBox title="Паспорт">
            <div className="space-y-1">
              <CompactRow label="ID" value={document.id} mono />
              <CompactRow label="Название" value={document.title} />
              <CompactRow label="Тип" value={document.document_type} />
              <CompactRow label="Язык" value={document.language} />
              <CompactRow
                label="Курс / Модуль / Тема"
                value={`${document.course_id || '—'} / ${document.module_id || '—'} / ${document.topic_id || '—'}`}
              />
            </div>
          </SectionBox>
          <SectionBox title="Эксплуатация">
            <div className="space-y-1">
              <CompactRow label="Файл" value={activeVersion?.original_filename} />
              <CompactRow label="Provider" value={execution?.provider} />
              <CompactRow label="Model" value={execution?.model} />
              <CompactRow label="PostgreSQL" value={execution?.postgres_status} />
              <CompactRow
                label="Индексация"
                value={
                  execution?.indexed_at
                    ? new Date(execution.indexed_at).toLocaleString('ru-RU')
                    : null
                }
              />
              <CompactRow label="sha256" value={execution?.sha256} mono />
            </div>
          </SectionBox>
        </div>

        {/* Description */}
        {(document.description || document.source_url) && (
          <SectionBox title="Описание">
            <div className="space-y-1">
              {document.description && (
                <CompactRow label="Описание" value={document.description} />
              )}
              {document.source_url && (
                <CompactRow label="URL" value={document.source_url} />
              )}
            </div>
          </SectionBox>
        )}

        {/* Versions table */}
        <div className="rounded-ai border border-ai-border bg-ai-surface p-2 flex flex-col min-h-0">
          <div className="overflow-x-auto max-h-[132px]">
            <table className="ai-table text-xs">
              <thead>
                <tr>
                  <th className="text-[0.65rem]">Версия</th>
                  <th className="text-[0.65rem]">Файл</th>
                  <th className="text-[0.65rem]">Статус</th>
                  <th className="text-[0.65rem]">Чанков</th>
                  <th className="text-[0.65rem]">Активна</th>
                  <th className="text-[0.65rem]">Дата</th>
                  <th className="text-[0.65rem]">Действие</th>
                </tr>
              </thead>
              <tbody>
                {document.versions?.map((version) => {
                  const isActive = version.id === activeVersion?.id;
                  return (
                    <tr key={version.id}>
                      <td>v{version.version_number}</td>
                      <td className="max-w-[120px] truncate" title={version.original_filename}>
                        {version.original_filename}
                      </td>
                      <td><StatusBadge status={version.status} /></td>
                      <td>{version.chunk_count || 0}</td>
                      <td>{isActive ? 'Да' : '—'}</td>
                      <td>
                        {version.created_at
                          ? new Date(version.created_at).toLocaleString('ru-RU')
                          : '—'}
                      </td>
                      <td>
                        {isActive ? (
                          <button
                            onClick={() =>
                              handleVersionAction(`reindex-${version.id}`, () =>
                                reindexKbVersion(document.id, version.id)
                              )
                            }
                            disabled={actionLoading === `reindex-${version.id}`}
                            className="ai-btn-outline px-2 py-0.5 text-xs"
                            type="button"
                          >
                            {actionLoading === `reindex-${version.id}` ? '…' : 'Переиндексировать'}
                          </button>
                        ) : (
                          <button
                            onClick={() =>
                              handleVersionAction(`activate-${version.id}`, () =>
                                activateKbVersion(document.id, version.id)
                              )
                            }
                            disabled={actionLoading === `activate-${version.id}`}
                            className="ai-btn-outline px-2 py-0.5 text-xs"
                            type="button"
                          >
                            {actionLoading === `activate-${version.id}` ? '…' : 'Активировать'}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Text preview */}
        <SectionBox
          title="PREVIEW ТЕКСТА"
          right={
            <div className="flex items-center gap-2">
              <button
                onClick={() => setTextStage('raw')}
                className={`px-2 py-0.5 text-xs rounded-ai border ${
                  textStage === 'raw'
                    ? 'border-ai-primary bg-ai-primary-light text-ai-text'
                    : 'border-ai-border text-ai-text-muted hover:border-ai-text-muted'
                }`}
                type="button"
              >
                RAW
              </button>
              <button
                onClick={() => setTextStage('cleaned')}
                className={`px-2 py-0.5 text-xs rounded-ai border ${
                  textStage === 'cleaned'
                    ? 'border-ai-primary bg-ai-primary-light text-ai-text'
                    : 'border-ai-border text-ai-text-muted hover:border-ai-text-muted'
                }`}
                type="button"
              >
                Очищенный
              </button>
              <button
                onClick={() => onOpenTextEditor?.({ stage: textStage })}
                className="ai-btn-outline px-2 py-0.5 text-xs"
                type="button"
              >
                Открыть
              </button>
            </div>
          }
        >
          <div className="flex items-center justify-between gap-2 mb-1.5">
            {textPreview && (
              <span className="text-xs text-ai-text-muted">
                {textPreview.preview_length} / {textPreview.total_length}
              </span>
            )}
          </div>
          {textPreview ? (
            <pre className="ai-text-preview__box max-h-[180px] overflow-auto rounded-ai bg-black/20 p-2 text-xs">
              {textPreview.preview}
            </pre>
          ) : (
            <div className="ai-empty py-2 text-xs">Нет preview текста.</div>
          )}
        </SectionBox>

        {/* Chunks */}
        <SectionBox title={`ЧАНКИ (${versionChunks.length})`} className="flex-1 min-h-0">
          {versionChunks.length === 0 ? (
            <div className="ai-empty py-2 text-xs">Нет чанков.</div>
          ) : (
            <div className="flex flex-col gap-1.5 overflow-auto pr-1 flex-1 min-h-0">
              {versionChunks.map((chunk) => {
                const isExpanded = expandedChunkId === chunk.id;
                return (
                  <div
                    key={chunk.id}
                    className="rounded-ai border border-ai-border-subtle bg-black/10 p-1.5 text-xs"
                  >
                    <div className="mb-1 flex items-center justify-between gap-2 text-ai-text-muted">
                      <div className="flex items-center gap-2">
                        <span>#{chunk.chunk_index}</span>
                        <span>·</span>
                        <span>{chunk.token_count || 0} токенов</span>
                      </div>
                      <button
                        onClick={() => setExpandedChunkId(isExpanded ? null : chunk.id)}
                        className="text-ai-primary hover:underline text-xs"
                        type="button"
                      >
                        {isExpanded ? 'Свернуть' : 'Раскрыть'}
                      </button>
                    </div>
                    <div
                      className={`text-ai-text-secondary whitespace-pre-wrap break-words ${
                        isExpanded ? '' : 'line-clamp-3'
                      }`}
                    >
                      {chunk.content_preview || '(нет preview)'}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </SectionBox>
      </div>
    </div>
  );
}

export default KbDocumentSummary;
