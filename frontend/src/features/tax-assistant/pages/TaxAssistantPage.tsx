import { ArrowUpRight, FileText, History, ShieldCheck, Sparkles } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { ChatMessage, FeedbackRating } from '../../../shared/types/tax'
import { ChatComposer } from '../components/ChatComposer'
import { MessageList } from '../components/MessageList'

interface Props {
  messages: ChatMessage[]
  busy: boolean
  error: string
  feedback: Record<string, FeedbackRating>
  onSend: (question: string, period: string, taxpayer: string) => void
  onFeedback: (id: string | undefined, rating: FeedbackRating) => void
  onDismissError: () => void
}

export function TaxAssistantPage({ messages, busy, error, feedback, onSend, onFeedback, onDismissError }: Props) {
  return <>
    <div className="chat-scroller">
      {messages.length ? <MessageList messages={messages} busy={busy} feedback={feedback} onFeedback={onFeedback} /> : <Welcome onSend={onSend} />}
    </div>
    <ChatComposer busy={busy} error={error} onSend={onSend} onDismissError={onDismissError} />
  </>
}

function Welcome({ onSend }: Pick<Props, 'onSend'>) {
  const { t } = useTranslation()
  const promptKeys = ['ppn', 'pph', 'regulation', 'period'] as const
  return <section className="welcome">
    <div className="welcome-eyebrow"><span className="eyebrow-line" /> {t('chat.eyebrow')} <span className="eyebrow-line" /></div>
    <div className="welcome-emblem"><Sparkles size={21} /></div>
    <h1>{t('chat.title')}</h1>
    <p className="welcome-subtitle">{t('chat.subtitle')}</p>
    <div className="trust-chips"><span><ShieldCheck size={14} /> {t('chat.evidenceGrounded')}</span><span><FileText size={14} /> {t('chat.sourceCited')}</span><span><History size={14} /> {t('chat.periodAware')}</span></div>
    <div className="prompt-heading"><span>{t('chat.promptHeading')}</span><span className="prompt-hint">{t('chat.promptHint')}</span></div>
    <div className="suggestion-grid">{promptKeys.map((key, index) => <button key={key} className="suggestion-card" onClick={() => onSend(t(`chat.prompts.${key}.question`), '', '')}><span className="suggestion-number">0{index + 1}</span><span className="suggestion-label">{t(`chat.prompts.${key}.label`)}</span><ArrowUpRight size={15} /><span className="suggestion-text">{t(`chat.prompts.${key}.question`)}</span></button>)}</div>
    <div className="welcome-disclaimer"><ShieldCheck size={14} /> {t('chat.disclaimer')}</div>
  </section>
}
