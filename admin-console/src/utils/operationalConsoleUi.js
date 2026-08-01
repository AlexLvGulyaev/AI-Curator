/**
 * Shared operational-console UI helpers.
 * Adapted from AI Portfolio operationalConsoleUi.ts.
 */

export function detailsJsonPreview(d) {
  if (d == null) return 'пусто';
  if (typeof d === 'string') return d.length > 56 ? `${d.slice(0, 56)}…` : d;
  try {
    const s = JSON.stringify(d);
    return s.length > 56 ? `${s.slice(0, 56)}…` : s || '{}';
  } catch {
    return '?';
  }
}

export function formatDetailsJson(d) {
  if (d == null) return 'null';
  if (typeof d === 'string') return d;
  try {
    return JSON.stringify(d, null, 2);
  } catch {
    return String(d);
  }
}

export function statusBadgeClass(status) {
  const s = String(status || '').trim().toLowerCase();
  if (s === 'ok' || s === 'success') {
    return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
  }
  if (s === 'error' || s === 'failed') {
    return 'bg-red-500/15 text-red-400 border-red-500/30';
  }
  if (s === 'pending' || s === 'started' || s === 'loading') {
    return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
  }
  return 'bg-ai-surface text-ai-text-muted border-ai-border';
}

export function normalizeOperationalModality(raw) {
  const k = String(raw || '').trim().toLowerCase();
  const known = ['rag', 'text', 'lms', 'mixed', 'log'];
  if (known.includes(k)) return k;
  if (k === 'mixed') return 'mixed';
  if (k.includes('rag')) return 'rag';
  if (k.includes('lms')) return 'lms';
  if (k.includes('text')) return 'text';
  return 'log';
}

export function operationalModalityBadgeClassList(mod) {
  const safe = normalizeOperationalModality(mod);
  const base = 'inline-flex items-center justify-center px-1.5 py-0.5 rounded text-[0.65rem] font-bold uppercase tracking-wide border';
  const map = {
    rag: 'bg-ai-primary-light text-ai-primary border-ai-primary/40',
    text: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/40',
    lms: 'bg-ai-warning-light text-ai-warning border-ai-warning/40',
    mixed: 'bg-ai-info-light text-ai-info border-ai-info/40',
    log: 'bg-ai-surface text-ai-text-muted border-ai-border',
  };
  return `${base} ${map[safe] || map.log}`;
}

export function operationalModalityFromRouteKey(routeKey) {
  const r = String(routeKey || '').trim().toLowerCase();
  if (!r) return 'log';
  if (r.includes('rag')) return 'rag';
  if (r.includes('lms')) return 'lms';
  if (r === 'text') return 'text';
  if (r.includes('mixed')) return 'mixed';
  return 'log';
}

export function pipelineStageVariant(stage, status) {
  const s = String(stage || '').toLowerCase();
  const st = String(status || '').trim().toLowerCase();
  if (st === 'error' || st === 'failed' || s.includes('error') || s.endsWith('_error')) return 'error';
  if (st === 'warning' || s.includes('warn')) return 'warning';
  if (s.includes('_started') || s.includes('loading') || s.includes('pending')) return 'loading';
  if (s.includes('_done') || s.includes('completed') || s.includes('success') || st === 'ok' || st === 'success') return 'success';
  if (s.includes('processing') || s.includes('retrieve') || s.includes('embedding') || s.includes('build')) return 'processing';
  return 'muted';
}
