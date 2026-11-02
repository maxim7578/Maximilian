import { usePage } from '@inertiajs/react'
import { useTranslation } from 'react-i18next'

/** Name the server sends when no custom name is set (see app/utils/assistant_name.ts). */
const SERVER_DEFAULT_NAME = 'AI Assistant'

/**
 * Display name of the AI assistant. A name the user chose is shown as is;
 * the server's built-in default is shown in the current UI language.
 */
export default function useAssistantName(): string {
  const { t } = useTranslation()
  const name = usePage<{ aiAssistantName?: string }>().props?.aiAssistantName?.trim()
  return !name || name === SERVER_DEFAULT_NAME ? t('common:assistant.defaultName') : name
}
