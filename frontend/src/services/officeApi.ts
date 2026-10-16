import type { IoTChatHistory, NewTask, OfficeEvent, OfficeSnapshot, OfficeTask } from '../types'

const API_BASE = (import.meta.env.VITE_OFFICE_API_URL ?? '').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })
  if (!response.ok) {
    throw new Error(`Office API ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const fetchSnapshot = () => request<OfficeSnapshot>('/api/office/snapshot')

export const fetchChatHistory = () =>
  request<IoTChatHistory>('/api/office/chat-history?limit=12')

export const createTask = (task: NewTask) =>
  request<OfficeTask>('/api/office/tasks', {
    method: 'POST',
    body: JSON.stringify(task),
  })

export const updateTask = (taskId: string, values: Partial<OfficeTask>) =>
  request<OfficeTask>(`/api/office/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(values),
  })

export function connectOfficeEvents(
  after: string | number | null,
  onEvent: (event: OfficeEvent) => void,
  onConnection: (connected: boolean) => void,
): () => void {
  const query = after == null ? '' : `?after=${encodeURIComponent(String(after))}`
  const source = new EventSource(`${API_BASE}/api/office/events${query}`)
  source.onopen = () => onConnection(true)
  source.onerror = () => onConnection(false)
  source.addEventListener('office.status', (message) => {
    onEvent(JSON.parse((message as MessageEvent<string>).data) as OfficeEvent)
  })
  return () => source.close()
}

