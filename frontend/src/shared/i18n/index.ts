import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { resources } from './resources'

const LANGUAGE_STORAGE_KEY = 'taxora-language'
const storedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY)
const initialLanguage = storedLanguage === 'id' ? 'id' : 'en'

void i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage,
  fallbackLng: 'en',
  supportedLngs: ['en', 'id'],
  interpolation: { escapeValue: false },
  returnNull: false,
})

i18n.on('languageChanged', language => {
  const normalizedLanguage = language === 'id' ? 'id' : 'en'
  localStorage.setItem(LANGUAGE_STORAGE_KEY, normalizedLanguage)
  document.documentElement.lang = normalizedLanguage
  document.title = i18n.t('common.documentTitle')
})

document.documentElement.lang = initialLanguage
document.title = i18n.t('common.documentTitle')

export default i18n
