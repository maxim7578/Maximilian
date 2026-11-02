import { useEffect, useState } from 'react'
import StyledButton from '~/components/StyledButton'
import StyledSectionHeader from '~/components/StyledSectionHeader'
import Alert from '~/components/Alert'
import api from '~/lib/api'
import Input from '~/components/inputs/Input'
import Switch from '~/components/inputs/Switch'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNotifications } from '~/context/NotificationContext'
import { useAutoUpdateStatus } from '~/hooks/useAutoUpdateStatus'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { formatDateTime } from '~/i18n'

function cooloffOptions(t: TFunction) {
  return [
    { value: 24, label: t('updates:schedule.cooloff24') },
    { value: 48, label: t('updates:schedule.cooloff48') },
    { value: 72, label: t('updates:schedule.cooloff72') },
    { value: 168, label: t('updates:schedule.cooloff168') },
  ]
}

export default function CoreAutoUpdateSection() {
  const { t } = useTranslation()
  const { addNotification } = useNotifications()
  const queryClient = useQueryClient()
  const { data: status, isLoading } = useAutoUpdateStatus()

  const [windowStart, setWindowStart] = useState('02:00')
  const [windowEnd, setWindowEnd] = useState('05:00')
  const [cooloff, setCooloff] = useState(72)

  // Seed editable fields once the persisted status loads.
  useEffect(() => {
    if (status) {
      setWindowStart(status.windowStart)
      setWindowEnd(status.windowEnd)
      setCooloff(status.cooloffHours)
    }
  }, [status?.windowStart, status?.windowEnd, status?.cooloffHours])

  const saveMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: any }) => api.updateSetting(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auto-update-status'] })
    },
    onError: () => {
      addNotification({ type: 'error', message: t('updates:coreAutoUpdate.toggleError') })
    },
  })

  const enabled = status?.enabled ?? false
  const autoDisabled = !!status?.autoDisabledReason

  const handleToggle = (value: boolean) => {
    saveMutation.mutate(
      { key: 'autoUpdate.enabled', value },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: ['auto-update-status'] })
          addNotification({
            type: 'success',
            message: value ? t('updates:coreAutoUpdate.enabledNotification') : t('updates:coreAutoUpdate.disabledNotification'),
          })
        },
      }
    )
  }

  const handleSaveWindow = async () => {
    try {
      await api.updateSetting('autoUpdate.windowStart', windowStart)
      await api.updateSetting('autoUpdate.windowEnd', windowEnd)
      await api.updateSetting('autoUpdate.cooloffHours', String(cooloff))
      queryClient.invalidateQueries({ queryKey: ['auto-update-status'] })
      addNotification({ type: 'success', message: t('updates:coreAutoUpdate.scheduleSaved') })
    } catch {
      addNotification({ type: 'error', message: t('updates:coreAutoUpdate.scheduleSaveError') })
    }
  }

  return (
    <>
      <StyledSectionHeader title={t('updates:coreAutoUpdate.title')} className="mt-8" />
      <div className="bg-surface-primary rounded-lg border shadow-md overflow-hidden mt-6 p-6">
        {autoDisabled && (
          <Alert
            type="warning"
            title={t('updates:coreAutoUpdate.autoDisabledTitle')}
            message={status?.autoDisabledReason || t('updates:coreAutoUpdate.autoDisabledFallback')}
            variant="bordered"
            className="mb-4"
          />
        )}

        <Switch
          checked={enabled}
          onChange={handleToggle}
          disabled={saveMutation.isPending || isLoading}
          label={t('updates:coreAutoUpdate.enableLabel')}
          description={t('updates:coreAutoUpdate.enableDescription')}
        />

        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <Input
            name="autoUpdateWindowStart"
            label={t('updates:schedule.windowStart')}
            type="time"
            value={windowStart}
            onChange={(e) => setWindowStart(e.target.value)}
            disabled={!enabled}
            helpText={t('updates:schedule.localServerTime')}
          />
          <Input
            name="autoUpdateWindowEnd"
            label={t('updates:schedule.windowEnd')}
            type="time"
            value={windowEnd}
            onChange={(e) => setWindowEnd(e.target.value)}
            disabled={!enabled}
            helpText={t('updates:schedule.localServerTime')}
          />
          <div>
            <label
              htmlFor="autoUpdateCooloff"
              className="block text-base/6 font-medium text-text-primary"
            >
              {t('updates:schedule.cooloffPeriod')}
            </label>
            <p className="mt-1 text-sm text-text-muted">{t('updates:coreAutoUpdate.cooloffHelp')}</p>
            <select
              id="autoUpdateCooloff"
              value={cooloff}
              onChange={(e) => setCooloff(Number(e.target.value))}
              disabled={!enabled}
              className="mt-1.5 block w-full rounded-md bg-surface-primary px-3 py-2 text-base text-text-primary border border-border-default focus:outline focus:outline-2 focus:-outline-offset-2 focus:outline-primary sm:text-sm/6 disabled:opacity-50"
            >
              {cooloffOptions(t).map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <StyledButton
            variant="primary"
            size="sm"
            onClick={handleSaveWindow}
            disabled={!enabled}
          >
            {t('updates:schedule.saveSchedule')}
          </StyledButton>
        </div>

        {enabled && status && (
          <div className="mt-6 pt-4 border-t border-desert-stone-light text-sm space-y-1">
            <p className="text-desert-stone-dark">
              <span className="font-medium">{t('updates:coreAutoUpdate.statusLabel')} </span>
              {status.eligibleTarget
                ? t('updates:coreAutoUpdate.eligibleReady', { version: status.eligibleTarget.version })
                : t('updates:coreAutoUpdate.noEligible')}
            </p>
            <p className="text-desert-stone">
              <span className="font-medium">{t('updates:schedule.updateWindowLabel')} </span>
              {status.withinWindow ? t('updates:coreAutoUpdate.insideWindow') : t('updates:coreAutoUpdate.outsideWindow')}
            </p>
            {status.lastResult && (
              <p className="text-desert-stone">
                <span className="font-medium">{t('updates:coreAutoUpdate.lastCheckLabel')} </span>
                {status.lastResult}
                {status.lastAttemptAt
                  ? ` (${formatDateTime(status.lastAttemptAt)})`
                  : ''}
              </p>
            )}
            {status.lastError && (
              <p className="text-desert-red">
                <span className="font-medium">{t('updates:schedule.lastErrorLabel')} </span>
                {status.lastError}
              </p>
            )}
          </div>
        )}
      </div>
    </>
  )
}
