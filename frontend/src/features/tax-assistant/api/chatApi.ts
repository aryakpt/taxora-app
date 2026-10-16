import type { ApiRequest } from '../../../shared/api/client'
import type { ChatResponse, FeedbackRating } from '../../../shared/types/tax'

export interface ConsultationContext {
  tax_period: string | null
  taxpayer_type: string | null
  transaction_type: string | null
}

export type ResponseLanguage = 'en' | 'id'

export function createChatApi(request: ApiRequest) {
  return {
    ask: (conversationId: string | null, question: string, context: ConsultationContext, responseLanguage: ResponseLanguage) => request<ChatResponse>('/api/v1/chat', {
      method: 'POST', data: { conversation_id: conversationId, question, context, response_language: responseLanguage },
    }),
    feedback: (messageId: string, rating: FeedbackRating) => request<{ saved: boolean }>('/api/v1/feedback', {
      method: 'POST', data: { message_id: messageId, rating },
    }),
  }
}
