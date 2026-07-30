export interface Message {
  id: string
  content: string
  role: "user" | "assistant"
  agent?: string
  timestamp: Date
}

export interface Agent {
  name: string
  description: string
  handoffs: string[]
  tools: string[]
  /** List of input guardrail identifiers for this agent */
  input_guardrails: string[]
}

export type EventType =
  | "message"
  | "handoff"
  | "tool_call"
  | "tool_output"
  | "context_update"
  | "progress_update"

export interface AgentEvent {
  id: string
  type: EventType
  agent: string
  content: string
  timestamp: Date
  metadata?: {
    source_agent?: string
    target_agent?: string
    tool_name?: string
    tool_args?: Record<string, any>
    tool_result?: any
    context_key?: string
    context_value?: any
    changes?: Record<string, any>
    icon?: string
  }
}

export interface GuardrailCheck {
  id: string
  name: string
  input: string
  reasoning: string
  passed: boolean
  timestamp: Date
}

export interface Source {
  doc_id: string
  doc_title: string
  page: number
  section: string
  snippet: string
  score: number
  header: string
}

export interface InspectorPayload {
  trace_id: string
  confidence: number
  breakdown: Record<string, number>
  reason_codes: string[]
  next_step_hint: string
  route: string
  path: string[]
  intent: string | null
  slots: Record<string, string>
  sources: Source[]
  latency_ms: number
  pending_approval: boolean
}
