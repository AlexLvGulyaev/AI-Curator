import { useEffect, useState } from 'react';
import { getKbVersionText, saveKbVersionText } from '../api/backend';

function KbDocumentTextEditor({ documentId, versionId, stage = 'cleaned', onDone, onCancel }) {
  const [text, setText] = useState('');
  const [originalText, setOriginalText] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const isReadOnly = stage === 'raw';

  useEffect(() => {
    let isMounted = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getKbVersionText(documentId, versionId, true, stage);
        if (isMounted) {
          setText(data.preview || '');
          setOriginalText(data.preview || '');
        }
      } catch (err) {
        if (isMounted) setError(err.message);
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    load();
    return () => {
      isMounted = false;
    };
  }, [documentId, versionId, stage]);

  async function handleSave() {
    if (isReadOnly) return;
    setSaving(true);
    setError(null);
    try {
      await saveKbVersionText(documentId, versionId, text, 'cleaned', true);
      onDone?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const hasChanges = text !== originalText;

  return (
    <div className="ai-modal-overlay">
      <div className="ai-modal">
        <div className="ai-modal__header">
          <h3 className="ai-modal__title">
            {stage === 'raw' ? 'RAW текст документа' : 'Очищенный текст документа'}
          </h3>
          <button onClick={onCancel} className="ai-modal__close" type="button">
            ×
          </button>
        </div>

        {error && (
          <div className="ai-error m-4 text-sm">{error}</div>
        )}

        {loading ? (
          <div className="ai-loading m-4 text-sm">
            <span className="mr-2 inline-block animate-pulse">●</span>
            Загрузка текста…
          </div>
        ) : (
          <textarea
            className="ai-textarea ai-textarea--modal"
            value={text}
            onChange={(e) => setText(e.target.value)}
            readOnly={isReadOnly}
            spellCheck={false}
          />
        )}

        <div className="ai-modal__actions">
          <button
            onClick={onCancel}
            className="ai-btn-outline px-4 py-2 text-sm"
            type="button"
            disabled={saving}
          >
            Закрыть
          </button>
          {!isReadOnly && (
            <button
              onClick={handleSave}
              disabled={saving || !hasChanges}
              className="ai-btn px-4 py-2 text-sm"
              type="button"
            >
              {saving ? '…' : 'Сохранить и переиндексировать'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default KbDocumentTextEditor;
