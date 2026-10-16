import { useEffect, useRef } from 'react'
import { BookOpen, CircleHelp, ShieldCheck, Sparkles, ThumbsDown, ThumbsUp, ArrowUpRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { ChatMessage, FeedbackRating } from '../../../shared/types/tax'

interface Props {
  messages: ChatMessage[]
  busy: boolean
  feedback: Record<string, FeedbackRating>
  onFeedback: (id: string | undefined, rating: FeedbackRating) => void
}

export function MessageList({ messages, busy, feedback, onFeedback }: Props) {
  const { t } = useTranslation()
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])

  return <section className="messages" aria-live="polite">
    {messages.map((message, index) => <article key={message.id || `${message.role}-${index}`} className={`message-row ${message.role}`}>
      <div className={`message-avatar ${message.role}`}>{message.role === 'assistant' ? <span className="mini-mark" /> : 'U'}</div>
      <div className="message-body">
        <div className="message-meta"><strong>{message.role === 'assistant' ? t('messages.assistant') : t('messages.user')}</strong>{message.role === 'assistant' && <span className="ai-badge"><Sparkles size={11} /> {t('messages.aiResponse')}</span>}</div>
        <div className={`message-content ${message.role === 'user' ? 'user-content' : ''}`}>{message.content}</div>
        {message.role === 'assistant' && <>
          {message.status && message.status !== 'answered' && <div className={`answer-status ${message.status}`}><CircleHelp size={15} /><span>{message.status === 'insufficient_evidence' ? t('messages.insufficientEvidence') : message.status === 'clarification_needed' ? t('messages.clarificationNeeded') : t('messages.failed')}</span></div>}
          {!!message.missing?.length && <div className="answer-note"><strong>{t('messages.clarify')}</strong>{message.missing.map(item => <span key={item}>• {item}</span>)}</div>}
          {!!message.limitations?.length && <div className="answer-note limitation"><strong>{t('messages.limitations')}</strong>{message.limitations.map(item => <span key={item}>{item}</span>)}</div>}
          {!!message.sources?.length && <div className="sources-block"><div className="sources-title"><span><BookOpen size={15} /> {t('messages.legalBasis')}</span><span className="source-count">{message.sources.length} {t(message.sources.length === 1 ? 'messages.source' : 'messages.sources')}</span></div>
            {message.sources.map(source => <div className="source-card" key={source.evidence_id}>
              <div className="source-top"><span className="source-type">{t('messages.regulation')}</span><span className={`verification ${source.verification_status === 'published' ? 'verified' : ''}`}><ShieldCheck size={12} />{source.verification_status === 'published' ? t('common.published') : source.verification_status}</span></div>
              <a className="source-name" href={source.source_url} target="_blank" rel="noreferrer">{source.regulation_number} · {source.title}<ArrowUpRight size={14} /></a>
              {source.article && <span className="source-article">{source.article}</span>}
              <blockquote>“{source.quote}”</blockquote>
              <div className="source-bottom"><span>{source.effective_from ? t('messages.effective', { date: source.effective_from }) : t('messages.effectiveUnknown')}</span><a href={source.source_url} target="_blank" rel="noreferrer">{t('messages.viewOriginal')} <ArrowUpRight size={12} /></a></div>
            </div>)}
          </div>}
          <div className="message-actions"><button aria-label={t('messages.helpful')} title={t('messages.helpful')} className={feedback[message.id || ''] === 'positive' ? 'rated' : ''} onClick={() => onFeedback(message.id, 'positive')}><ThumbsUp size={14} /></button><button aria-label={t('messages.unhelpful')} title={t('messages.unhelpful')} className={feedback[message.id || ''] === 'negative' ? 'rated' : ''} onClick={() => onFeedback(message.id, 'negative')}><ThumbsDown size={14} /></button><span>{message.latency ? `${(message.latency / 1000).toFixed(1)}s` : ''}</span></div>
        </>}
      </div>
    </article>)}
    {busy && <article className="message-row assistant"><div className="message-avatar assistant"><span className="mini-mark" /></div><div className="message-body"><div className="message-meta"><strong>{t('messages.assistant')}</strong><span className="ai-badge"><Sparkles size={11} /> {t('messages.reviewingSources')}</span></div><div className="loading-card"><span className="spinner" /><span>{t('messages.loadingAnswer')}</span></div></div></article>}
    <div ref={bottomRef} />
  </section>
}
