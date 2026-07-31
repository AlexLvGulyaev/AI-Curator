import { useEffect, useState } from 'react';
import { getOrchestratorConfig, updateOrchestratorConfig } from '../api/backend';

const DEFAULT_INTENTS = ['deadline', 'progress', 'study', 'mixed', 'organizational'];

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

function InputRow({ label, children, inline = false }) {
  return (
    <div className={inline ? 'ai-field-row ai-field-row--inline' : 'ai-field-row'}>
      <label className="ai-field-label">{label}</label>
      {children}
    </div>
  );
}

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

function ConditionBuilder({ condition, onChange, onRemove, ruleKeywords }) {
  if (!Array.isArray(condition) && !condition?.and) {
    return null;
  }

  if (condition?.and) {
    return (
      <div className="ai-condition ai-condition--and">
        <div className="ai-condition__header">
          <span className="ai-condition__label">И (все условия)</span>
          <button type="button" className="ai-btn ai-btn--secondary ai-btn--tiny" onClick={onRemove}>
            Удалить
          </button>
        </div>
        {condition.and.map((sub, idx) => (
          <ConditionBuilder
            key={idx}
            condition={sub}
            ruleKeywords={ruleKeywords}
            onChange={(next) => {
              const updated = { ...condition, and: [...condition.and] };
              updated.and[idx] = next;
              onChange(updated);
            }}
            onRemove={() => {
              const updated = { ...condition, and: condition.and.filter((_, i) => i !== idx) };
              onChange(updated);
            }}
          />
        ))}
        <div className="ai-condition__actions">
          <button
            type="button"
            className="ai-btn ai-btn--tiny"
            onClick={() => onChange({ ...condition, and: [...condition.and, ['is_org']] })}
          >
            + is_*
          </button>
          <button
            type="button"
            className="ai-btn ai-btn--tiny"
            onClick={() => onChange({ ...condition, and: [...condition.and, ['has_keyword', [...ruleKeywords]]] })}
          >
            + has_keyword
          </button>
          <button
            type="button"
            className="ai-btn ai-btn--tiny"
            onClick={() => onChange({ and: [...condition.and, ['is_org']] })}
          >
            + И
          </button>
        </div>
      </div>
    );
  }

  const head = condition[0];
  if (head === 'has_keyword') {
    const words = Array.isArray(condition[1]) ? condition[1] : [];
    return (
      <div className="ai-condition ai-condition--leaf">
        <span>Содержит одно из:</span>
        <textarea
          className="ai-textarea ai-textarea--small"
          rows={2}
          value={words.join('\n')}
          onChange={(e) => onChange(['has_keyword', textToKeywords(e.target.value)])}
        />
        <button type="button" className="ai-btn ai-btn--secondary ai-btn--tiny" onClick={onRemove}>
          Удалить
        </button>
      </div>
    );
  }

  return (
    <div className="ai-condition ai-condition--leaf">
      <select
        className="ai-select"
        value={head}
        onChange={(e) => onChange([e.target.value])}
      >
        <option value="is_org">is_org (организационные keywords)</option>
        <option value="is_study">is_study (учебные keywords)</option>
        <option value="is_progress">is_progress (прогресс keywords)</option>
      </select>
      <button type="button" className="ai-btn ai-btn--secondary ai-btn--tiny" onClick={onRemove}>
        Удалить
      </button>
    </div>
  );
}

function IntentRuleEditor({ intent, rule, source, onChange }) {
  const [keywordsText, setKeywordsText] = useState(keywordsToText(rule.keywords));
  const [priority, setPriority] = useState(rule.priority);
  const [conditions, setConditions] = useState(rule.conditions || []);

  useEffect(() => {
    onChange({
      keywords: textToKeywords(keywordsText),
      priority,
      conditions,
    });
  }, [keywordsText, priority, conditions]);

  return (
    <div className="ai-intent-rule">
      <div className="ai-intent-rule__header">
        <strong>{intent}</strong>
        <span className="ai-status ai-status--muted">
          LMS: {source.lms ? 'да' : 'нет'} · RAG: {source.rag ? 'да' : 'нет'} · strict: {source.strict_course ? 'да' : 'нет'}
        </span>
      </div>

      <InputRow label="Keywords (одна фраза на строку)">
        <textarea
          className="ai-textarea ai-textarea--small"
          rows={3}
          value={keywordsText}
          onChange={(e) => setKeywordsText(e.target.value)}
        />
      </InputRow>

      <InputRow label="Priority" inline>
        <input
          type="number"
          className="ai-input ai-input--inline"
          value={priority}
          min={1}
          onChange={(e) => setPriority(Number(e.target.value))}
        />
      </InputRow>

      <div className="ai-field-row">
        <label className="ai-field-label">Conditions</label>
        {conditions.length === 0 && <p className="ai-field-hint">Нет conditions — классификация по keywords.</p>}
        {conditions.map((cond, idx) => (
          <ConditionBuilder
            key={idx}
            condition={cond}
            ruleKeywords={textToKeywords(keywordsText)}
            onChange={(next) => {
              const updated = [...conditions];
              updated[idx] = next;
              setConditions(updated);
            }}
            onRemove={() => setConditions(conditions.filter((_, i) => i !== idx))}
          />
        ))}
        <button
          type="button"
          className="ai-btn ai-btn--small"
          onClick={() => setConditions([...conditions, ['is_org']])}
        >
          + Condition
        </button>
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

  async function save() {
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
      setMessage('Конфигурация оркестратора сохранена');
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
        Загрузка конфигурации оркестратора…
      </div>
    );
  }

  return (
    <div className="ai-config-page">
      <div className="ai-page__header">
        <div>
          <h1 className="ai-page__title">Orchestrator</h1>
          <p className="ai-page__subtitle">
            Настройка классификации запросов, выбора источников, лимитов контекста,
            token-бюджетов и fallback-сообщений.
          </p>
        </div>
        <button onClick={load} className="ai-btn ai-btn--small" type="button">
          Обновить
        </button>
      </div>

      {error && <div className="ai-error">{error}</div>}
      {message && <div className="ai-success">{message}</div>}

      <div className="ai-config-top">
        <Section title="Intent Classification" subtitle="Keywords, priority и conditions для каждого intent.">
          <div className="ai-intent-rules">
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

          <InputRow label="Default intent" inline>
            <select
              className="ai-select"
              value={defaultIntent}
              onChange={(e) => setDefaultIntent(e.target.value)}
            >
              {DEFAULT_INTENTS.map((i) => (
                <option key={i} value={i}>{i}</option>
              ))}
            </select>
          </InputRow>
        </Section>

        <Section title="Source Routing" subtitle="Какие источники данных использовать для каждого intent.">
          <table className="ai-table">
            <thead>
              <tr>
                <th>Intent</th>
                <th>LMS</th>
                <th>RAG</th>
                <th>Strict course</th>
              </tr>
            </thead>
            <tbody>
              {DEFAULT_INTENTS.map((intent) => (
                <tr key={intent}>
                  <td>{intent}</td>
                  <td>
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
                  <td>
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
                  <td>
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
        </Section>
      </div>

      <div className="ai-config-bottom">
        <Section title="Context Limits" subtitle="Ограничения LMS-контекста в prompt.">
          <InputRow label="Max LMS contents" inline>
            <input
              type="number"
              className="ai-input ai-input--inline"
              min={1}
              max={100}
              value={maxLmsContents}
              onChange={(e) => setMaxLmsContents(Number(e.target.value))}
            />
          </InputRow>
          <InputRow label="Max LMS deadlines" inline>
            <input
              type="number"
              className="ai-input ai-input--inline"
              min={1}
              max={50}
              value={maxLmsDeadlines}
              onChange={(e) => setMaxLmsDeadlines(Number(e.target.value))}
            />
          </InputRow>
        </Section>

        <Section title="Token Budgets" subtitle="Max output tokens в зависимости от intent и уровня.">
          <InputRow label="Organizational" inline>
            <input
              type="number"
              className="ai-input ai-input--inline"
              min={1}
              max={4096}
              value={intentMaxTokens.organizational}
              onChange={(e) =>
                setIntentMaxTokens({ ...intentMaxTokens, organizational: Number(e.target.value) })
              }
            />
          </InputRow>
          <InputRow label="Study beginner" inline>
            <input
              type="number"
              className="ai-input ai-input--inline"
              min={1}
              max={4096}
              value={intentMaxTokens.study_beginner}
              onChange={(e) =>
                setIntentMaxTokens({ ...intentMaxTokens, study_beginner: Number(e.target.value) })
              }
            />
          </InputRow>
          <InputRow label="Mixed" inline>
            <input
              type="number"
              className="ai-input ai-input--inline"
              min={1}
              max={4096}
              value={intentMaxTokens.mixed}
              onChange={(e) => setIntentMaxTokens({ ...intentMaxTokens, mixed: Number(e.target.value) })}
            />
          </InputRow>
          <InputRow label="Default" inline>
            <input
              type="number"
              className="ai-input ai-input--inline"
              min={1}
              max={4096}
              value={intentMaxTokens.default}
              onChange={(e) =>
                setIntentMaxTokens({ ...intentMaxTokens, default: Number(e.target.value) })
              }
            />
          </InputRow>
        </Section>
      </div>

      <Section title="Fallback Messages" subtitle="Сообщения при недостатке данных или вне области доступных курсов.">
        <InputRow label="No LMS data">
          <textarea
            className="ai-textarea"
            rows={2}
            value={fallbackMessages.no_lms_data}
            onChange={(e) =>
              setFallbackMessages({ ...fallbackMessages, no_lms_data: e.target.value })
            }
          />
        </InputRow>
        <InputRow label="No RAG context">
          <textarea
            className="ai-textarea"
            rows={2}
            value={fallbackMessages.no_rag_context}
            onChange={(e) =>
              setFallbackMessages({ ...fallbackMessages, no_rag_context: e.target.value })
            }
          />
        </InputRow>
        <InputRow label="Out of scope course (placeholder: {course})">
          <textarea
            className="ai-textarea"
            rows={2}
            value={fallbackMessages.out_of_scope_course}
            onChange={(e) =>
              setFallbackMessages({ ...fallbackMessages, out_of_scope_course: e.target.value })
            }
          />
        </InputRow>
      </Section>

      <Section title="Course Name Starters" subtitle="Слова, которые не считаются названиями курсов при экстракции.">
        <InputRow label="Non-course starters (одно слово на строку)">
          <textarea
            className="ai-textarea"
            rows={6}
            value={nonCourseStarters}
            onChange={(e) => setNonCourseStarters(e.target.value)}
          />
        </InputRow>
      </Section>

      <div className="ai-actions-center ai-actions--sticky">
        <button type="button" className="ai-btn" onClick={save} disabled={saving}>
          {saving ? 'Сохранение…' : 'Сохранить'}
        </button>
      </div>
    </div>
  );
}

export default OrchestratorConfig;
