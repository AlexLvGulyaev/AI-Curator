import { useEffect, useState } from 'react';
import { getOrchestratorConfig, updateOrchestratorConfig } from '../api/backend';

const DEFAULT_INTENTS = ['deadline', 'progress', 'study', 'mixed', 'organizational'];

const TOOLTIPS = {
  default_intent: 'Интент, который выбирается, если сообщение студента не подошло ни под одно правило.',
  keywords:
    'Каждая строка — фраза, по которой Orchestrator понимает, что вопрос относится к этому интенту.',
  priority:
    'Приоритет правила. Меньше число — выше приоритет. Применяется только к интентам, определённым через условия (conditions). Интенты deadline и progress определяются по keywords раньше и не участвуют в сравнении priority.',
  priority_deadline_progress:
    'Deadline и progress всегда определяются по keywords раньше условий (conditions), поэтому их priority не влияет на перехват организационных вопросов.',
  advanced_conditions:
    'Дополнительные условия: требовать наличие keywords другого типа, прежде чем применить это правило.',
  source_lms: 'Обращаться к Moodle LMS за курсами, дедлайнами, прогрессом.',
  source_rag: 'Искать релевантные фрагменты в Knowledge Base AI Curator.',
  source_strict_course:
    'Жёстко фильтровать RAG-поиск по course_id текущего курса. Если выключено — разрешены общие материалы из других курсов.',
  max_lms_contents:
    'Сколько элементов курса (уроков/модулей) передавать в prompt LLM из LMS. Не ограничивает детерминированные ответы deadline, progress и подсчёты "сколько".',
  max_lms_deadlines:
    'Сколько ближайших дедлайнов передавать в prompt LLM из LMS и показывать в коротком deadline-ответе.',
  intent_max_tokens_organizational:
    'Soft-лимит токенов для LLM на организационные вопросы. Модель постарается не превысить лимит, но не гарантирует заполнение до него.',
  intent_max_tokens_study_beginner:
    'Soft-лимит токенов для LLM на учебные вопросы в режиме beginner.',
  intent_max_tokens_mixed:
    'Soft-лимит токенов для LLM на смешанные вопросы.',
  intent_max_tokens_default:
    'Soft-лимит токенов для LLM на остальные сценарии.',
  fallback_no_lms_data: 'Текст ответа, когда в LMS нет запрошенных данных.',
  fallback_no_rag_context: 'Текст ответа, когда в Knowledge Base не найдено релевантных фрагментов.',
  fallback_out_of_scope_course:
    'Шаблон отказа, когда студент спрашивает про курс, к которому не имеет доступа. Используйте {course} для подстановки названия.',
  non_course_starters:
    'Слова, с которых обычно начинаются вопросы, но которые не являются названием курса. Помогают избежать ложного «курс не найден».',
};

function keywordsToText(keywords) {
  return Array.isArray(keywords) ? keywords.join('\n') : '';
}

function textToKeywords(text) {
  return text
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
}

function ensureIntentRulesShape(rules) {
  const next = {};
  for (const intent of DEFAULT_INTENTS) {
    const rule = rules?.[intent] || {};
    next[intent] = {
      keywords: Array.isArray(rule.keywords) ? rule.keywords : [],
      priority: typeof rule.priority === 'number' ? rule.priority : 99,
      conditions: Array.isArray(rule.conditions) ? rule.conditions : [],
    };
  }
  return next;
}

function ensureSourceMapShape(map) {
  const next = {};
  for (const intent of DEFAULT_INTENTS) {
    const src = map?.[intent] || {};
    next[intent] = {
      lms: Boolean(src.lms),
      rag: Boolean(src.rag),
      strict_course: Boolean(src.strict_course),
    };
  }
  return next;
}

function parseConditions(conditions) {
  const flat = [];
  for (const cond of conditions || []) {
    if (cond && Array.isArray(cond.and)) {
      for (const part of cond.and) flat.push(part);
    } else if (Array.isArray(cond)) {
      flat.push(cond);
    }
  }
  return flat;
}

function buildConditions({ requireOrg, requireStudy, requireProgress }) {
  const predicates = [];
  if (requireOrg) predicates.push(['is_org']);
  if (requireStudy) predicates.push(['is_study']);
  if (requireProgress) predicates.push(['is_progress']);
  if (predicates.length === 0) return [];
  if (predicates.length === 1) return [predicates[0]];
  return [{ and: predicates }];
}

function Tooltip({ children, text }) {
  return (
    <span className="ai-tooltip">
      {children}
      <span className="ai-tooltip__text">{text}</span>
    </span>
  );
}

function validateNumber(value, { min, max, integer }) {
  if (value === '' || value === null || value === undefined) return 'Введите число';
  const num = Number(value);
  if (Number.isNaN(num)) return 'Введите число';
  if (integer && !Number.isInteger(num)) return 'Целое число';
  if (min !== undefined && num < min) return `Минимум ${min}`;
  if (max !== undefined && num > max) return `Максимум ${max}`;
  return null;
}

function IntentRuleEditor({ intent, rule, source, onChange }) {
  const [keywordsText, setKeywordsText] = useState(keywordsToText(rule.keywords));
  const [priority, setPriority] = useState(rule.priority);
  const [showAdvanced, setShowAdvanced] = useState((rule.conditions || []).length > 0);

  const predicates = parseConditions(rule.conditions);
  const requireOrg = predicates.some((p) => p[0] === 'is_org');
  const requireStudy = predicates.some((p) => p[0] === 'is_study');
  const requireProgress = predicates.some((p) => p[0] === 'is_progress');

  useEffect(() => {
    onChange({
      keywords: textToKeywords(keywordsText),
      priority,
      conditions: rule.conditions || [],
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keywordsText, priority]);

  function updateConditions(patch) {
    const next = buildConditions({
      requireOrg: patch.requireOrg ?? requireOrg,
      requireStudy: patch.requireStudy ?? requireStudy,
      requireProgress: patch.requireProgress ?? requireProgress,
    });
    onChange({
      keywords: textToKeywords(keywordsText),
      priority,
      conditions: next,
    });
  }

  const priorityError = validateNumber(priority, { min: 1, max: 100, integer: true });

  return (
    <div className="ai-provider-card" style={{ padding: '8px 10px', gap: '6px' }}>
      <div className="ai-provider-card__header" style={{ marginBottom: '2px' }}>
        <strong style={{ fontSize: '0.875rem' }}>{intent}</strong>
        <span className="ai-status ai-status--muted" style={{ fontSize: '0.65rem' }}>
          LMS {source.lms ? '✓' : '—'} · RAG {source.rag ? '✓' : '—'} · strict {source.strict_course ? '✓' : '—'}
        </span>
      </div>

      <Tooltip text={TOOLTIPS.keywords}>
        <textarea
          className="ai-textarea ai-textarea--small"
          rows={2}
          style={{ minHeight: '54px', padding: '5px 8px', fontSize: '0.875rem' }}
          value={keywordsText}
          placeholder="keywords, одна фраза на строку"
          onChange={(e) => setKeywordsText(e.target.value)}
        />
      </Tooltip>

      <div className="ai-field-row ai-field-row--inline" style={{ justifyContent: 'space-between', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Tooltip text={intent === 'deadline' || intent === 'progress' ? TOOLTIPS.priority_deadline_progress : TOOLTIPS.priority}>
            <label className="ai-field-label" style={{ margin: 0 }}>
              Priority
            </label>
          </Tooltip>
          <input
            type="number"
            className={`ai-input ai-input--inline ${priorityError ? 'ai-input--error' : ''}`}
            style={{ width: '48px', height: '26px', padding: '2px 4px' }}
            value={priority}
            min={1}
            max={100}
            onChange={(e) => setPriority(Number(e.target.value))}
          />
          {priorityError && <span className="ai-field-error-inline">{priorityError}</span>}
        </div>
        <Tooltip text={TOOLTIPS.advanced_conditions}>
          <button
            type="button"
            className="ai-btn ai-btn--secondary ai-btn--tiny"
            onClick={() => setShowAdvanced((s) => !s)}
          >
            {showAdvanced ? '▾ Дополнительно' : '▸ Дополнительно'}
          </button>
        </Tooltip>
      </div>

      {showAdvanced && (
        <div className="ai-provider-card" style={{ backgroundColor: 'rgba(0,0,0,0.15)', padding: '8px', gap: '6px', marginTop: '2px' }}>
          <label className="ai-field-label" style={{ fontSize: '0.6875rem', margin: 0 }}>
            Требовать наличие
          </label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label className="ai-field-row ai-field-row--inline" style={{ gap: '6px', fontSize: '0.8125rem', margin: 0 }}>
              <input
                type="checkbox"
                checked={requireOrg}
                onChange={(e) => updateConditions({ requireOrg: e.target.checked })}
              />
              <span>организационных keywords</span>
            </label>
            <label className="ai-field-row ai-field-row--inline" style={{ gap: '6px', fontSize: '0.8125rem', margin: 0 }}>
              <input
                type="checkbox"
                checked={requireStudy}
                onChange={(e) => updateConditions({ requireStudy: e.target.checked })}
              />
              <span>учебных keywords</span>
            </label>
            <label className="ai-field-row ai-field-row--inline" style={{ gap: '6px', fontSize: '0.8125rem', margin: 0 }}>
              <input
                type="checkbox"
                checked={requireProgress}
                onChange={(e) => updateConditions({ requireProgress: e.target.checked })}
              />
              <span>keywords прогресса</span>
            </label>
          </div>
        </div>
      )}
    </div>
  );
}

function NumberField({ label, value, min = 1, max = 4096, onChange, tooltip }) {
  const error = validateNumber(value, { min, max, integer: true });
  return (
    <div className="ai-field-row ai-field-row--inline" style={{ gap: '8px', justifyContent: 'space-between' }}>
      <Tooltip text={tooltip}>
        <label className="ai-field-label" style={{ flex: 1 }}>
          {label}
        </label>
      </Tooltip>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <input
          type="number"
          className={`ai-input ai-input--inline ${error ? 'ai-input--error' : ''}`}
          style={{ width: '64px', height: '26px', padding: '2px 4px', textAlign: 'right' }}
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
        />
        {error && <span className="ai-field-error-inline">{error}</span>}
      </div>
    </div>
  );
}

function OrchestratorConfig() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [saving, setSaving] = useState(false);

  const [intentRules, setIntentRules] = useState({});
  const [sourceMap, setSourceMap] = useState({});
  const [defaultIntent, setDefaultIntent] = useState('study');
  const [maxLmsContents, setMaxLmsContents] = useState(12);
  const [maxLmsDeadlines, setMaxLmsDeadlines] = useState(5);
  const [intentMaxTokens, setIntentMaxTokens] = useState({});
  const [fallbackMessages, setFallbackMessages] = useState({});
  const [nonCourseStarters, setNonCourseStarters] = useState('');

  async function load() {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const cfg = await getOrchestratorConfig();
      setConfig(cfg);
      setIntentRules(ensureIntentRulesShape(cfg.intent_rules));
      setSourceMap(ensureSourceMapShape(cfg.intent_source_map));
      setDefaultIntent(cfg.default_intent || 'study');
      setMaxLmsContents(cfg.max_lms_contents ?? 12);
      setMaxLmsDeadlines(cfg.max_lms_deadlines ?? 5);
      setIntentMaxTokens({
        organizational: cfg.intent_max_tokens?.organizational ?? 500,
        study_beginner: cfg.intent_max_tokens?.study_beginner ?? 650,
        mixed: cfg.intent_max_tokens?.mixed ?? 800,
        default: cfg.intent_max_tokens?.default ?? 750,
      });
      setFallbackMessages({
        no_lms_data: cfg.fallback_messages?.no_lms_data ?? '',
        no_rag_context: cfg.fallback_messages?.no_rag_context ?? '',
        out_of_scope_course: cfg.fallback_messages?.out_of_scope_course ?? '',
      });
      setNonCourseStarters(keywordsToText(cfg.non_course_starters));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function hasErrors() {
    const priorityErrors = DEFAULT_INTENTS.some(
      (intent) =>
        validateNumber(intentRules[intent]?.priority, { min: 1, max: 100, integer: true }) !== null
    );
    const limitErrors =
      validateNumber(maxLmsContents, { min: 1, max: 100, integer: true }) !== null ||
      validateNumber(maxLmsDeadlines, { min: 1, max: 50, integer: true }) !== null;
    const tokenErrors =
      validateNumber(intentMaxTokens.organizational, { min: 1, max: 4096, integer: true }) !== null ||
      validateNumber(intentMaxTokens.study_beginner, { min: 1, max: 4096, integer: true }) !== null ||
      validateNumber(intentMaxTokens.mixed, { min: 1, max: 4096, integer: true }) !== null ||
      validateNumber(intentMaxTokens.default, { min: 1, max: 4096, integer: true }) !== null;
    return priorityErrors || limitErrors || tokenErrors;
  }

  async function save() {
    if (hasErrors()) {
      setError('Исправьте ошибки в форме перед сохранением');
      return;
    }
    const payload = {
      intent_rules: intentRules,
      default_intent: defaultIntent,
      intent_source_map: sourceMap,
      non_course_starters: textToKeywords(nonCourseStarters),
      max_lms_contents: maxLmsContents,
      max_lms_deadlines: maxLmsDeadlines,
      intent_max_tokens: intentMaxTokens,
      fallback_messages: fallbackMessages,
    };

    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await updateOrchestratorConfig(payload);
      setConfig(updated);
      setIntentRules(ensureIntentRulesShape(updated.intent_rules));
      setSourceMap(ensureSourceMapShape(updated.intent_source_map));
      setMessage('Конфигурация сохранена');
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="ai-loading flex items-center gap-2">
        <span className="inline-block animate-pulse">●</span>
        Загрузка конфигурации…
      </div>
    );
  }

  return (
    <div className="ai-config-page">
      <div className="ai-page__header">
        <div>
          <h1 className="ai-page__title">Оркестратор</h1>
          <p className="ai-page__subtitle">Классификация запросов, источники данных, лимиты и fallback.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={load} className="ai-btn ai-btn--small ai-btn--secondary" type="button" disabled={saving}>
            Обновить
          </button>
          <button type="button" className="ai-btn ai-btn--small" onClick={save} disabled={saving || hasErrors()}>
            {saving ? 'Сохранение…' : 'Сохранить'}
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

      <div className="ai-config-top" style={{ gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        <div className="ai-card ai-section" style={{ minHeight: 0, padding: '10px 12px' }}>
          <div
            className="ai-section__title"
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}
          >
            <span>Классификация интентов</span>
            <div className="ai-field-row ai-field-row--inline" style={{ gap: '4px' }}>
              <Tooltip text={TOOLTIPS.default_intent}>
                <label className="ai-field-label" style={{ margin: 0 }}>
                  Default
                </label>
              </Tooltip>
              <select
                className="ai-select"
                style={{ width: '110px', height: '24px', padding: '1px 4px', fontSize: '0.75rem' }}
                value={defaultIntent}
                onChange={(e) => setDefaultIntent(e.target.value)}
              >
                {DEFAULT_INTENTS.map((i) => (
                  <option key={i} value={i}>
                    {i}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div
            className="ai-provider-cards"
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gridTemplateRows: 'repeat(3, minmax(0, 1fr))',
              gap: '8px',
              overflow: 'auto',
            }}
          >
            {DEFAULT_INTENTS.map((intent) => (
              <IntentRuleEditor
                key={intent}
                intent={intent}
                rule={intentRules[intent] || { keywords: [], priority: 99, conditions: [] }}
                source={sourceMap[intent] || { lms: false, rag: false, strict_course: false }}
                onChange={(rule) => setIntentRules({ ...intentRules, [intent]: rule })}
              />
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minHeight: 0 }}>
          <div className="ai-config-top" style={{ gridTemplateColumns: '1fr 1fr', flex: '0 0 auto', gap: '8px' }}>
            <div className="ai-card ai-section" style={{ minHeight: '160px', padding: '10px 12px' }}>
              <h2 className="ai-section__title" style={{ marginBottom: '8px' }}>Маршрутизация источников</h2>
              <table className="ai-table" style={{ fontSize: '0.875rem' }}>
                <thead>
                  <tr>
                    <th>Intent</th>
                    <th style={{ textAlign: 'center' }}>
                      <Tooltip text={TOOLTIPS.source_lms}>LMS</Tooltip>
                    </th>
                    <th style={{ textAlign: 'center' }}>
                      <Tooltip text={TOOLTIPS.source_rag}>RAG</Tooltip>
                    </th>
                    <th style={{ textAlign: 'center' }}>
                      <Tooltip text={TOOLTIPS.source_strict_course}>Strict</Tooltip>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {DEFAULT_INTENTS.map((intent) => (
                    <tr key={intent}>
                      <td>{intent}</td>
                      <td style={{ textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={sourceMap[intent]?.lms || false}
                          onChange={(e) =>
                            setSourceMap({
                              ...sourceMap,
                              [intent]: { ...sourceMap[intent], lms: e.target.checked },
                            })
                          }
                        />
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={sourceMap[intent]?.rag || false}
                          onChange={(e) =>
                            setSourceMap({
                              ...sourceMap,
                              [intent]: { ...sourceMap[intent], rag: e.target.checked },
                            })
                          }
                        />
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={sourceMap[intent]?.strict_course || false}
                          onChange={(e) =>
                            setSourceMap({
                              ...sourceMap,
                              [intent]: { ...sourceMap[intent], strict_course: e.target.checked },
                            })
                          }
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="ai-card ai-section" style={{ minHeight: '160px', padding: '10px 12px' }}>
              <h2 className="ai-section__title" style={{ marginBottom: '8px' }}>Лимиты и токен-бюджеты</h2>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 12px' }}>
                <NumberField
                  label="Max contents"
                  value={maxLmsContents}
                  max={100}
                  onChange={setMaxLmsContents}
                  tooltip={TOOLTIPS.max_lms_contents}
                />
                <NumberField
                  label="Max deadlines"
                  value={maxLmsDeadlines}
                  max={50}
                  onChange={setMaxLmsDeadlines}
                  tooltip={TOOLTIPS.max_lms_deadlines}
                />
                <NumberField
                  label="Organizational"
                  value={intentMaxTokens.organizational}
                  onChange={(v) => setIntentMaxTokens({ ...intentMaxTokens, organizational: v })}
                  tooltip={TOOLTIPS.intent_max_tokens_organizational}
                />
                <NumberField
                  label="Study beginner"
                  value={intentMaxTokens.study_beginner}
                  onChange={(v) => setIntentMaxTokens({ ...intentMaxTokens, study_beginner: v })}
                  tooltip={TOOLTIPS.intent_max_tokens_study_beginner}
                />
                <NumberField
                  label="Mixed"
                  value={intentMaxTokens.mixed}
                  onChange={(v) => setIntentMaxTokens({ ...intentMaxTokens, mixed: v })}
                  tooltip={TOOLTIPS.intent_max_tokens_mixed}
                />
                <NumberField
                  label="Default"
                  value={intentMaxTokens.default}
                  onChange={(v) => setIntentMaxTokens({ ...intentMaxTokens, default: v })}
                  tooltip={TOOLTIPS.intent_max_tokens_default}
                />
              </div>
            </div>
          </div>

          <div className="ai-card ai-section" style={{ flex: '1 1 auto', minHeight: 0, padding: '10px 12px' }}>
            <h2 className="ai-section__title" style={{ marginBottom: '8px' }}>Fallback-ответы и фильтры курсов</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minHeight: 0 }}>
              <Tooltip text={TOOLTIPS.fallback_no_lms_data}>
                <label className="ai-field-label" style={{ margin: 0 }}>No LMS data</label>
              </Tooltip>
              <textarea
                className="ai-textarea ai-textarea--small"
                rows={2}
                style={{ minHeight: '44px', padding: '5px 8px', fontSize: '0.875rem' }}
                value={fallbackMessages.no_lms_data}
                onChange={(e) => setFallbackMessages({ ...fallbackMessages, no_lms_data: e.target.value })}
              />
              <Tooltip text={TOOLTIPS.fallback_no_rag_context}>
                <label className="ai-field-label" style={{ margin: 0 }}>No RAG context</label>
              </Tooltip>
              <textarea
                className="ai-textarea ai-textarea--small"
                rows={2}
                style={{ minHeight: '44px', padding: '5px 8px', fontSize: '0.875rem' }}
                value={fallbackMessages.no_rag_context}
                onChange={(e) => setFallbackMessages({ ...fallbackMessages, no_rag_context: e.target.value })}
              />
              <Tooltip text={TOOLTIPS.fallback_out_of_scope_course}>
                <label className="ai-field-label" style={{ margin: 0 }}>
                  Out of scope (placeholder: {'{course}'})
                </label>
              </Tooltip>
              <textarea
                className="ai-textarea ai-textarea--small"
                rows={2}
                style={{ minHeight: '44px', padding: '5px 8px', fontSize: '0.875rem' }}
                value={fallbackMessages.out_of_scope_course}
                onChange={(e) =>
                  setFallbackMessages({ ...fallbackMessages, out_of_scope_course: e.target.value })
                }
              />
              <Tooltip text={TOOLTIPS.non_course_starters}>
                <label className="ai-field-label" style={{ margin: '4px 0 0' }}>Non-course starters</label>
              </Tooltip>
              <textarea
                className="ai-textarea"
                rows={6}
                style={{ flex: '1 1 auto', minHeight: '100px', padding: '5px 8px', fontSize: '0.875rem' }}
                value={nonCourseStarters}
                placeholder="одно слово на строку"
                onChange={(e) => setNonCourseStarters(e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default OrchestratorConfig;
