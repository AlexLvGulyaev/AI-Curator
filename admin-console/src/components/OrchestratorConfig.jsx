import { useEffect, useState } from 'react';
import { getOrchestratorConfig, updateOrchestratorConfig } from '../api/backend';

const DEFAULT_INTENTS = ['deadline', 'progress', 'study', 'mixed', 'organizational'];

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

  return (
    <div className="ai-provider-card" style={{ padding: '8px 10px', gap: '6px' }}>
      <div className="ai-provider-card__header" style={{ marginBottom: '2px' }}>
        <strong style={{ fontSize: '0.875rem' }}>{intent}</strong>
        <span className="ai-status ai-status--muted" style={{ fontSize: '0.65rem' }}>
          LMS {source.lms ? '✓' : '—'} · RAG {source.rag ? '✓' : '—'} · strict {source.strict_course ? '✓' : '—'}
        </span>
      </div>

      <textarea
        className="ai-textarea ai-textarea--small"
        rows={2}
        style={{ minHeight: '54px', padding: '5px 8px', fontSize: '0.875rem' }}
        value={keywordsText}
        placeholder="keywords, одна фраза на строку"
        onChange={(e) => setKeywordsText(e.target.value)}
      />

      <div className="ai-field-row ai-field-row--inline" style={{ justifyContent: 'space-between', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <label className="ai-field-label" style={{ margin: 0 }}>Priority</label>
          <input
            type="number"
            className="ai-input ai-input--inline"
            style={{ width: '48px', height: '26px', padding: '2px 4px' }}
            value={priority}
            min={1}
            onChange={(e) => setPriority(Number(e.target.value))}
          />
        </div>
        <button
          type="button"
          className="ai-btn ai-btn--secondary ai-btn--tiny"
          onClick={() => setShowAdvanced((s) => !s)}
        >
          {showAdvanced ? '▾ Advanced' : '▸ Advanced'}
        </button>
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

function NumberField({ label, value, min = 1, max = 4096, onChange }) {
  return (
    <div className="ai-field-row ai-field-row--inline" style={{ gap: '8px', justifyContent: 'space-between' }}>
      <label className="ai-field-label" style={{ flex: 1 }}>
        {label}
      </label>
      <input
        type="number"
        className="ai-input ai-input--inline"
        style={{ width: '64px', height: '26px', padding: '2px 4px', textAlign: 'right' }}
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
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
      setMessage('Конфигурация сохранена');
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
          <h1 className="ai-page__title">Orchestrator</h1>
          <p className="ai-page__subtitle">Классификация запросов, источники данных, лимиты и fallback.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={load} className="ai-btn ai-btn--small ai-btn--secondary" type="button">
            Обновить
          </button>
          <button type="button" className="ai-btn ai-btn--small" onClick={save} disabled={saving}>
            {saving ? 'Сохранение…' : 'Сохранить'}
          </button>
        </div>
      </div>

      {error && <div className="ai-error">{error}</div>}
      {message && <div className="ai-success">{message}</div>}

      <div className="ai-config-top" style={{ gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        <div className="ai-card ai-section" style={{ minHeight: 0, padding: '10px 12px' }}>
          <div
            className="ai-section__title"
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}
          >
            <span>Intent Classification</span>
            <div className="ai-field-row ai-field-row--inline" style={{ gap: '4px' }}>
              <label className="ai-field-label" style={{ margin: 0 }}>Default</label>
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
              <h2 className="ai-section__title" style={{ marginBottom: '8px' }}>Source Routing</h2>
              <table className="ai-table" style={{ fontSize: '0.875rem' }}>
                <thead>
                  <tr>
                    <th>Intent</th>
                    <th style={{ textAlign: 'center' }}>LMS</th>
                    <th style={{ textAlign: 'center' }}>RAG</th>
                    <th style={{ textAlign: 'center' }}>Strict</th>
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
              <h2 className="ai-section__title" style={{ marginBottom: '8px' }}>Limits &amp; Token Budgets</h2>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 12px' }}>
                <NumberField label="Max contents" value={maxLmsContents} max={100} onChange={setMaxLmsContents} />
                <NumberField label="Max deadlines" value={maxLmsDeadlines} max={50} onChange={setMaxLmsDeadlines} />
                <NumberField
                  label="Organizational"
                  value={intentMaxTokens.organizational}
                  onChange={(v) => setIntentMaxTokens({ ...intentMaxTokens, organizational: v })}
                />
                <NumberField
                  label="Study beginner"
                  value={intentMaxTokens.study_beginner}
                  onChange={(v) => setIntentMaxTokens({ ...intentMaxTokens, study_beginner: v })}
                />
                <NumberField
                  label="Mixed"
                  value={intentMaxTokens.mixed}
                  onChange={(v) => setIntentMaxTokens({ ...intentMaxTokens, mixed: v })}
                />
                <NumberField
                  label="Default"
                  value={intentMaxTokens.default}
                  onChange={(v) => setIntentMaxTokens({ ...intentMaxTokens, default: v })}
                />
              </div>
            </div>
          </div>

          <div className="ai-card ai-section" style={{ flex: '1 1 auto', minHeight: 0, padding: '10px 12px' }}>
            <h2 className="ai-section__title" style={{ marginBottom: '8px' }}>Fallbacks &amp; Course Starters</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minHeight: 0 }}>
              <label className="ai-field-label" style={{ margin: 0 }}>No LMS data</label>
              <textarea
                className="ai-textarea ai-textarea--small"
                rows={2}
                style={{ minHeight: '44px', padding: '5px 8px', fontSize: '0.875rem' }}
                value={fallbackMessages.no_lms_data}
                onChange={(e) => setFallbackMessages({ ...fallbackMessages, no_lms_data: e.target.value })}
              />
              <label className="ai-field-label" style={{ margin: 0 }}>No RAG context</label>
              <textarea
                className="ai-textarea ai-textarea--small"
                rows={2}
                style={{ minHeight: '44px', padding: '5px 8px', fontSize: '0.875rem' }}
                value={fallbackMessages.no_rag_context}
                onChange={(e) => setFallbackMessages({ ...fallbackMessages, no_rag_context: e.target.value })}
              />
              <label className="ai-field-label" style={{ margin: 0 }}>Out of scope (placeholder: {'{course}'})</label>
              <textarea
                className="ai-textarea ai-textarea--small"
                rows={2}
                style={{ minHeight: '44px', padding: '5px 8px', fontSize: '0.875rem' }}
                value={fallbackMessages.out_of_scope_course}
                onChange={(e) =>
                  setFallbackMessages({ ...fallbackMessages, out_of_scope_course: e.target.value })
                }
              />
              <label className="ai-field-label" style={{ margin: '4px 0 0' }}>Non-course starters</label>
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
