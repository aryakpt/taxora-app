import type { ApiRequest } from '../../../shared/api/client'
import type { ChatResponse, FeedbackRating } from '../../../shared/types/tax'

export interface ConsultationContext {
  tax_period: string | null
  taxpayer_type: string | null
  transaction_type: string | null
}

export type ResponseLanguage = 'en' | 'id'

// The backend may try the LLM twice at up to 60 s each (LLM_ATTEMPTS x LLM_TIMEOUT_SECONDS); free models
// often need 15-70 s. The default 30 s request timeout would give up on answers that are still coming.
const CHAT_TIMEOUT_MS = 150_000

export function createChatApi(request: ApiRequest) {
  return {
    ask: (conversationId: string | null, question: string, context: ConsultationContext, responseLanguage: ResponseLanguage) => request<ChatResponse>('/api/v1/chat', {
      method: 'POST', data: { conversation_id: conversationId, question, context, response_language: responseLanguage },
      timeout: CHAT_TIMEOUT_MS,
    }),
    feedback: (messageId: string, rating: FeedbackRating) => request<{ saved: boolean }>('/api/v1/feedback', {
      method: 'POST', data: { message_id: messageId, rating },
    }),
  }
}
