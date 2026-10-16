export type ChatView = 'chat' | 'library' | 'admin'
export type MessageRole = 'user' | 'assistant'
export type FeedbackRating = 'positive' | 'negative'

export interface Source {
  evidence_id: string
  regulation_number: string
  title: string
  article?: string | null
  quote: string
  source_url: string
  verification_status: string
  effective_from?: string | null
  effective_until?: string | null
}

export interface ChatMessage {
  id?: string
  role: MessageRole
  content: string
  sources?: Source[]
  status?: string
  latency?: number
  missing?: string[]
  limitations?: string[]
}

export interface ConversationSummary {
  id: string
  title: string
  updated_at?: string
}

export interface Regulation {
  id: string
  number: string
  type: string
  title: string
  topic: string
  source_url: string
}

export interface IngestionJob {
  id: string
  source_url: string
  status: string
  error?: string | null
  created_at?: string
}

export interface ChatResponse {
  request_id: string
  conversation_id: string
  answer_status: string
  answer: string
  sources?: Source[]
  missing_information?: string[]
  limitations?: string[]
  latency_ms: number
}
