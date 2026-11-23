import type {ApiRequest} from '../../../shared/api/client';
import type {ChatMessage, ConversationSummary} from '../../../shared/types/tax';

interface ConversationDetail {
  id: string;
  title: string;
  messages: Array<{id: string; role: 'user' | 'assistant'; content: string; metadata?: {answer_status?: string}}>;
}

export function createConversationsApi(request: ApiRequest) {
  return {
    list: () => request<ConversationSummary[]>('/api/v1/conversations'),
    rename: (id: string, title: string) =>
      request<ConversationSummary>(`/api/v1/conversations/${id}`, {method: 'PATCH', data: {title}}),
    remove: (id: string) => request<{deleted: boolean}>(`/api/v1/conversations/${id}`, {method: 'DELETE'}),
    async get(id: string): Promise<ChatMessage[]> {
      const detail = await request<ConversationDetail>(`/api/v1/conversations/${id}`);
      return detail.messages.map((message) => ({
        id: message.id,
        role: message.role,
        content: message.content,
        status: message.metadata?.answer_status,
      }));
    },
  };
}
