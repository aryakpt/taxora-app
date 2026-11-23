import type { ApiRequest } from '../../../shared/api/client'
import type { ChatResponse, FeedbackRating } from '../../../shared/types/tax'

export type ResponseLanguage = 'en' | 'id'

// The backend tries up to LLM_ATTEMPTS models at up to LLM_TIMEOUT_SECONDS each, pausing after a busy (503)
// reply; production allows 4 x 60 s (deploy/vercel.py), under the host's 300 s request limit. When Gemini is
// overloaded the one model still answering can take ~45 s. A shorter timeout would drop answers still coming.
const CHAT_TIMEOUT_MS = 290_000

export function createChatApi(request: ApiRequest) {
  return {
    // The case (tax year, taxpayer, transaction) is described in the question itself.
    ask: (conversationId: string | null, question: string, responseLanguage: ResponseLanguage) => request<ChatResponse>('/api/v1/chat', {
      method: 'POST', data: { conversation_id: conversationId, question, response_language: responseLanguage },
      timeout: CHAT_TIMEOUT_MS,
    }),
    feedback: (messageId: string, rating: FeedbackRating) => request<{ saved: boolean }>('/api/v1/feedback', {
      method: 'POST', data: { message_id: messageId, rating },
    }),
  }
}
