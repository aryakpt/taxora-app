import { Navigate, Route, Routes } from 'react-router-dom'
import type { ApiRequest } from '../shared/api/client'
import type { ChatMessage, FeedbackRating } from '../shared/types/tax'
import { TaxAssistantPage } from '../features/tax-assistant/pages/TaxAssistantPage'
import { KnowledgeAdminPage } from '../features/knowledge-admin/pages/KnowledgeAdminPage'
import { RegulationLibraryPage } from '../features/regulation-library/pages/RegulationLibraryPage'

interface Props {
  request: ApiRequest
  messages: ChatMessage[]
  busy: boolean
  error: string
  feedback: Record<string, FeedbackRating>
  setError: (message: string) => void
  onSend: (question: string, period: string, taxpayer: string) => void
  onFeedback: (messageId: string | undefined, rating: FeedbackRating) => void
}

export function AppRouter({ request, messages, busy, error, feedback, setError, onSend, onFeedback }: Props) {
  return <Routes>
    <Route path="/" element={<TaxAssistantPage messages={messages} busy={busy} error={error} feedback={feedback} onSend={onSend} onFeedback={onFeedback} onDismissError={() => setError('')} />} />
    <Route path="/regulations" element={<RegulationLibraryPage request={request} error={error} setError={setError} />} />
    <Route path="/admin" element={<KnowledgeAdminPage request={request} error={error} setError={setError} />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
}
