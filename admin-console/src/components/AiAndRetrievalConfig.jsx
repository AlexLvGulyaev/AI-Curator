import { useEffect, useMemo, useState } from 'react';
import {
  getActiveAiConfig,
  updateActiveAiConfig,
  getRetrievalTuning,
  updateRetrievalTuning,
  getLlmProviders,
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
  const labelMap = {
    ACTIVE: 'АКТИВНЫЙ',
    FALLBACK: 'РЕЗЕРВ',
    READY: 'ГОТОВ',
    'NOT READY': 'НЕ ГОТОВ',
  };
  return <span className={`ai-status ${map[variant] || 'ai-status--muted'}`}>{labelMap[label] || label}</span>;
}

function InputRow({ label, children, inline = false, error }) {
  return (
    <div className={inline ? 'ai-field-row ai-field-row--inline' : 'ai-field-row'}>
      <label className="ai-field-label">{label}</label>
      {children}
      {error && <span className="ai-field-error-inline">{error}</span>}
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

function validateNumber(value, { min, max, step, integer }) {
  if (value === '' || value === null || value === undefined) return null;
  const num = Number(value);
  if (Number.isNaN(num)) return 'Введите число';
  if (integer && !Number.isInteger(num)) return 'Целое число';
  if (min !== undefined && num < min) return `Минимум ${min}`;
  if (max !== undefined && num > max) return `Максимум ${max}`;
  if (step !== undefined && step > 0) {
    const scaled = Math.round((num - (min ?? 0)) / step);
    const expected = scaled * step + (min ?? 0);
    if (Math.abs(num - expected) > 1e-9) return `Шаг ${step}`;
  }
  return null;
}

function AiAndRetrievalConfig() {
  const [config, setConfig] = useState(null);
  const [tuning, setTuning] = useState(null);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const [modal, setModal] = useState({ open: false, field: '', title: '', value: '' });

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
      const mergedProviders = provs.reduce((acc, p) => {
        const settings = cfg.provider_settings?.[p.key] || {};
        acc[p.key] = {
          ...p,
          model: settings.model ?? p.model,
          temperature: settings.temperature ?? p.temperature,
          max_tokens: settings.max_tokens ?? p.max_tokens,
        };
        return acc;
      }, {});
      setProviderForms(mergedProviders);
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
    const trimmed = modal.value.trim();
    if (!trimmed) {
      setError('Системный промпт не может быть пустым');
      return;
    }
    try {
      const updated = await updateActiveAiConfig({ ...config, [modal.field]: modal.value });
      setConfig(updated);
      closeModal();
    } catch (err) {
      setError(err.message);
    }
  }

  const tuningErrors = useMemo(() => {
    if (!tuningForms) return {};
    return {
      top_k: validateNumber(tuningForms.top_k, { min: 1, max: 20, integer: true }),
      rag_distance_threshold: validateNumber(tuningForms.rag_distance_threshold, { min: 0, max: 10, step: 0.05 }),
      chunk_size: validateNumber(tuningForms.chunk_size, { min: 128, max: 8192, integer: true }),
      chunk_overlap: validateNumber(tuningForms.chunk_overlap, { min: 0, max: 4096, integer: true }),
      cache_ttl_seconds: validateNumber(tuningForms.cache_ttl_seconds, { min: 30, max: 86400, step: 30, integer: true }),
      retrieval_timeout_ms: validateNumber(tuningForms.retrieval_timeout_ms, { min: 500, max: 60000, step: 100, integer: true }),
      embedding_timeout_ms: validateNumber(tuningForms.embedding_timeout_ms, { min: 1000, max: 300000, step: 1000, integer: true }),
      course_boost_factor: validateNumber(tuningForms.course_boost_factor, { min: 0, max: 1, step: 0.05 }),
    };
  }, [tuningForms]);

  const hasTuningErrors = useMemo(() => {
    if (tuningForms.chunk_overlap >= tuningForms.chunk_size) return true;
    return Object.values(tuningErrors).some(Boolean);
  }, [tuningErrors, tuningForms]);

  const configErrors = useMemo(() => {
    if (!config) return {};
    return {
      system_prompt: !config.system_prompt || !config.system_prompt.trim() ? 'Системный промпт обязателен' : null,
      max_history_messages: validateNumber(config.max_history_messages, { min: 0, max: 50, integer: true }),
    };
  }, [config]);

  const hasConfigErrors = useMemo(() => Object.values(configErrors).some(Boolean), [configErrors]);

  async function saveAll() {
    if (!config || !tuning) return;
    if (hasConfigErrors || hasTuningErrors) {
      setError('Исправьте ошибки в форме перед сохранением');
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const [updatedConfig, updatedTuning] = await Promise.all([
        updateActiveAiConfig({
          ...config,
          system_prompt: config.system_prompt,
          output_rules: config.output_rules,
          refusal_answer_text: config.refusal_answer_text,
          beginner_instructions: config.beginner_instructions,
          advanced_instructions: config.advanced_instructions,
          few_shot_examples: config.few_shot_examples,
          max_history_messages: config.max_history_messages,
          active_provider: config.active_provider,
          fallback_provider: config.fallback_provider,
          openai_enabled: config.openai_enabled,
          gigachat_enabled: config.gigachat_enabled,
          provider_settings: {
            openai: {
              model: providerForms.openai?.model,
              temperature: Number(providerForms.openai?.temperature),
              max_tokens: Number(providerForms.openai?.max_tokens),
            },
            gigachat: {
              model: providerForms.gigachat?.model,
              temperature: Number(providerForms.gigachat?.temperature),
              max_tokens: Number(providerForms.gigachat?.max_tokens),
            },
          },
        }),
        updateRetrievalTuning({
          top_k: tuningForms.top_k,
          rag_distance_threshold: tuningForms.rag_distance_threshold,
          chunk_size: tuningForms.chunk_size,
          chunk_overlap: tuningForms.chunk_overlap,
          cache_enabled: tuningForms.cache_enabled,
          cache_ttl_seconds: tuningForms.cache_ttl_seconds,
          retrieval_timeout_ms: tuningForms.retrieval_timeout_ms,
          embedding_timeout_ms: tuningForms.embedding_timeout_ms,
          course_boost_enabled: tuningForms.course_boost_enabled,
          course_boost_factor: tuningForms.course_boost_factor,
        }),
      ]);
      setConfig(updatedConfig);
      setTuning(updatedTuning);
      setTuningForms({ ...updatedTuning });
      // Refresh provider states from backend after config change.
      const provs = await getLlmProviders();
      setProviders(provs);
      const mergedProviders = provs.reduce((acc, p) => {
        const settings = updatedConfig.provider_settings?.[p.key] || {};
        acc[p.key] = {
          ...p,
          model: settings.model ?? p.model,
          temperature: settings.temperature ?? p.temperature,
          max_tokens: settings.max_tokens ?? p.max_tokens,
        };
        return acc;
      }, {});
      setProviderForms(mergedProviders);
      setMessage('Настройки сохранены');
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function runProviderTest(key) {
    setSaving(true);
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
      setSaving(false);
    }
  }

  function updateConfigField(field, value) {
    setConfig((prev) => {
      if (!prev) return prev;
      const next = { ...prev, [field]: value };
      // If active/fallback providers conflict or active becomes disabled, reconcile.
      if (field === 'active_provider' && next.fallback_provider === value) {
        next.fallback_provider = value === 'openai' ? 'gigachat' : 'openai';
      }
      if (field === 'fallback_provider' && next.active_provider === value) {
        next.fallback_provider = next.active_provider === 'openai' ? 'gigachat' : 'openai';
      }
      if (field === 'openai_enabled' && !value && next.active_provider === 'openai') {
        next.active_provider = 'gigachat';
      }
      if (field === 'gigachat_enabled' && !value && next.active_provider === 'gigachat') {
        next.active_provider = 'openai';
      }
      return next;
    });
  }

  function updateProviderForm(key, field, value) {
    setProviderForms((prev) => ({
      ...prev,
      [key]: { ...prev[key], [field]: value },
    }));
  }

  function updateTuningForm(field, rawValue) {
    let value = rawValue;
    if (typeof rawValue === 'string') {
      const num = Number(rawValue);
      value = rawValue === '' ? '' : Number.isNaN(num) ? rawValue : num;
    }
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
          <h1 className="ai-page__title">AI и Retrieval</h1>
          <p className="ai-page__subtitle">Настройки LLM-провайдеров, поведения модели и параметров поиска.</p>
        </div>
        <div className="ai-page__actions">
          <button
            type="button"
            className="ai-btn"
            onClick={saveAll}
            disabled={saving || hasConfigErrors || hasTuningErrors}
          >
            {saving ? 'Сохранение…' : 'Сохранить'}
          </button>
          <button onClick={load} className="ai-btn ai-btn--small ai-btn--secondary" type="button" disabled={saving}>
            Обновить
          </button>
        </div>
      </div>

      {error && <div className="ai-error">{error}</div>}
      {message && (
        <div className="ai-toast ai-toast--success ai-toast--floating">
          {message}
          <button
            type="button"
            className="ai-toast__close"
            onClick={() => setMessage(null)}
            aria-label="Закрыть"
          >
            ×
          </button>
        </div>
      )}

      {/* Top row: LLM providers + Retrieval */}
      <div className="ai-config-top">
        <Section title="LLM-провайдеры и активность" subtitle="Активный / fallback провайдер и карточки.">
          <div className="ai-provider-controls">
            <div className="ai-provider-selects">
              <InputRow label="Активный провайдер">
                <select
                  value={config.active_provider || 'openai'}
                  onChange={(e) => updateConfigField('active_provider', e.target.value)}
                  className="ai-select"
                >
                  <option value="openai" disabled={!config.openai_enabled}>OpenAI</option>
                  <option value="gigachat" disabled={!config.gigachat_enabled}>GigaChat</option>
                </select>
              </InputRow>
              <InputRow label="Fallback провайдер">
                <select
                  value={config.fallback_provider || 'gigachat'}
                  onChange={(e) => updateConfigField('fallback_provider', e.target.value)}
                  className="ai-select"
                >
                  <option value="gigachat" disabled={!config.gigachat_enabled}>GigaChat</option>
                  <option value="openai" disabled={!config.openai_enabled}>OpenAI</option>
                </select>
              </InputRow>
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
                      checked={p.key === 'openai' ? !!config.openai_enabled : !!config.gigachat_enabled}
                      onChange={(e) => updateConfigField(
                        p.key === 'openai' ? 'openai_enabled' : 'gigachat_enabled',
                        e.target.checked,
                      )}
                      disabled={!isImplemented}
                    />
                  </InputRow>

                  <div className="ai-actions-center">
                    <button
                      type="button"
                      className="ai-btn ai-btn--secondary ai-btn--small"
                      onClick={() => runProviderTest(p.key)}
                      disabled={!isImplemented || saving}
                    >
                      {saving ? 'Проверка…' : 'Проверить'}
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

        <Section title="Параметры поиска" subtitle="Параметры поиска, чанкования и кэширования.">
          <div className="ai-retrieval-fields">
            <InputRow label="Top-K" error={tuningErrors.top_k}>
              <input
                type="number"
                className={`ai-input ${tuningErrors.top_k ? 'ai-input--error' : ''}`}
                min="1"
                max="20"
                value={tuningForms.top_k ?? ''}
                onChange={(e) => updateTuningForm('top_k', e.target.value)}
              />
            </InputRow>

            <InputRow label="Distance threshold" error={tuningErrors.rag_distance_threshold}>
              <input
                type="number"
                className={`ai-input ${tuningErrors.rag_distance_threshold ? 'ai-input--error' : ''}`}
                step="0.05"
                min="0"
                max="10"
                value={tuningForms.rag_distance_threshold ?? ''}
                onChange={(e) => updateTuningForm('rag_distance_threshold', e.target.value)}
              />
            </InputRow>

            <InputRow label="Chunk size" error={tuningErrors.chunk_size}>
              <input
                type="number"
                className={`ai-input ${tuningErrors.chunk_size ? 'ai-input--error' : ''}`}
                min="128"
                max="8192"
                value={tuningForms.chunk_size ?? ''}
                onChange={(e) => updateTuningForm('chunk_size', e.target.value)}
              />
            </InputRow>

            <InputRow label="Chunk overlap" error={tuningErrors.chunk_overlap}>
              <input
                type="number"
                className={`ai-input ${tuningErrors.chunk_overlap ? 'ai-input--error' : ''}`}
                min="0"
                max="4096"
                value={tuningForms.chunk_overlap ?? ''}
                onChange={(e) => updateTuningForm('chunk_overlap', e.target.value)}
              />
            </InputRow>

            {tuningForms.chunk_overlap >= tuningForms.chunk_size && (
              <p className="ai-field-error">Overlap должен быть меньше chunk size</p>
            )}

            <InputRow label="Cache enabled" inline>
              <div className="ai-checkbox-cell">
                <input
                  type="checkbox"
                  checked={!!tuningForms.cache_enabled}
                  onChange={(e) => updateTuningForm('cache_enabled', e.target.checked)}
                />
              </div>
            </InputRow>

            <InputRow label="Cache TTL, сек" error={tuningErrors.cache_ttl_seconds}>
              <input
                type="number"
                className={`ai-input ${tuningErrors.cache_ttl_seconds ? 'ai-input--error' : ''}`}
                min="30"
                max="86400"
                step="30"
                value={tuningForms.cache_ttl_seconds ?? ''}
                onChange={(e) => updateTuningForm('cache_ttl_seconds', e.target.value)}
              />
            </InputRow>

            <InputRow label="Retrieval timeout, мс" error={tuningErrors.retrieval_timeout_ms}>
              <input
                type="number"
                className={`ai-input ${tuningErrors.retrieval_timeout_ms ? 'ai-input--error' : ''}`}
                min="500"
                max="60000"
                step="100"
                value={tuningForms.retrieval_timeout_ms ?? ''}
                onChange={(e) => updateTuningForm('retrieval_timeout_ms', e.target.value)}
              />
            </InputRow>

            <InputRow label="Embedding timeout, мс" error={tuningErrors.embedding_timeout_ms}>
              <input
                type="number"
                className={`ai-input ${tuningErrors.embedding_timeout_ms ? 'ai-input--error' : ''}`}
                min="1000"
                max="300000"
                step="1000"
                value={tuningForms.embedding_timeout_ms ?? ''}
                onChange={(e) => updateTuningForm('embedding_timeout_ms', e.target.value)}
              />
            </InputRow>

            <InputRow label="Course boost" inline>
              <div className="ai-checkbox-cell">
                <input
                  type="checkbox"
                  checked={!!tuningForms.course_boost_enabled}
                  onChange={(e) => updateTuningForm('course_boost_enabled', e.target.checked)}
                />
              </div>
            </InputRow>

            <InputRow label="Course boost factor" error={tuningErrors.course_boost_factor}>
              <input
                type="number"
                className={`ai-input ${tuningErrors.course_boost_factor ? 'ai-input--error' : ''}`}
                min="0"
                max="1"
                step="0.05"
                value={tuningForms.course_boost_factor ?? ''}
                onChange={(e) => updateTuningForm('course_boost_factor', e.target.value)}
              />
            </InputRow>
          </div>
        </Section>
      </div>

      {/* Bottom row: Behavior + Instructions */}
      <div className="ai-config-bottom">
        <Section title="Поведение" subtitle="Промпт, правила ответа и история.">
          <div className="ai-behavior-grid">
            <div
              className={`ai-text-preview ai-text-preview--tall ${configErrors.system_prompt ? 'ai-text-preview--error' : ''}`}
              onClick={() => openTextModal('system_prompt')}
              role="button"
              tabIndex={0}
            >
              <label>Системный промпт {configErrors.system_prompt && <span className="ai-field-error-inline">({configErrors.system_prompt})</span>}</label>
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
              <InputRow label="Max history messages" error={configErrors.max_history_messages}>
                <input
                  type="number"
                  className={`ai-input ai-input--inline ${configErrors.max_history_messages ? 'ai-input--error' : ''}`}
                  min="0"
                  max="50"
                  value={config.max_history_messages ?? ''}
                  onChange={(e) => updateConfigField('max_history_messages', Number(e.target.value))}
                />
              </InputRow>
            </div>
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
        </Section>
      </div>

      <TextModal
        isOpen={modal.open}
        title={modal.title}
        value={modal.value}
        onChange={(v) => setModal((prev) => ({ ...prev, value: v }))}
        onSave={saveTextField}
        onClose={closeModal}
        saving={saving}
      />
    </div>
  );
}

export default AiAndRetrievalConfig;
