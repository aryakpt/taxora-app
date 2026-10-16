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
