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

// Audit
export async function getAuditLog(params = {}) {
  const qs = new URLSearchParams();
  if (params.action) qs.set('action', params.action);
  if (params.resource_type) qs.set('resource_type', params.resource_type);
  if (params.user_id) qs.set('user_id', params.user_id);
  if (params.limit) qs.set('limit', params.limit);
  if (params.offset !== undefined) qs.set('offset', params.offset);
  return apiRequest(`/api/v1/admin/audit?${qs.toString()}`);
}
