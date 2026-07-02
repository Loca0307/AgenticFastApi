const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function runAgent(task) {
  const response = await fetch(`${API_BASE_URL}/agent-review/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ task }),
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const detail = data?.detail || `Backend returned ${response.status}`
    throw new Error(detail)
  }

  return data
}
