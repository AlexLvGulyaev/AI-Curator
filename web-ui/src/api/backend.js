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
    let message = `Ошибка ${response.status}: ${text}`;
    try {
      const data = JSON.parse(text);
      if (data.detail) {
        message = data.detail;
      }
    } catch {
      // keep raw text
    }
    if (response.status === 429) {
      throw new Error(`Демо-лимит исчерпан: ${message}. Начните новую сессию.`);
    }
    if (response.status === 403 || response.status === 401) {
      throw new Error(`Доступ запрещён: ${message}. Начните новую демо-сессию.`);
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export async function startDemoSession(sessionId = null) {
  return apiRequest('/api/v1/demo/start', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function getDemoStatus(demoToken) {
  return apiRequest('/api/v1/demo/status', {
    headers: { 'X-Demo-Token': demoToken },
  });
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

export async function sendChatMessage({ message, role, difficulty, courseId, history = [], sessionId, demoToken }) {
  const headers = {};
  if (demoToken) {
    headers['X-Demo-Token'] = demoToken;
  }
  return apiRequest('/api/v1/chat', {
    method: 'POST',
    headers,
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

export async function sendChatFeedback(logId, score) {
  return apiRequest(`/api/v1/chat/${logId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ score }),
  });
}
