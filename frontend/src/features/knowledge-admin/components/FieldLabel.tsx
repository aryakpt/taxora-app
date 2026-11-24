import { useTranslation } from 'react-i18next'
import { InfoTooltip } from '../../../shared/components/InfoTooltip'

export type HelpKey = 'sourceMode' | 'sourceUrl' | 'file' | 'regulationType' | 'regulationNumber' | 'title' | 'issuer'
  | 'topic' | 'issuedAt' | 'effectiveFrom' | 'effectiveUntil'

/** A form field's label text with its explanation (admin.help.*) behind a "?" tooltip. */
export function FieldLabel({ text, help }: { text: string, help: HelpKey }) {
  const { t } = useTranslation()
  return <span className="field-label">{text}<InfoTooltip label={text}>{t(`admin.help.${help}`)}</InfoTooltip></span>
}
