import { IconSun, IconMoon } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { useThemeContext } from '~/providers/ThemeProvider'

interface ThemeToggleProps {
  compact?: boolean
}

export default function ThemeToggle({ compact = false }: ThemeToggleProps) {
  const { t } = useTranslation()
  const { theme, toggleTheme } = useThemeContext()
  const isDark = theme === 'dark'
  const label = isDark ? t('common:theme.switchToDay') : t('common:theme.switchToNight')

  return (
    <button
      onClick={toggleTheme}
      className="flex items-center gap-1.5 rounded-md px-2 py-1 text-sm transition-colors
                 text-desert-stone hover:text-desert-green-darker cursor-pointer"
      aria-label={label}
      title={label}
    >
      {isDark ? <IconSun className="size-4" /> : <IconMoon className="size-4" />}
      {!compact && <span>{isDark ? t('common:theme.day') : t('common:theme.night')}</span>}
    </button>
  )
}
