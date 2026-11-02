import { IconLanguage } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { SUPPORTED_LANGUAGES, setLanguage, type Language } from '~/i18n'
import classNames from '~/lib/classNames'

/** Compact DE | EN switch shown next to the theme toggle. */
export default function LanguageSwitcher() {
  const { t, i18n } = useTranslation()
  const current = i18n.resolvedLanguage
  const names: Record<Language, string> = {
    de: t('common:language.names.de'),
    en: t('common:language.names.en'),
  }

  return (
    <div
      role="group"
      aria-label={t('common:language.label')}
      className="flex items-center gap-1 text-sm text-desert-stone"
    >
      <IconLanguage className="size-4" aria-hidden="true" />
      {SUPPORTED_LANGUAGES.map((language, index) => (
        <span key={language} className="flex items-center gap-1">
          {index > 0 && <span aria-hidden="true">|</span>}
          <button
            type="button"
            lang={language}
            onClick={() => setLanguage(language)}
            aria-pressed={current === language}
            title={t('common:language.switchTo', { language: names[language] })}
            className={classNames(
              'rounded px-1 cursor-pointer transition-colors hover:text-desert-green-darker',
              current === language ? 'font-semibold text-desert-green-darker' : ''
            )}
          >
            {language.toUpperCase()}
          </button>
        </span>
      ))}
    </div>
  )
}
