const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

async function apiRequest(path, { token, method = 'GET', body, isForm = false } = {}) {
  const headers = {};
  if (!isForm) {
    headers['Content-Type'] = 'application/json';
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};

  if (!response.ok) {
    const message = data.detail || JSON.stringify(data);
    throw new Error(message);
  }

  return data;
}

export async function register(payload) {
  return apiRequest('/auth/register/', { method: 'POST', body: payload });
}

export async function login(payload) {
  return apiRequest('/auth/token/', { method: 'POST', body: payload });
}

export async function uploadDocument(token, file) {
  const formData = new FormData();
  formData.append('file', file);
  return apiRequest('/documents/upload/', { method: 'POST', token, body: formData, isForm: true });
}

export async function uploadBatch(token, archive) {
  const formData = new FormData();
  formData.append('archive', archive);
  return apiRequest('/documents/upload-batch/', { method: 'POST', token, body: formData, isForm: true });
}

export async function listDocuments(token) {
  return apiRequest('/documents/', { token });
}

export async function getTask(token, taskId) {
  return apiRequest(`/processing/tasks/${taskId}/`, { token });
}

export async function searchDocuments(token, query) {
  return apiRequest(`/search/documents/?q=${encodeURIComponent(query)}`, { token });
}

export async function downloadProcessedResult(token, documentId) {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}/download/`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const text = await response.text();
    let message = text;
    try {
      const parsed = JSON.parse(text);
      message = parsed.detail || text;
    } catch (_error) {
      message = text;
    }
    throw new Error(message || 'Download failed');
  }

  const blob = await response.blob();
  const disposition = response.headers.get('content-disposition') || '';
  const match = disposition.match(/filename=\"?([^\";]+)\"?/i);
  const filename = match ? match[1] : 'processed-document.txt';
  return { blob, filename };
}
