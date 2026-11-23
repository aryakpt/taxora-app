import { useCallback, useEffect, useState } from 'react'
import type { ApiRequest } from '../../../shared/api/client'
import type { ChatMessage, ConversationGroup, ConversationSummary } from '../../../shared/types/tax'
import { createConversationsApi } from '../api/conversationsApi'

const byName = (a: ConversationGroup, b: ConversationGroup) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })

export function useConversations(request: ApiRequest, token: string) {
  const api = createConversationsApi(request)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [groups, setGroups] = useState<ConversationGroup[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])

  const refresh = useCallback(async () => {
    if (!token) return
    const [list, groupList] = await Promise.all([api.list(), api.groups()])
    setConversations(list)
    setGroups(groupList)
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

  const move = useCallback(async (id: string, groupId: string | null) => {
    const moved = await api.move(id, groupId)
    setConversations(current => current.map(item => item.id === id ? { ...item, group_id: moved.group_id ?? null } : item))
  }, [])

  const remove = useCallback(async (id: string) => {
    await api.remove(id)
    setConversations(current => current.filter(item => item.id !== id))
    if (activeId === id) startNew()
  }, [activeId, startNew])

  const createGroup = useCallback(async (name: string) => {
    const group = await api.createGroup(name)
    setGroups(current => [...current, group].sort(byName))
    return group
  }, [])

  const renameGroup = useCallback(async (id: string, name: string) => {
    const group = await api.renameGroup(id, name)
    setGroups(current => current.map(item => item.id === id ? group : item).sort(byName))
  }, [])

  const removeGroup = useCallback(async (id: string) => {
    await api.removeGroup(id)
    setGroups(current => current.filter(item => item.id !== id))
    // The server keeps the conversations and takes them out of the group.
    setConversations(current => current.map(item => item.group_id === id ? { ...item, group_id: null } : item))
  }, [])

  return {
    conversations, setConversations, groups, activeId, setActiveId, messages, setMessages, refresh, open, startNew,
    rename, move, remove, createGroup, renameGroup, removeGroup,
  }
}
