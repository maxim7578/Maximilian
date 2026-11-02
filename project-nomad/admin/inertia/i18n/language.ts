/**
 * Pure language helpers for the UI translations. Kept free of browser and
 * i18next imports so the selection logic can be unit tested in Node.
 */

export const SUPPORTED_LANGUAGES = ['de', 'en'] as const
export type Language = (typeof SUPPORTED_LANGUAGES)[number]

export const FALLBACK_LANGUAGE: Language = 'en'
export const LANGUAGE_STORAGE_KEY = 'nomad:language'

const LOCALES: Record<Language, string> = {
  de: 'de-DE',
  en: 'en-US',
}

export function isSupportedLanguage(value: unknown): value is Language {
  return typeof value === 'string' && (SUPPORTED_LANGUAGES as readonly string[]).includes(value)
}

/**
 * A language the user picked before wins. Otherwise the first browser language
 * NOMAD supports is used (e.g. "de-AT" -> "de"), falling back to English.
 */
export function pickLanguage(
  stored: string | null | undefined,
  browserLanguages: readonly string[]
): Language {
  if (isSupportedLanguage(stored)) return stored
  for (const browserLanguage of browserLanguages) {
    const base = browserLanguage.toLowerCase().split('-')[0]
    if (isSupportedLanguage(base)) return base
  }
  return FALLBACK_LANGUAGE
}

/** BCP 47 locale used for number and date formatting in the given language. */
export function localeFor(language: Language): string {
  return LOCALES[language]
}

/**
 * Marks a translation key in code that must stay importable in Node (modules
 * covered by unit tests cannot import i18next or Vite-only code). It returns the
 * key unchanged; the React component renders it with t(key). The locale test
 * checks keys marked this way like any other namespaced key in a t() call.
 */
export function tk<Key extends string>(key: Key): Key {
  return key
}
