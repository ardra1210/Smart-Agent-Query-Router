// Mirrors backend/app/models.py.

export type RouteStatus = 'routed' | 'clarify' | 'fallback' | 'multi'

export interface ResponseItem {
  id: string
  title: string
  subtitle: string
  status: string | null
}

export interface AgentResponse {
  agent: string
  capability: string
  message: string
  items: ResponseItem[]
}

export interface RoutingDecision {
  status: RouteStatus
  agent: string | null
  confidence: number
  scores: Record<string, number>
  signals: Record<string, string[]>
  candidates: string[]
  strategy: string
  reason: string | null
  escalated: boolean
}

export interface QueryResult {
  query: string
  message: string
  decision: RoutingDecision
  response: AgentResponse | null
  latency_ms: number
  parts: QueryResult[]
}

export interface Health {
  status: string
  strategy: string
  escalation: string | null
}

export interface AgentInfo {
  name: string
  label: string
  description: string
  capabilities: { name: string; description: string }[]
}

export type ChatMessage =
  | { id: string; role: 'user'; text: string }
  | { id: string; role: 'assistant'; result: QueryResult }
  | { id: string; role: 'error'; text: string }
