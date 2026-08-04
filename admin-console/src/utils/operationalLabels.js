/**
 * Operational display labels for logs / lifecycle.
 * Adapted from AI Portfolio operationalLabels.ts.
 */

const STATUS_RU = {
  ok: 'успешно',
  error: 'ошибка',
  pending: 'ожидание',
  skipped: 'пропущено',
  retry: 'повтор',
  started: 'запущено',
  warning: 'предупреждение',
  failed: 'ошибка',
};

const INTENT_RU = {
  study: 'учебный',
  organizational: 'организационный',
  mixed: 'смешанный',
  progress: 'прогресс',
  deadline: 'дедлайн',
};

const ROUTE_LABEL_RU = {
  text: 'TEXT',
  lms: 'LMS',
  rag: 'RAG',
  mixed: 'MIXED',
};

const STAGE_NAME_RU = {
  intent_classify: 'Классификация intent',
  cache_hit: 'Cache hit',
  lms_fetch: 'LMS fetch',
  rag_search: 'RAG поиск',
  context_build: 'Построение контекста',
  llm_call: 'Вызов LLM',
  answer_validate: 'Валидация ответа',
  source_attach: 'Прикрепление источников',
  response_save: 'Сохранение ответа',
};

export function normalizeStatus(s) {
  return String(s || '').trim().toLowerCase();
}

export function statusLabelRu(raw) {
  return STATUS_RU[normalizeStatus(raw)] || raw || '—';
}

export function intentLabelRu(raw) {
  return INTENT_RU[normalizeStatus(raw)] || raw || '—';
}

export function formatTimestampMsk(isoOrMs) {
  if (isoOrMs == null) return '—';
  const ms = typeof isoOrMs === 'number' ? isoOrMs : new Date(isoOrMs).getTime();
  if (!Number.isFinite(ms)) return '—';
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
    .format(new Date(ms))
    .replace(',', '');
}

export function formatTimeMsk(isoOrMs) {
  if (isoOrMs == null) return '—';
  const ms = typeof isoOrMs === 'number' ? isoOrMs : new Date(isoOrMs).getTime();
  if (!Number.isFinite(ms)) return '—';
  return new Intl.DateTimeFormat('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(ms));
}

export function formatDate(isoOrMs) {
  if (isoOrMs == null) return '—';
  const ms = typeof isoOrMs === 'number' ? isoOrMs : new Date(isoOrMs).getTime();
  if (!Number.isFinite(ms)) return '—';
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(ms));
}

export function formatDurationMs(ms) {
  if (ms == null || !Number.isFinite(ms)) return '—';
  if (ms < 1000) return `${Math.round(ms)} мс`;
  return `${(ms / 1000).toFixed(2)} с`;
}

export function shortId(id, n = 8) {
  if (!id) return '—';
  return id.length <= n ? id : `${id.slice(0, n)}…`;
}

export function normalizeRouteKey(route) {
  const raw = String(route || '').trim().toLowerCase();
  if (!raw) return 'unknown';
  if (raw === 'rag' || raw.includes('rag')) return 'rag';
  if (raw === 'lms' || raw.includes('lms')) return 'lms';
  if (raw === 'text' || raw.includes('text')) return 'text';
  if (raw === 'mixed' || raw.includes('mixed')) return 'mixed';
  return 'unknown';
}

export function routeLabelRu(route) {
  return ROUTE_LABEL_RU[normalizeRouteKey(route)] || route || '—';
}

export function shortModelName(model) {
  if (!model) return '—';
  const raw = String(model).trim().toLowerCase();
  if (raw.includes('gpt')) return 'gpt';
  if (raw.includes('gigachat')) return 'gigachat';
  if (raw.includes('claude')) return 'claude';
  if (raw.includes('llama')) return 'llama';
  if (raw.includes('deepseek')) return 'deepseek';
  if (raw.includes('yandex')) return 'yandex';
  const first = raw.split(/[-_/\s]/)[0];
  return first || model;
}

export function stageToActionRu(stage) {
  const raw = String(stage || '').trim();
  if (!raw) return '—';
  return STAGE_NAME_RU[raw] || raw.replace(/_/g, ' ');
}
