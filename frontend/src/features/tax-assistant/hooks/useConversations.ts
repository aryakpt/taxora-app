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

  const rename = useCallback(async (id: string, title: string) => {
    const renamed = await api.rename(id, title)
    setConversations(current => current.map(item => item.id === id ? { ...item, title: renamed.title } : item))
  }, [])

  const remove = useCallback(async (id: string) => {
    await api.remove(id)
    setConversations(current => current.filter(item => item.id !== id))
    if (activeId === id) startNew()
  }, [activeId, startNew])

  return { conversations, setConversations, activeId, setActiveId, messages, setMessages, refresh, open, startNew, rename, remove }
}
