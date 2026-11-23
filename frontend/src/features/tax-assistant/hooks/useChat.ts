import { useCallback, useState } from 'react'
import type { ApiRequest } from '../../../shared/api/client'
import type { ChatMessage, FeedbackRating } from '../../../shared/types/tax'
import { createChatApi, type ResponseLanguage } from '../api/chatApi'

interface ChatOptions {
  request: ApiRequest
  conversationId: string | null
  setConversationId: (id: string) => void
  messages: ChatMessage[]
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>
  refreshConversations: () => Promise<void>
  onError: (message: string) => void
}

export function useChat({ request, conversationId, setConversationId, messages, setMessages, refreshConversations, onError }: ChatOptions) {
  const api = createChatApi(request)
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState<Record<string, FeedbackRating>>({})

  const sendQuestion = useCallback(async (text: string, responseLanguage: ResponseLanguage) => {
    const question = text.trim()
    if (!question || busy) return false
    setBusy(true)
    setMessages(current => [...current, { role: 'user', content: question }])
    try {
      const result = await api.ask(conversationId, question, responseLanguage)
      setConversationId(result.conversation_id)
      setMessages(current => [...current, {
        id: result.message_id,
        role: 'assistant',
        content: result.answer,
        sources: result.sources || [],
        status: result.answer_status,
        latency: result.latency_ms,
        missing: result.missing_information || [],
        limitations: result.limitations || [],
      }])
      await refreshConversations()
      return true
    } catch (error) {
      onError((error as Error).message)
      setMessages(current => current.length > messages.length ? current.slice(0, messages.length) : current)
      return false
    } finally {
      setBusy(false)
    }
  }, [api, busy, conversationId, messages.length, onError, refreshConversations, setConversationId, setMessages])

  const submitFeedback = useCallback(async (messageId: string | undefined, rating: FeedbackRating) => {
    if (!messageId) return
    try {
      await api.feedback(messageId, rating)
      setFeedback(current => ({ ...current, [messageId]: rating }))
    } catch (error) { onError((error as Error).message) }
  }, [api, onError])

  return { busy, feedback, sendQuestion, submitFeedback }
}
