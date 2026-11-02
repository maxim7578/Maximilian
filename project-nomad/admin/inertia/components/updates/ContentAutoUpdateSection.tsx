import { useEffect, useState } from 'react'
import StyledButton from '~/components/StyledButton'
import StyledSectionHeader from '~/components/StyledSectionHeader'
import Alert from '~/components/Alert'
import api from '~/lib/api'
import Input from '~/components/inputs/Input'
import Switch from '~/components/inputs/Switch'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNotifications } from '~/context/NotificationContext'
import { useContentAutoUpdateStatus } from '~/hooks/useContentAutoUpdateStatus'
import { formatBytes } from '~/lib/util'
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

const BYTES_PER_GB = 1024 * 1024 * 1024

export default function ContentAutoUpdateSection() {
  const { t } = useTranslation()
  const { addNotification } = useNotifications()
  const queryClient = useQueryClient()
  const { data: status, isLoading } = useContentAutoUpdateStatus()

  const [windowStart, setWindowStart] = useState('02:00')
  const [windowEnd, setWindowEnd] = useState('05:00')
  const [cooloff, setCooloff] = useState(72)
  // Data cap is stored in bytes but edited in GB (0 = unlimited).
  const [capGb, setCapGb] = useState('0')

  // Seed editable fields once the persisted status loads.
  useEffect(() => {
    if (status) {
      setWindowStart(status.windowStart)
      setWindowEnd(status.windowEnd)
      setCooloff(status.cooloffHours)
      setCapGb(
        status.maxBytesPerWindow > 0
          ? String(Math.round((status.maxBytesPerWindow / BYTES_PER_GB) * 100) / 100)
          : '0'
      )
    }
  }, [status?.windowStart, status?.windowEnd, status?.cooloffHours, status?.maxBytesPerWindow])

  const enabled = status?.enabled ?? false
  const autoDisabled = !!status?.autoDisabledReason

  const toggleMutation = useMutation({
    mutationFn: (value: boolean) => api.updateSetting('contentAutoUpdate.enabled', value),
    onSuccess: (_data, value) => {
      queryClient.invalidateQueries({ queryKey: ['content-auto-update-status'] })
      addNotification({
        type: 'success',
        message: value
          ? t('updates:contentAutoUpdate.enabledNotification')
          : t('updates:contentAutoUpdate.disabledNotification'),
      })
    },
    onError: () => {
      addNotification({ type: 'error', message: t('updates:contentAutoUpdate.toggleError') })
    },
  })

  const handleSaveSchedule = async () => {
    const parsedGb = Number(capGb)
    if (!Number.isFinite(parsedGb) || parsedGb < 0) {
      addNotification({ type: 'error', message: t('updates:contentAutoUpdate.invalidDataCap') })
      return
    }
    const capBytes = Math.round(parsedGb * BYTES_PER_GB)
    try {
      await api.updateSetting('contentAutoUpdate.windowStart', windowStart)
      await api.updateSetting('contentAutoUpdate.windowEnd', windowEnd)
      await api.updateSetting('contentAutoUpdate.cooloffHours', String(cooloff))
      await api.updateSetting('contentAutoUpdate.maxBytesPerWindow', String(capBytes))
      queryClient.invalidateQueries({ queryKey: ['content-auto-update-status'] })
      addNotification({ type: 'success', message: t('updates:contentAutoUpdate.scheduleSaved') })
    } catch {
      addNotification({ type: 'error', message: t('updates:contentAutoUpdate.scheduleSaveError') })
    }
  }

  return (
    <>
      <StyledSectionHeader title={t('updates:contentAutoUpdate.title')} className="mt-8" />
      <div className="bg-surface-primary rounded-lg border shadow-md overflow-hidden mt-6 p-6">
        {autoDisabled && (
          <Alert
            type="warning"
            title={t('updates:contentAutoUpdate.autoDisabledTitle')}
            message={
              status?.autoDisabledReason ||
              t('updates:contentAutoUpdate.autoDisabledFallback')
            }
            variant="bordered"
            className="mb-4"
          />
        )}

        <Switch
          checked={enabled}
          onChange={(value) => toggleMutation.mutate(value)}
          disabled={toggleMutation.isPending || isLoading}
          label={t('updates:contentAutoUpdate.enableLabel')}
          description={t('updates:contentAutoUpdate.enableDescription')}
        />

        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Input
            name="contentWindowStart"
            label={t('updates:schedule.windowStart')}
            type="time"
            value={windowStart}
            onChange={(e) => setWindowStart(e.target.value)}
            disabled={!enabled}
            helpText={t('updates:schedule.localServerTime')}
          />
          <Input
            name="contentWindowEnd"
            label={t('updates:schedule.windowEnd')}
            type="time"
            value={windowEnd}
            onChange={(e) => setWindowEnd(e.target.value)}
            disabled={!enabled}
            helpText={t('updates:schedule.localServerTime')}
          />
          <div>
            <label
              htmlFor="contentCooloff"
              className="block text-base/6 font-medium text-text-primary"
            >
              {t('updates:schedule.cooloffPeriod')}
            </label>
            <p className="mt-1 text-sm text-text-muted">{t('updates:contentAutoUpdate.cooloffHelp')}</p>
            <select
              id="contentCooloff"
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
          <Input
            name="contentDataCap"
            label={t('updates:contentAutoUpdate.dataCapLabel')}
            type="number"
            min="0"
            step="1"
            value={capGb}
            onChange={(e) => setCapGb(e.target.value)}
            disabled={!enabled}
            helpText={t('updates:contentAutoUpdate.dataCapHelp')}
          />
        </div>

        <div className="mt-4 flex justify-end">
          <StyledButton variant="primary" size="sm" onClick={handleSaveSchedule} disabled={!enabled}>
            {t('updates:schedule.saveSchedule')}
          </StyledButton>
        </div>

        {enabled && status && (
          <div className="mt-6 pt-4 border-t border-desert-stone-light text-sm">
            <p className="text-desert-stone mb-3">
              <span className="font-medium">{t('updates:schedule.updateWindowLabel')} </span>
              {t('updates:contentAutoUpdate.windowSummary', {
                start: status.windowStart,
                end: status.windowEnd,
                state: status.withinWindow
                  ? t('updates:contentAutoUpdate.currentlyInside')
                  : t('updates:contentAutoUpdate.currentlyOutside'),
                hours: status.cooloffHours,
                cap:
                  status.maxBytesPerWindow > 0
                    ? formatBytes(status.maxBytesPerWindow)
                    : t('updates:contentAutoUpdate.unlimited'),
                usage:
                  status.maxBytesPerWindow > 0
                    ? t('updates:contentAutoUpdate.usedThisWindow', {
                        used: formatBytes(status.windowBytesUsed),
                      })
                    : '',
              })}
              {status.lastResult && (
                <>
                  {' '}
                  <span className="font-medium">{t('updates:schedule.lastRunLabel')} </span>
                  {status.lastResult}
                  {status.lastAttemptAt
                    ? ` (${formatDateTime(status.lastAttemptAt)})`
                    : ''}
                </>
              )}
            </p>

            {status.lastError && (
              <p className="text-desert-red mb-3">
                <span className="font-medium">{t('updates:schedule.lastErrorLabel')} </span>
                {status.lastError}
              </p>
            )}

            {status.resources.length === 0 ? (
              <p className="text-desert-stone-dark">
                {t('updates:contentAutoUpdate.allUpToDate')}
              </p>
            ) : (
              <ul className="space-y-2">
                {status.resources.map((resource) => (
                  <li
                    key={`${resource.resource_type}:${resource.resource_id}`}
                    className="flex items-start justify-between gap-4 rounded-md bg-surface-secondary px-3 py-2"
                  >
                    <div>
                      <p className="font-medium text-text-primary">
                        {resource.resource_id}{' '}
                        <span className="text-xs uppercase text-desert-stone">
                          {resource.resource_type}
                        </span>
                      </p>
                      <p className="text-desert-stone">
                        {resource.current_version}
                        {resource.available_update_version
                          ? ` → ${resource.available_update_version}`
                          : ` (${t('updates:schedule.upToDate')})`}
                        {resource.size_bytes ? ` · ${formatBytes(resource.size_bytes)}` : ''}
                      </p>
                      {resource.auto_disabled_reason && (
                        <p className="text-desert-red mt-0.5">{resource.auto_disabled_reason}</p>
                      )}
                    </div>
                    <span
                      className={`shrink-0 text-xs font-medium ${resource.exceeds_cap
                          ? 'text-desert-red'
                          : resource.eligible
                            ? 'text-desert-green'
                            : 'text-desert-stone'
                        }`}
                    >
                      {resource.exceeds_cap ? t('updates:contentAutoUpdate.skippedExceedsCap') : resource.reason}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </>
  )
}
