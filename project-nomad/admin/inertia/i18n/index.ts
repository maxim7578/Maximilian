import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import {
  FALLBACK_LANGUAGE,
  LANGUAGE_STORAGE_KEY,
  SUPPORTED_LANGUAGES,
  isSupportedLanguage,
  localeFor,
  pickLanguage,
  type Language,
} from './language'

export { SUPPORTED_LANGUAGES, type Language }

/**
 * UI translations live in inertia/locales/<language>/<namespace>.json and are
 * bundled here, so adding a namespace only means adding the two JSON files.
 * Keys are always written with their namespace prefix, e.g. "settings:system.title".
 */
const modules = import.meta.glob<{ default: Record<string, unknown> }>('../locales/*/*.json', {
  eager: true,
})

const resources: Record<string, Record<string, Record<string, unknown>>> = {}
for (const [path, module] of Object.entries(modules)) {
  const match = path.match(/locales\/([^/]+)\/([^/]+)\.json$/)
  if (!match) continue
  const [, language, namespace] = match
  resources[language] ??= {}
  resources[language][namespace] = module.default
}

function readStoredLanguage(): string | null {
  try {
    return localStorage.getItem(LANGUAGE_STORAGE_KEY)
  } catch {
    return null
  }
}

function applyLanguage(language: string) {
  document.documentElement.lang = language
}

const initialLanguage = pickLanguage(readStoredLanguage(), navigator.languages ?? [navigator.language])

i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage,
  fallbackLng: FALLBACK_LANGUAGE,
  supportedLngs: [...SUPPORTED_LANGUAGES],
  defaultNS: 'common',
  ns: Object.keys(resources[FALLBACK_LANGUAGE] ?? {}),
  interpolation: {
    // React already escapes rendered values
    escapeValue: false,
  },
  returnNull: false,
})

applyLanguage(initialLanguage)
i18n.on('languageChanged', applyLanguage)

/** Switches the UI language and remembers the choice in this browser. */
export function setLanguage(language: Language) {
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
  } catch {}
  void i18n.changeLanguage(language)
}

export function currentLanguage(): Language {
  const language = i18n.resolvedLanguage ?? i18n.language
  return isSupportedLanguage(language) ? language : FALLBACK_LANGUAGE
}

/** Formats a number for the current UI language (replaces toLocaleString()). */
export function formatNumber(value: number, options?: Intl.NumberFormatOptions): string {
  return new Intl.NumberFormat(localeFor(currentLanguage()), options).format(value)
}

/** Formats a date for the current UI language (replaces toLocaleDateString()). */
export function formatDate(
  value: Date | string | number,
  options: Intl.DateTimeFormatOptions = { dateStyle: 'medium' }
): string {
  return new Intl.DateTimeFormat(localeFor(currentLanguage()), options).format(new Date(value))
}

/** Formats date and time for the current UI language (replaces Date#toLocaleString()). */
export function formatDateTime(
  value: Date | string | number,
  options: Intl.DateTimeFormatOptions = { dateStyle: 'medium', timeStyle: 'short' }
): string {
  return new Intl.DateTimeFormat(localeFor(currentLanguage()), options).format(new Date(value))
}

export default i18n
