import { useCallback, useEffect, useState } from 'react'
import type { ApiRequest } from '../../../shared/api/client'
import type { ChatMessage, ConversationSummary } from '../../../shared/types/tax'
import { createConversationsApi } from '../api/conversationsApi'

export function useConversations(request: ApiRequest, token: string) {
  const api = createConversationsApi(request)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])

  const refresh = useCallback(async () => {
    if (token) setConversations(await api.list())
  }, [token])

  useEffect(() => { refresh().catch(() => undefined) }, [refresh])

  const open = useCallback(async (id: string) => {
    setMessages(await api.get(id))
    setActiveId(id)
  }, [])

  const startNew = useCallback(() => {
    setActiveId(null)
    setMessages([])
  }, [])

  return { conversations, setConversations, activeId, setActiveId, messages, setMessages, refresh, open, startNew }
}
