const BASE = '/api/v1'

function getApiKey() {
  return window.localStorage.getItem('api_key') || import.meta.env.VITE_API_KEY || ''
}

function buildHeaders(extra = {}) {
  const headers = { ...extra }
  const apiKey = getApiKey()
  if (apiKey) headers['X-API-Key'] = apiKey
  return headers
}

async function parseJsonOrThrow(res) {
  const contentType = res.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')

  const payload = isJson ? await res.json().catch(() => ({})) : await res.text()

  if (!res.ok) {
    const detail = typeof payload === 'object' && payload !== null
      ? payload.detail || payload.message || JSON.stringify(payload)
      : payload
    throw new Error(detail || `Server error ${res.status}`)
  }

  return payload
}

export async function submitProcessReportsTask(files) {
  const form = new FormData()
  for (const file of files) form.append('files', file)
  const res = await fetch(`${BASE}/tasks/process-reports`, {
    method: 'POST',
    headers: buildHeaders(),
    body: form,
  })
  return parseJsonOrThrow(res)
}

export async function submitDietTask(files, prefs = {}) {
  const form = new FormData()
  for (const file of files) form.append('files', file)
  if (Object.keys(prefs).length) {
    form.append('dietary_preferences', JSON.stringify(prefs))
  }
  const res = await fetch(`${BASE}/tasks/generate-diet-plan`, {
    method: 'POST',
    headers: buildHeaders(),
    body: form,
  })
  return parseJsonOrThrow(res)
}

export async function submitRegenerateDietTask(aggregationResult, prefs = {}) {
  const res = await fetch(`${BASE}/tasks/regenerate-diet-plan`, {
    method: 'POST',
    headers: buildHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      aggregation_result: aggregationResult,
      dietary_preferences: prefs,
    }),
  })
  return parseJsonOrThrow(res)
}

export async function pollTask(taskId) {
  const res = await fetch(`${BASE}/tasks/${taskId}`, {
    headers: buildHeaders(),
  })
  return parseJsonOrThrow(res)
}

export async function askChat(sessionId, message, chatHistory = []) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: buildHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      session_id: sessionId,
      message,
      chat_history: chatHistory,
    }),
  })
  return parseJsonOrThrow(res)
}
