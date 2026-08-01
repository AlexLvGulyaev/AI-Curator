const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://curator-api.alex-n8n.site';

function getToken() {
  return localStorage.getItem('ai-curator-admin-token');
}

async function apiRequest(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;
  const token = getToken();
  const headers = {
    ...options.headers,
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Ошибка ${response.status}: ${text}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

// Monitoring
export async function getMonitoringStatus() {
  return apiRequest('/api/v1/admin/monitoring/status');
}

export async function getRecentErrors(limit = 10) {
  return apiRequest(`/api/v1/admin/monitoring/errors?limit=${limit}`);
}

// Knowledge Base
export async function listKbDocuments(params = {}) {
  const qs = new URLSearchParams();
  if (params.course_id) qs.set('course_id', params.course_id);
  if (params.module_id) qs.set('module_id', params.module_id);
  if (params.is_published !== undefined && params.is_published !== null) qs.set('is_published', params.is_published);
  if (params.limit) qs.set('limit', params.limit);
  if (params.offset !== undefined) qs.set('offset', params.offset);
  return apiRequest(`/api/v1/admin/kb/documents?${qs.toString()}`);
}

export async function getKbDocument(id) {
  return apiRequest(`/api/v1/admin/kb/documents/${id}`);
}

export async function uploadKbDocument(formData) {
  return apiRequest('/api/v1/admin/kb/documents', {
    method: 'POST',
    body: formData,
  });
}

export async function updateKbDocument(id, data) {
  return apiRequest(`/api/v1/admin/kb/documents/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function processKbDocument(id) {
  return apiRequest(`/api/v1/admin/kb/documents/${id}/process`, {
    method: 'POST',
  });
}

export async function publishKbDocument(id, publish = true) {
  return apiRequest(`/api/v1/admin/kb/documents/${id}/publish?publish=${publish}`, {
    method: 'POST',
  });
}

export async function uploadKbVersion(id, formData) {
  return apiRequest(`/api/v1/admin/kb/documents/${id}/versions`, {
    method: 'POST',
    body: formData,
  });
}

export async function getKbDocumentDetail(id) {
  return apiRequest(`/api/v1/admin/kb/documents/${id}/detail`);
}

export async function getKbVersionText(documentId, versionId, full = false, stage = 'cleaned') {
  return apiRequest(
    `/api/v1/admin/kb/documents/${documentId}/versions/${versionId}/text?full=${full}&stage=${encodeURIComponent(stage)}`
  );
}

export async function saveKbVersionText(documentId, versionId, text, stage = 'cleaned', reindex = true) {
  return apiRequest(
    `/api/v1/admin/kb/documents/${documentId}/versions/${versionId}/text?stage=${encodeURIComponent(stage)}&reindex=${reindex}`,
    {
      method: 'POST',
      body: JSON.stringify({ text }),
    }
  );
}

export async function getKbVersionChunks(documentId, versionId) {
  return apiRequest(
    `/api/v1/admin/kb/documents/${documentId}/versions/${versionId}/chunks`
  );
}

export async function getKbDocumentTimeline(documentId, limit = 100) {
  return apiRequest(
    `/api/v1/admin/kb/documents/${documentId}/timeline?limit=${limit}`
  );
}

export async function reindexKbVersion(documentId, versionId) {
  return apiRequest(
    `/api/v1/admin/kb/documents/${documentId}/versions/${versionId}/reindex`,
    { method: 'POST' }
  );
}

export async function activateKbVersion(documentId, versionId) {
  return apiRequest(
    `/api/v1/admin/kb/documents/${documentId}/versions/${versionId}/activate`,
    { method: 'POST' }
  );
}

export async function reindexKbDocument(documentId) {
  return apiRequest(`/api/v1/admin/kb/documents/${documentId}/reindex`, {
    method: 'POST',
  });
}

export async function reindexAllKbDocuments() {
  return apiRequest('/api/v1/admin/kb/reindex-all', {
    method: 'POST',
  });
}

export async function deleteKbDocument(id) {
  return apiRequest(`/api/v1/admin/kb/documents/${id}`, {
    method: 'DELETE',
  });
}

export async function getKbStatus() {
  return apiRequest('/api/v1/admin/kb/status');
}

// AI Config
export async function getActiveAiConfig() {
  return apiRequest('/api/v1/admin/ai-config');
}

export async function getAiConfigHistory() {
  return apiRequest('/api/v1/admin/ai-config/history');
}

export async function createAiConfig(data) {
  return apiRequest('/api/v1/admin/ai-config', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function activateAiConfig(id) {
  return apiRequest(`/api/v1/admin/ai-config/${id}/activate`, {
    method: 'POST',
  });
}

// AI Config — update active config (creates new version and activates it)
export async function updateActiveAiConfig(data) {
  const payload = {
    name: data.name || 'Updated via Admin Console',
    system_prompt: data.system_prompt || '',
    model: data.model || 'gpt-4o-mini',
    temperature: data.temperature ?? 0.3,
    max_tokens: data.max_tokens ?? 1024,
    beginner_instructions: data.beginner_instructions,
    advanced_instructions: data.advanced_instructions,
    few_shot_examples: data.few_shot_examples,
    output_rules: data.output_rules,
    refusal_answer_text: data.refusal_answer_text,
    max_history_messages: data.max_history_messages ?? 6,
  };
  const created = await createAiConfig(payload);
  return activateAiConfig(created.id);
}

// Orchestrator Config
export async function getOrchestratorConfig() {
  return apiRequest('/api/v1/admin/orchestrator/config');
}

export async function updateOrchestratorConfig(data) {
  return apiRequest('/api/v1/admin/orchestrator/config', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// Retrieval Tuning
export async function getRetrievalTuning() {
  return apiRequest('/api/v1/admin/retrieval/tuning');
}

export async function updateRetrievalTuning(data) {
  return apiRequest('/api/v1/admin/retrieval/tuning', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function getRetrievalBackends() {
  return apiRequest('/api/v1/admin/retrieval/backends');
}

export async function reindexKnowledgeBase() {
  return apiRequest('/api/v1/admin/retrieval/reindex', {
    method: 'POST',
  });
}

// LLM Providers
export async function getLlmProviders() {
  return [
    {
      key: 'openai',
      display_name: 'OpenAI',
      is_active: true,
      is_fallback: false,
      implementation_status: 'implemented',
      base_url: 'https://api.openai.com/v1',
      model: 'gpt-4o-mini',
      temperature: 0.3,
      max_tokens: 1024,
      is_enabled: true,
    },
    {
      key: 'gigachat',
      display_name: 'GigaChat',
      is_active: false,
      is_fallback: true,
      implementation_status: 'not_implemented',
      readiness_reason: 'Интеграция GigaChat не реализована в текущей версии.',
      base_url: 'https://gigachat.devices.sberbank.ru/api/v1/chat/completions',
      model: 'GigaChat-Max',
      temperature: 0.1,
      max_tokens: 500,
      is_enabled: false,
    },
  ];
}

export async function updateLlmProvider(key, data) {
  // Placeholder until provider settings backend is implemented.
  return { key, ...data };
}

export async function testLlmProvider(key) {
  // Placeholder until provider test backend is implemented.
  return { ok: key === 'openai', message: key === 'openai' ? 'OpenAI доступен' : 'Provider не реализован' };
}

// Analytics
export async function getAnalyticsDashboard() {
  return apiRequest('/api/v1/admin/analytics/dashboard');
}

export async function getAnalyticsTopics(limit = 20) {
  return apiRequest(`/api/v1/admin/analytics/topics?limit=${limit}`);
}

export async function getAnalyticsUnanswered(limit = 50) {
  return apiRequest(`/api/v1/admin/analytics/unanswered?limit=${limit}`);
}

export async function getAnalyticsFeedback() {
  return apiRequest('/api/v1/admin/analytics/feedback');
}

export async function getAnalyticsEvents(limit = 100) {
  return apiRequest(`/api/v1/admin/analytics/events?limit=${limit}`);
}

// Operational Logs
export async function getOperationalLogs(params = {}) {
  const qs = new URLSearchParams();
  if (params.session_id) qs.set('session_id', params.session_id);
  if (params.role) qs.set('role', params.role);
  if (params.course_id !== undefined) qs.set('course_id', params.course_id);
  if (params.intent) qs.set('intent', params.intent);
  if (params.status) qs.set('status', params.status);
  if (params.has_error !== undefined) qs.set('has_error', params.has_error);
  if (params.date_from) qs.set('date_from', params.date_from);
  if (params.date_to) qs.set('date_to', params.date_to);
  if (params.limit) qs.set('limit', params.limit);
  if (params.offset !== undefined) qs.set('offset', params.offset);
  return apiRequest(`/api/v1/admin/operational-logs?${qs.toString()}`);
}

export async function getOperationalLog(id) {
  return apiRequest(`/api/v1/admin/operational-logs/${id}`);
}

// Dialog Sessions
export async function getDialogSessions(params = {}) {
  const qs = new URLSearchParams();
  if (params.hours) qs.set('hours', params.hours);
  if (params.mode) qs.set('mode', params.mode);
  if (params.active_only !== undefined) qs.set('active_only', params.active_only);
  if (params.search) qs.set('search', params.search);
  if (params.limit) qs.set('limit', params.limit);
  if (params.offset !== undefined) qs.set('offset', params.offset);
  return apiRequest(`/api/v1/admin/dialog-sessions?${qs.toString()}`);
}

export async function getDialogSession(sessionId) {
  return apiRequest(`/api/v1/admin/dialog-sessions/${encodeURIComponent(sessionId)}`);
}

// Audit
export async function getAuditLog(params = {}) {
  const qs = new URLSearchParams();
  if (params.action) qs.set('action', params.action);
  if (params.resource_type) qs.set('resource_type', params.resource_type);
  if (params.user_id) qs.set('user_id', params.user_id);
  if (params.date_from) qs.set('date_from', params.date_from);
  if (params.date_to) qs.set('date_to', params.date_to);
  if (params.limit) qs.set('limit', params.limit);
  if (params.offset !== undefined) qs.set('offset', params.offset);
  return apiRequest(`/api/v1/admin/audit?${qs.toString()}`);
}

export async function getAuditEntry(id) {
  return apiRequest(`/api/v1/admin/audit/${id}`);
}
