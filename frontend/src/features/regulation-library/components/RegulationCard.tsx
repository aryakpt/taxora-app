import { ArrowUpRight, Check, FileText } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { Regulation } from '../../../shared/types/tax'

interface Props { regulation: Regulation }

export function RegulationCard({ regulation }: Props) {
  const { t } = useTranslation()
  return <article className="regulation-card">
    <div className="regulation-icon"><FileText size={19} /></div>
    <div className="regulation-copy">
      <span className="regulation-meta">{regulation.type} · {regulation.number} · {regulation.topic}</span>
      <h2>{regulation.title}</h2>
      <span className="published-tag"><Check size={12} /> {t('common.published')}</span>
    </div>
    <a className="outline-link" href={regulation.source_url} target="_blank" rel="noreferrer">{t('common.originalSource')} <ArrowUpRight size={14} /></a>
  </article>
}
