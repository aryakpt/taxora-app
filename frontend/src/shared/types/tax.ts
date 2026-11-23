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

export type JobStatus = 'queued' | 'processing' | 'review_required' | 'approved' | 'published' | 'failed'

export interface IngestionJob {
  id: string
  status: JobStatus
  source_url: string
  filename: string | null
  error: string | null
  detail: string | null
  created_at: string
  updated_at: string
  storage_available: boolean
  regulation: { id: string; type: string; number: string; title: string; issuer: string; topic: string } | null
  version: {
    id: string
    status: JobStatus
    document_hash: string
    issued_at: string | null
    effective_from: string | null
    effective_until: string | null
    verified_at: string | null
  } | null
}

export interface ExtractedSection {
  id: string
  kind: 'preamble' | 'article' | 'attachment'
  number: string | null
  text: string
  chunks: number
}

export interface ChatResponse {
  request_id: string
  conversation_id: string
  message_id: string
  answer_status: string
  answer: string
  sources?: Source[]
  missing_information?: string[]
  limitations?: string[]
  latency_ms: number
}
