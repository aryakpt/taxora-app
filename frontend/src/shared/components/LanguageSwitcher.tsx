import { useTranslation } from 'react-i18next'

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation()
  const language = i18n.resolvedLanguage === 'id' ? 'id' : 'en'

  return <label className="language-switcher">
    <span className="sr-only">{t('language.select')}</span>
    <select value={language} aria-label={t('language.select')} onChange={event => void i18n.changeLanguage(event.target.value)}>
      <option value="en">EN</option>
      <option value="id">ID</option>
    </select>
  </label>
}
