const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://curator-api.alex-n8n.site';

async function apiRequest(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
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

export async function checkBackendStatus() {
  try {
    const data = await apiRequest('/health');
    return data.status === 'ok';
  } catch {
    return false;
  }
}

export async function getCourses() {
  return apiRequest('/api/v1/courses');
}

export async function getDeadlines(courseId) {
  return apiRequest(`/api/v1/courses/${courseId}/deadlines`);
}

export async function getProgress() {
  return apiRequest('/api/v1/me/progress');
}

export async function sendChatMessage({ message, role, difficulty, courseId, history = [], sessionId }) {
  return apiRequest('/api/v1/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      role,
      difficulty,
      course_id: courseId,
      history,
      session_id: sessionId,
    }),
  });
}
