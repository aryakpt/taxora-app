import type {ApiRequest} from '../../../shared/api/client';
import type {ChatMessage, ConversationGroup, ConversationSummary, Source} from '../../../shared/types/tax';

interface StoredMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  answer_status?: string | null;
  sources?: Source[];
  missing_information?: string[];
  limitations?: string[];
  latency_ms?: number | null;
}

interface ConversationDetail {
  id: string;
  title: string;
  messages: StoredMessage[];
}

export function createConversationsApi(request: ApiRequest) {
  return {
    list: () => request<ConversationSummary[]>('/api/v1/conversations'),
    rename: (id: string, title: string) =>
      request<ConversationSummary>(`/api/v1/conversations/${id}`, {method: 'PATCH', data: {title}}),
    move: (id: string, groupId: string | null) =>
      request<ConversationSummary>(`/api/v1/conversations/${id}`, {method: 'PATCH', data: {group_id: groupId}}),
    remove: (id: string) => request<{deleted: boolean}>(`/api/v1/conversations/${id}`, {method: 'DELETE'}),
    groups: () => request<ConversationGroup[]>('/api/v1/conversation-groups'),
    createGroup: (name: string) =>
      request<ConversationGroup>('/api/v1/conversation-groups', {method: 'POST', data: {name}}),
    renameGroup: (id: string, name: string) =>
      request<ConversationGroup>(`/api/v1/conversation-groups/${id}`, {method: 'PATCH', data: {name}}),
    removeGroup: (id: string) => request<{deleted: boolean}>(`/api/v1/conversation-groups/${id}`, {method: 'DELETE'}),
    async get(id: string): Promise<ChatMessage[]> {
      const detail = await request<ConversationDetail>(`/api/v1/conversations/${id}`);
      // Same shape as a fresh answer, so a reopened conversation looks exactly as it did.
      return detail.messages.map((message) => ({
        id: message.id,
        role: message.role,
        content: message.content,
        status: message.answer_status ?? undefined,
        sources: message.sources ?? [],
        missing: message.missing_information ?? [],
        limitations: message.limitations ?? [],
        latency: message.latency_ms ?? undefined,
      }));
    },
  };
}
