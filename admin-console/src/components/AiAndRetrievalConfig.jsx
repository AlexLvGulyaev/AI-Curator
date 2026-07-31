import { useEffect, useMemo, useState } from 'react';
import {
  getActiveAiConfig,
  updateActiveAiConfig,
  getRetrievalTuning,
  updateRetrievalTuning,
  getLlmProviders,
  updateLlmProvider,
  testLlmProvider,
} from '../api/backend';

const OPENAI_MODELS = [
  { value: 'gpt-4o-mini', label: 'gpt-4o-mini' },
  { value: 'gpt-4o', label: 'gpt-4o' },
];

const GIGACHAT_MODELS = [
  { value: 'GigaChat-Max', label: 'GigaChat-Max' },
];

function Section({ title, subtitle, children, className = '' }) {
  return (
    <div className={`ai-card ai-section ${className}`.trim()}>
      <div>
        <h3 className="ai-section__title">{title}</h3>
        {subtitle && <p className="ai-section__subtitle">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

function StatusBadge({ variant, label }) {
  const map = {
    active: 'ai-status--ok',
    ready: 'ai-status--ok',
    fallback: 'ai-status--info',
    'not-ready': 'ai-status--muted',
    disabled: 'ai-status--muted',
  };
  return <span className={`ai-status ${map[variant] || 'ai-status--muted'}`}>{label}</span>;
}

function InputRow({ label, children, inline = false }) {
  return (
    <div className={inline ? 'ai-field-row ai-field-row--inline' : 'ai-field-row'}>
      <label className="ai-field-label">{label}</label>
      {children}
    </div>
  );
}

function TextModal({ isOpen, title, value, onChange, onSave, onClose, saving }) {
  if (!isOpen) return null;
  return (
    <div className="ai-modal-overlay" onClick={onClose}>
      <div className="ai-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ai-modal__header">
          <h3 className="ai-modal__title">{title}</h3>
          <button type="button" className="ai-modal__close" onClick={onClose}>×</button>
        </div>
        <textarea
          className="ai-textarea ai-textarea--modal"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={saving}
        />
        <div className="ai-modal__actions">
          <button type="button" className="ai-btn ai-btn--secondary" onClick={onClose} disabled={saving}>
            Отмена
          </button>
          <button type="button" className="ai-btn" onClick={onSave} disabled={saving}>
            {saving ? 'Сохранение…' : 'Сохранить'}
          </button>
        </div>
      </div>
    </div>
  );
}

function AiAndRetrievalConfig() {
  const [config, setConfig] = useState(null);
  const [tuning, setTuning] = useState(null);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [saving, setSaving] = useState({});
  const [testResult, setTestResult] = useState(null);

  const [modal, setModal] = useState({ open: false, field: '', title: '', value: '' });

  const [activeProvider, setActiveProvider] = useState('openai');
  const [fallbackProvider, setFallbackProvider] = useState('gigachat');
  const [providerForms, setProviderForms] = useState({});
  const [tuningForms, setTuningForms] = useState({});

  async function load() {
    setLoading(true);
    setError(null);
    setMessage(null);
    setTestResult(null);
    try {
      const [cfg, tun, provs] = await Promise.all([
        getActiveAiConfig(),
        getRetrievalTuning(),
        getLlmProviders(),
      ]);
      setConfig(cfg);
      setTuning(tun);
      setProviders(provs);
      setProviderForms(
        provs.reduce((acc, p) => {
          acc[p.key] = { ...p };
          return acc;
        }, {}),
      );
      setTuningForms({ ...tun });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const textFields = useMemo(
    () => ({
      system_prompt: { title: 'Системный промпт' },
      output_rules: { title: 'Правила ответа' },
      refusal_answer_text: { title: 'Текст отказа' },
      beginner_instructions: { title: 'Инструкции для начинающих' },
      advanced_instructions: { title: 'Инструкции для продвинутых' },
      few_shot_examples: { title: 'Few-shot примеры' },
    }),
    [],
  );

  function openTextModal(field) {
    if (!config) return;
    setModal({ open: true, field, title: textFields[field].title, value: config[field] || '' });
  }

  function closeModal() {
    setModal((prev) => ({ ...prev, open: false }));
  }

  async function saveTextField() {
    if (!config) return;
    setSaving((prev) => ({ ...prev, [modal.field]: true }));
    setError(null);
    setMessage(null);
    try {
      const updated = await updateActiveAiConfig({ ...config, [modal.field]: modal.value });
      setConfig(updated);
      // success message removed
      closeModal();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving((prev) => ({ ...prev, [modal.field]: false }));
    }
  }

  async function saveBehaviorGroup() {
    if (!config) return;
    setSaving((prev) => ({ ...prev, behavior: true }));
    setError(null);
    setMessage(null);
    try {
      const updated = await updateActiveAiConfig({
        ...config,
        system_prompt: config.system_prompt,
        output_rules: config.output_rules,
        refusal_answer_text: config.refusal_answer_text,
        max_history_messages: config.max_history_messages,
      });
      setConfig(updated);
      // success message removed
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving((prev) => ({ ...prev, behavior: false }));
    }
  }

  async function saveInstructionsGroup() {
    if (!config) return;
    setSaving((prev) => ({ ...prev, instructions: true }));
    setError(null);
    setMessage(null);
    try {
      const updated = await updateActiveAiConfig({
        ...config,
        beginner_instructions: config.beginner_instructions,
        advanced_instructions: config.advanced_instructions,
        few_shot_examples: config.few_shot_examples,
      });
      setConfig(updated);
      // success message removed
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving((prev) => ({ ...prev, instructions: false }));
    }
  }

  async function saveProviderCard(key) {
    setSaving((prev) => ({ ...prev, [`provider_${key}`]: true }));
    setError(null);
    setMessage(null);
    try {
      const updated = await updateLlmProvider(key, providerForms[key]);
      setProviderForms((prev) => ({ ...prev, [key]: updated }));
      // success message removed
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving((prev) => ({ ...prev, [`provider_${key}`]: false }));
    }
  }

  async function runProviderTest(key) {
    setSaving((prev) => ({ ...prev, [`test_${key}`]: true }));
    setError(null);
    setTestResult(null);
    try {
      const result = await testLlmProvider(key);
      setTestResult(result);
      if (!result.ok) setError(result.message);
      else setMessage(result.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving((prev) => ({ ...prev, [`test_${key}`]: false }));
    }
  }

  async function saveTuningBlock(fields) {
    if (!tuning) return;
    setSaving((prev) => ({ ...prev, tuning: true }));
    setError(null);
    setMessage(null);
    try {
      const payload = {};
      fields.forEach((f) => {
        payload[f] = tuningForms[f];
      });
      const updated = await updateRetrievalTuning(payload);
      setTuning(updated);
      setTuningForms({ ...updated });
      // success message removed
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving((prev) => ({ ...prev, tuning: false }));
    }
  }

  function updateConfigField(field, value) {
    setConfig((prev) => (prev ? { ...prev, [field]: value } : prev));
  }

  function updateProviderForm(key, field, value) {
    setProviderForms((prev) => ({
      ...prev,
      [key]: { ...prev[key], [field]: value },
    }));
  }

  function updateTuningForm(field, value) {
    setTuningForms((prev) => ({ ...prev, [field]: value }));
  }

  if (loading) {
    return (
      <div className="ai-loading flex items-center gap-2">
        <span className="inline-block animate-pulse">●</span>
        Загрузка настроек…
      </div>
    );
  }

  if (error && !config) {
    return <div className="ai-error">{error}</div>;
  }

  const openai = providers.find((p) => p.key === 'openai');
  const gigachat = providers.find((p) => p.key === 'gigachat');

  return (
    <div className="ai-config-page">
      <div className="ai-page__header">
        <div>
          <h1 className="ai-page__title">AI & Retrieval</h1>
          <p className="ai-page__subtitle">Настройки LLM-провайдеров, поведения модели и параметров поиска.</p>
        </div>
        <button onClick={load} className="ai-btn ai-btn--small" type="button">
          Обновить
        </button>
      </div>

      {error && <div className="ai-error">{error}</div>}
      {message && <div className="ai-success">{message}</div>}

      {/* Top row: LLM providers + Retrieval */}
      <div className="ai-config-top">
        <Section title="LLM-провайдеры и активность" subtitle="Активный / fallback провайдер и карточки.">
          <div className="ai-provider-controls">
            <div className="ai-provider-selects">
              <InputRow label="Активный провайдер">
                <select
                  value={activeProvider}
                  onChange={(e) => setActiveProvider(e.target.value)}
                  className="ai-select"
                >
                  <option value="openai">OpenAI</option>
                  <option value="gigachat" disabled>GigaChat</option>
                </select>
              </InputRow>
              <InputRow label="Fallback провайдер">
                <select
                  value={fallbackProvider}
                  onChange={(e) => setFallbackProvider(e.target.value)}
                  className="ai-select"
                >
                  <option value="gigachat">GigaChat</option>
                  <option value="openai" disabled>OpenAI</option>
                </select>
              </InputRow>
            </div>
            <div className="ai-actions-center">
              <button type="button" className="ai-btn ai-btn--small" onClick={() => {}}>
                Сохранить
              </button>
            </div>
          </div>

          <div className="ai-provider-cards">
            {[openai, gigachat].filter(Boolean).map((p) => {
              const isImplemented = p.implementation_status === 'implemented';
              const form = providerForms[p.key] || p;
              return (
                <div key={p.key} className={`ai-provider-card ${!isImplemented ? 'ai-provider-card--muted' : ''}`}>
                  <div className="ai-provider-card__header">
                    <strong>{p.display_name}</strong>
                    <div className="ai-provider-badges">
                      {p.is_active && <StatusBadge variant="active" label="ACTIVE" />}
                      {p.is_fallback && <StatusBadge variant="fallback" label="FALLBACK" />}
                      {isImplemented ? <StatusBadge variant="ready" label="READY" /> : <StatusBadge variant="not-ready" label="NOT READY" />}
                    </div>
                  </div>

                  <InputRow label="Base URL / Endpoint">
                    <input
                      type="text"
                      className="ai-input"
                      value={form.base_url || ''}
                      onChange={(e) => updateProviderForm(p.key, 'base_url', e.target.value)}
                      disabled={!isImplemented}
                    />
                  </InputRow>

                  <InputRow label="Model">
                    <select
                      className="ai-select"
                      value={form.model || ''}
                      onChange={(e) => updateProviderForm(p.key, 'model', e.target.value)}
                      disabled={!isImplemented}
                    >
                      {(p.key === 'openai' ? OPENAI_MODELS : GIGACHAT_MODELS).map((m) => (
                        <option key={m.value} value={m.value}>{m.label}</option>
                      ))}
                    </select>
                  </InputRow>

                  <div className="ai-grid ai-grid--2">
                    <InputRow label="Temperature">
                      <input
                        type="number"
                        className="ai-input"
                        step="0.1"
                        min="0"
                        max="2"
                        value={form.temperature ?? ''}
                        onChange={(e) => updateProviderForm(p.key, 'temperature', e.target.value)}
                        disabled={!isImplemented}
                      />
                    </InputRow>
                    <InputRow label="Max tokens">
                      <input
                        type="number"
                        className="ai-input"
                        min="1"
                        value={form.max_tokens ?? ''}
                        onChange={(e) => updateProviderForm(p.key, 'max_tokens', e.target.value)}
                        disabled={!isImplemented}
                      />
                    </InputRow>
                  </div>

                  <InputRow label="Включён" inline>
                    <input
                      type="checkbox"
                      checked={!!form.is_enabled}
                      onChange={(e) => updateProviderForm(p.key, 'is_enabled', e.target.checked)}
                      disabled={!isImplemented}
                    />
                  </InputRow>

                  <div className="ai-actions-center">
                    <button
                      type="button"
                      className="ai-btn ai-btn--small"
                      onClick={() => saveProviderCard(p.key)}
                      disabled={!isImplemented || saving[`provider_${p.key}`]}
                    >
                      {saving[`provider_${p.key}`] ? 'Сохранение…' : 'Сохранить'}
                    </button>
                    <button
                      type="button"
                      className="ai-btn ai-btn--secondary ai-btn--small"
                      onClick={() => runProviderTest(p.key)}
                      disabled={!isImplemented || saving[`test_${p.key}`]}
                    >
                      {saving[`test_${p.key}`] ? 'Проверка…' : 'Проверить'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {testResult && (
            <pre className="ai-code-preview">{JSON.stringify(testResult, null, 2)}</pre>
          )}
        </Section>

        <Section title="Retrieval Settings" subtitle="Параметры поиска, чанкования и кэширования.">
          <div className="ai-retrieval-fields">
            <InputRow label="Top-K">
              <input
                type="number"
                className="ai-input"
                min="1"
                max="20"
                value={tuningForms.top_k ?? ''}
                onChange={(e) => updateTuningForm('top_k', Number(e.target.value))}
              />
            </InputRow>

            <InputRow label="Distance threshold">
              <input
                type="number"
                className="ai-input"
                step="0.05"
                min="0"
                max="10"
                value={tuningForms.rag_distance_threshold ?? ''}
                onChange={(e) => updateTuningForm('rag_distance_threshold', Number(e.target.value))}
              />
            </InputRow>

            <InputRow label="Chunk size">
              <input
                type="number"
                className="ai-input"
                min="128"
                max="8192"
                value={tuningForms.chunk_size ?? ''}
                onChange={(e) => updateTuningForm('chunk_size', Number(e.target.value))}
              />
            </InputRow>

            <InputRow label="Chunk overlap">
              <input
                type="number"
                className="ai-input"
                min="0"
                max="4096"
                value={tuningForms.chunk_overlap ?? ''}
                onChange={(e) => updateTuningForm('chunk_overlap', Number(e.target.value))}
              />
            </InputRow>

            <InputRow label="Cache enabled">
              <div className="ai-checkbox-cell">
                <input
                  type="checkbox"
                  checked={!!tuningForms.cache_enabled}
                  onChange={(e) => updateTuningForm('cache_enabled', e.target.checked)}
                />
              </div>
            </InputRow>

            <InputRow label="Cache TTL, сек">
              <input
                type="number"
                className="ai-input"
                min="30"
                max="86400"
                step="30"
                value={tuningForms.cache_ttl_seconds ?? ''}
                onChange={(e) => updateTuningForm('cache_ttl_seconds', Number(e.target.value))}
              />
            </InputRow>

            <InputRow label="Retrieval timeout, мс">
              <input
                type="number"
                className="ai-input"
                min="500"
                max="60000"
                step="100"
                value={tuningForms.retrieval_timeout_ms ?? ''}
                onChange={(e) => updateTuningForm('retrieval_timeout_ms', Number(e.target.value))}
              />
            </InputRow>

            <InputRow label="Embedding timeout, мс">
              <input
                type="number"
                className="ai-input"
                min="1000"
                max="300000"
                step="1000"
                value={tuningForms.embedding_timeout_ms ?? ''}
                onChange={(e) => updateTuningForm('embedding_timeout_ms', Number(e.target.value))}
              />
            </InputRow>

            {tuningForms.chunk_overlap >= tuningForms.chunk_size && (
              <p className="ai-field-error">Overlap должен быть меньше chunk size</p>
            )}
          </div>

          <div className="ai-actions-center">
            <button
              type="button"
              className="ai-btn ai-btn--small"
              onClick={() => saveTuningBlock(['top_k', 'rag_distance_threshold', 'chunk_size', 'chunk_overlap', 'cache_enabled', 'cache_ttl_seconds', 'retrieval_timeout_ms', 'embedding_timeout_ms'])}
              disabled={saving.tuning || tuningForms.chunk_overlap >= tuningForms.chunk_size}
            >
              {saving.tuning ? 'Сохранение…' : 'Сохранить'}
            </button>
          </div>
        </Section>
      </div>

      {/* Bottom row: Behavior + Instructions */}
      <div className="ai-config-bottom">
        <Section title="Поведение" subtitle="Промпт, правила ответа и история.">
          <div className="ai-behavior-grid">
            <div
              className="ai-text-preview ai-text-preview--tall"
              onClick={() => openTextModal('system_prompt')}
              role="button"
              tabIndex={0}
            >
              <label>Системный промпт</label>
              <div className="ai-text-preview__box">{config.system_prompt || ''}</div>
            </div>
            <div className="ai-behavior-col ai-behavior-col--right">
              <div
                className="ai-text-preview ai-text-preview--large"
                onClick={() => openTextModal('output_rules')}
                role="button"
                tabIndex={0}
              >
                <label>Правила ответа</label>
                <div className="ai-text-preview__box">{config.output_rules || ''}</div>
              </div>
              <div
                className="ai-text-preview ai-text-preview--short"
                onClick={() => openTextModal('refusal_answer_text')}
                role="button"
                tabIndex={0}
              >
                <label>Текст отказа</label>
                <div className="ai-text-preview__box">{config.refusal_answer_text || ''}</div>
              </div>
              <InputRow label="Max history messages">
                <input
                  type="number"
                  className="ai-input ai-input--inline"
                  min="0"
                  max="50"
                  value={config.max_history_messages ?? ''}
                  onChange={(e) => updateConfigField('max_history_messages', Number(e.target.value))}
                />
              </InputRow>
            </div>
          </div>
          <div className="ai-actions-center">
            <button
              type="button"
              className="ai-btn ai-btn--small"
              onClick={saveBehaviorGroup}
              disabled={saving.behavior}
            >
              {saving.behavior ? 'Сохранение…' : 'Сохранить'}
            </button>
          </div>
        </Section>

        <Section title="Инструкции" subtitle="Уровни подготовки и примеры.">
          <div className="ai-instructions-grid">
            <div className="ai-instructions-col">
              <div
                className="ai-text-preview ai-text-preview--half"
                onClick={() => openTextModal('beginner_instructions')}
                role="button"
                tabIndex={0}
              >
                <label>Инструкции для начинающих</label>
                <div className="ai-text-preview__box">{config.beginner_instructions || ''}</div>
              </div>
              <div
                className="ai-text-preview ai-text-preview--half"
                onClick={() => openTextModal('advanced_instructions')}
                role="button"
                tabIndex={0}
              >
                <label>Инструкции для продвинутых</label>
                <div className="ai-text-preview__box">{config.advanced_instructions || ''}</div>
              </div>
            </div>
            <div className="ai-instructions-col">
              <div
                className="ai-text-preview ai-text-preview--tall"
                onClick={() => openTextModal('few_shot_examples')}
                role="button"
                tabIndex={0}
              >
                <label>Few-shot примеры</label>
                <div className="ai-text-preview__box">{config.few_shot_examples || ''}</div>
              </div>
            </div>
          </div>
          <div className="ai-actions-center">
            <button
              type="button"
              className="ai-btn ai-btn--small"
              onClick={saveInstructionsGroup}
              disabled={saving.instructions}
            >
              {saving.instructions ? 'Сохранение…' : 'Сохранить'}
            </button>
          </div>
        </Section>
      </div>

      <TextModal
        isOpen={modal.open}
        title={modal.title}
        value={modal.value}
        onChange={(v) => setModal((prev) => ({ ...prev, value: v }))}
        onSave={saveTextField}
        onClose={closeModal}
        saving={saving[modal.field]}
      />
    </div>
  );
}

export default AiAndRetrievalConfig;
