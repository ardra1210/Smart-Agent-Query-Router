import type { AgentInfo, Health, QueryResult } from './types'

// Empty in development (Vite proxies /api); set VITE_API_URL for a deployed backend.
const BASE_URL = import.meta.env.VITE_API_URL ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) throw new Error(`Request failed (${res.status})`)
  return res.json() as Promise<T>
}

export const fetchHealth = () => request<Health>('/api/health')

export const fetchAgents = () => request<AgentInfo[]>('/api/agents')

export const sendQuery = (query: string) =>
  request<QueryResult>('/api/query', { method: 'POST', body: JSON.stringify({ query }) })
