import { Head } from '@inertiajs/react'
import SettingsLayout from '~/layouts/SettingsLayout'
import StyledButton from '~/components/StyledButton'
import StyledSectionHeader from '~/components/StyledSectionHeader'
import Alert from '~/components/Alert'
import { useEffect, useRef, useState } from 'react'
import { IconAlertCircle, IconArrowBigUpLines, IconCheck, IconCircleCheck, IconReload } from '@tabler/icons-react'
import { SystemUpdateStatus } from '../../../types/system'
import api from '~/lib/api'
import Input from '~/components/inputs/Input'
import Switch from '~/components/inputs/Switch'
import { useMutation } from '@tanstack/react-query'
import { useNotifications } from '~/context/NotificationContext'
import { useSystemSetting } from '~/hooks/useSystemSetting'
import CoreAutoUpdateSection from '~/components/updates/CoreAutoUpdateSection'
import AppAutoUpdateSection from '~/components/updates/AppAutoUpdateSection'
import ContentAutoUpdateSection from '~/components/updates/ContentAutoUpdateSection'
import ContentUpdatesSection from '~/components/updates/ContentUpdatesSection'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'

type Props = {
  updateAvailable: boolean
  latestVersion: string
  currentVersion: string
  earlyAccess: boolean
}

function stageLabels(t: TFunction): Record<SystemUpdateStatus['stage'], string> {
  return {
    idle: t('updates:updatePage.stages.idle'),
    starting: t('updates:updatePage.stages.starting'),
    pulling: t('updates:updatePage.stages.pulling'),
    pulled: t('updates:updatePage.stages.pulled'),
    recreating: t('updates:updatePage.stages.recreating'),
    complete: t('updates:updatePage.stages.complete'),
    error: t('updates:updatePage.stages.error'),
  }
}

const ADVANCED_STAGES: ReadonlySet<SystemUpdateStatus['stage']> = new Set([
  'pulling',
  'pulled',
  'recreating',
  'complete',
])

export default function SystemUpdatePage(props: { system: Props }) {
  const { t } = useTranslation()
  const { addNotification } = useNotifications()

  const [isUpdating, setIsUpdating] = useState(false)
  const [updateStatus, setUpdateStatus] = useState<SystemUpdateStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showLogs, setShowLogs] = useState(false)
  const [logs, setLogs] = useState<string>('')
  const [email, setEmail] = useState('')
  const [versionInfo, setVersionInfo] = useState<Omit<Props, 'earlyAccess'>>(props.system)
  const [showConnectionLostNotice, setShowConnectionLostNotice] = useState(false)
  // Tracks whether this update session has progressed past 'idle'/'starting'.
  // The sidecar sits on 'complete' for ~5s before resetting to 'idle' (see
  // install/sidecar-updater/update-watcher.sh), and the SPA can miss that
  // window across the admin container restart. If we resurface to 'idle'
  // after seeing an advanced stage, treat it as the missed completion.
  const seenAdvancedStageRef = useRef(false)

  const earlyAccessSetting = useSystemSetting({
    key: 'system.earlyAccess', initialData: {
      key: 'system.earlyAccess',
      value: props.system.earlyAccess,
    }
  })

  useEffect(() => {
    if (!isUpdating) return

    const interval = setInterval(async () => {
      try {
        const response = await api.getSystemUpdateStatus()
        if (!response) {
          throw new Error('Failed to fetch update status')
        }
        setUpdateStatus(response)

        if (ADVANCED_STAGES.has(response.stage)) {
          seenAdvancedStageRef.current = true
        }

        // If we can connect again, hide the connection lost notice
        setShowConnectionLostNotice(false)

        // Check if update is complete or errored. We also treat a return to
        // 'idle' as completion if we previously saw an advanced stage — this
        // catches the race where the sidecar's brief 'complete' window passes
        // while we're disconnected during the admin container restart.
        const isComplete =
          response.stage === 'complete' ||
          (response.stage === 'idle' && seenAdvancedStageRef.current)

        if (isComplete) {
          // Re-check version so the KV store clears the stale "update available" flag
          // before we reload, otherwise the banner shows "current → current"
          try {
            await api.checkLatestVersion(true)
          } catch {
            // Non-critical - page reload will still work
          }
          setTimeout(() => {
            window.location.reload()
          }, 2000)
        } else if (response.stage === 'error') {
          setIsUpdating(false)
          setError(response.message)
        }
      } catch (err) {
        // During container restart, we'll lose connection - this is expected
        // Show a notice to inform the user that this is normal
        setShowConnectionLostNotice(true)
        // Continue polling to detect when the container comes back up
        console.log('Polling update status (container may be restarting)...')
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [isUpdating])

  const handleStartUpdate = async () => {
    try {
      setError(null)
      seenAdvancedStageRef.current = false
      setIsUpdating(true)
      const response = await api.startSystemUpdate()
      if (!response || !response.success) {
        throw new Error(t('updates:updatePage.failedToStart'))
      }
    } catch (err: any) {
      setIsUpdating(false)
      setError(err.response?.data?.error || err.message || t('updates:updatePage.failedToStart'))
    }
  }

  const handleViewLogs = async () => {
    try {
      const response = await api.getSystemUpdateLogs()
      if (!response) {
        throw new Error(t('updates:updatePage.failedToFetchLogs'))
      }
      setLogs(response.logs)
      setShowLogs(true)
    } catch (err) {
      setError(t('updates:updatePage.failedToFetchLogs'))
    }
  }

  const checkVersionMutation = useMutation({
    mutationKey: ['checkLatestVersion'],
    mutationFn: () => api.checkLatestVersion(true),
    onSuccess: (data) => {
      if (data) {
        setVersionInfo({
          updateAvailable: data.updateAvailable,
          latestVersion: data.latestVersion,
          currentVersion: data.currentVersion,
        })
        if (data.updateAvailable) {
          addNotification({
            type: 'success',
            message: t('updates:updatePage.updateAvailableNotification', { version: data.latestVersion }),
          })
        } else {
          addNotification({ type: 'success', message: t('updates:updatePage.systemUpToDateNotification') })
        }
        setError(null)
      }
    },
    onError: (error: any) => {
      const errorMessage = error?.message || t('updates:updatePage.failedToCheck')
      setError(errorMessage)
      addNotification({ type: 'error', message: errorMessage })
    },
  })

  const getProgressBarColor = () => {
    if (updateStatus?.stage === 'error') return 'bg-desert-red'
    if (updateStatus?.stage === 'complete') return 'bg-desert-olive'
    return 'bg-desert-green'
  }

  const getStatusIcon = () => {
    if (updateStatus?.stage === 'complete')
      return <IconCheck className="h-12 w-12 text-desert-olive" />
    if (updateStatus?.stage === 'error')
      return <IconAlertCircle className="h-12 w-12 text-desert-red" />
    if (isUpdating) return <IconReload className="h-12 w-12 text-desert-green animate-spin" />
    if (versionInfo.updateAvailable)
      return <IconArrowBigUpLines className="h-16 w-16 text-desert-green" />
    return <IconCircleCheck className="h-16 w-16 text-desert-olive" />
  }

  const updateSettingMutation = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: boolean }) => {
      return await api.updateSetting(key, value)
    },
    onSuccess: () => {
      addNotification({ message: t('updates:updatePage.settingUpdated'), type: 'success' })
      earlyAccessSetting.refetch()
      // Toggling Early Access changes which versions are eligible, so re-evaluate
      // immediately rather than making the user click Check Again.
      checkVersionMutation.mutate()
    },
    onError: (error) => {
      console.error('Error updating setting:', error)
      addNotification({ message: t('updates:updatePage.settingUpdateError'), type: 'error' })
    },
  })

  const subscribeToReleaseNotesMutation = useMutation({
    mutationKey: ['subscribeToReleaseNotes'],
    mutationFn: (email: string) => api.subscribeToReleaseNotes(email),
    onSuccess: (data) => {
      if (data && data.success) {
        addNotification({ type: 'success', message: t('updates:updatePage.subscribed') })
        setEmail('')
      } else {
        addNotification({
          type: 'error',
          message: t('updates:updatePage.subscribeFailed', { error: data?.message || t('updates:updatePage.unknownError') }),
        })
      }
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        message: t('updates:updatePage.subscribeError', { error: error.message || t('updates:updatePage.unknownError') }),
      })
    },
  })

  return (
    <SettingsLayout>
      <Head title={t('updates:updatePage.title')} />
      <div className="xl:pl-72 w-full">
        <main className="px-6 lg:px-12 py-6 lg:py-8">
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-desert-green mb-2">{t('updates:updatePage.title')}</h1>
            <p className="text-desert-stone-dark">
              {t('updates:updatePage.subtitle')}
            </p>
          </div>

          {error && (
            <div className="mb-6">
              <Alert
                type="error"
                title={t('updates:updatePage.stages.error')}
                message={error}
                variant="bordered"
                dismissible
                onDismiss={() => setError(null)}
              />
            </div>
          )}
          {isUpdating && updateStatus?.stage === 'recreating' && (
            <div className="mb-6">
              <Alert
                type="info"
                title={t('updates:updatePage.containerRestartingTitle')}
                message={t('updates:updatePage.containerRestartingMessage')}
                variant="solid"
              />
            </div>
          )}
          {isUpdating && showConnectionLostNotice && (
            <div className="mb-6">
              <Alert
                type="info"
                title={t('updates:updatePage.connectionLostTitle')}
                message={t('updates:updatePage.connectionLostMessage')}
                variant="solid"
              />
            </div>
          )}
          <div className="bg-surface-primary rounded-lg border shadow-md overflow-hidden">
            <div className="p-8 text-center">
              <div className="flex justify-center mb-4">{getStatusIcon()}</div>

              {!isUpdating && (
                <>
                  <h2 className="text-2xl font-bold text-desert-green mb-2">
                    {versionInfo.updateAvailable ? t('updates:updatePage.updateAvailable') : t('updates:updatePage.systemUpToDate')}
                  </h2>
                  <p className="text-desert-stone-dark mb-6">
                    {versionInfo.updateAvailable
                      ? t('updates:updatePage.newVersionAvailable', { version: versionInfo.latestVersion })
                      : t('updates:updatePage.runningLatest')}
                  </p>
                </>
              )}

              {isUpdating && updateStatus && (
                <>
                  <h2 className="text-2xl font-bold text-desert-green mb-2">
                    {stageLabels(t)[updateStatus.stage] ?? updateStatus.stage}
                  </h2>
                  <p className="text-desert-stone-dark mb-6">{updateStatus.message}</p>
                </>
              )}

              <div className="flex justify-center gap-8 mb-6">
                <div className="text-center">
                  <p className="text-sm text-desert-stone mb-1">{t('updates:updatePage.currentVersion')}</p>
                  <p className="text-xl font-bold text-desert-green">
                    {versionInfo.currentVersion}
                  </p>
                </div>
                {versionInfo.updateAvailable && (
                  <>
                    <div className="flex items-center">
                      <svg
                        className="h-6 w-6 text-desert-stone"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M13 7l5 5m0 0l-5 5m5-5H6"
                        />
                      </svg>
                    </div>
                    <div className="text-center">
                      <p className="text-sm text-desert-stone mb-1">{t('updates:updatePage.latestVersion')}</p>
                      <p className="text-xl font-bold text-desert-olive">
                        {versionInfo.latestVersion}
                      </p>
                    </div>
                  </>
                )}
              </div>
              {isUpdating && updateStatus && (
                <div className="mb-4">
                  <div className="w-full bg-desert-stone-light rounded-full h-3 overflow-hidden">
                    <div
                      className={`${getProgressBarColor()} h-full transition-all duration-500 ease-out`}
                      style={{ width: `${updateStatus.progress}%` }}
                    />
                  </div>
                  <p className="text-sm text-desert-stone mt-2">
                    {t('updates:updatePage.progressComplete', { progress: updateStatus.progress })}
                  </p>
                </div>
              )}
              {!isUpdating && (
                <div className="flex justify-center gap-4">
                  <StyledButton
                    variant="primary"
                    size="lg"
                    icon="IconDownload"
                    onClick={handleStartUpdate}
                    disabled={!versionInfo.updateAvailable}
                  >
                    {versionInfo.updateAvailable ? t('updates:updatePage.startUpdate') : t('updates:updatePage.noUpdateAvailable')}
                  </StyledButton>
                  <StyledButton
                    variant="ghost"
                    size="lg"
                    icon="IconRefresh"
                    onClick={() => checkVersionMutation.mutate()}
                    loading={checkVersionMutation.isPending}
                  >
                    {t('updates:updatePage.checkAgain')}
                  </StyledButton>
                </div>
              )}
            </div>
            <div className="border-t bg-surface-primary p-6">
              <h3 className="text-lg font-semibold text-desert-green mb-4">
                {t('updates:updatePage.whatHappens')}
              </h3>
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-desert-green text-white flex items-center justify-center text-sm font-bold">
                    1
                  </div>
                  <div>
                    <p className="font-medium text-desert-stone-dark">{t('updates:updatePage.step1Title')}</p>
                    <p className="text-sm text-desert-stone">
                      {t('updates:updatePage.step1Description')}
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-desert-green text-white flex items-center justify-center text-sm font-bold">
                    2
                  </div>
                  <div>
                    <p className="font-medium text-desert-stone-dark">{t('updates:updatePage.step2Title')}</p>
                    <p className="text-sm text-desert-stone">
                      {t('updates:updatePage.step2Description')}
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-desert-green text-white flex items-center justify-center text-sm font-bold">
                    3
                  </div>
                  <div>
                    <p className="font-medium text-desert-stone-dark">{t('updates:updatePage.step3Title')}</p>
                    <p className="text-sm text-desert-stone">
                      {t('updates:updatePage.step3Description')}
                    </p>
                  </div>
                </div>
              </div>

              {isUpdating && (
                <div className="mt-6 pt-6 border-t border-desert-stone-light">
                  <StyledButton
                    variant="ghost"
                    size="sm"
                    icon="IconLogs"
                    onClick={handleViewLogs}
                    fullWidth
                  >
                    {t('updates:updatePage.viewLogs')}
                  </StyledButton>
                </div>
              )}
            </div>
          </div>
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <Alert
              type="info"
              title={t('updates:updatePage.backupReminderTitle')}
              message={t('updates:updatePage.backupReminderMessage')}
              variant="solid"
            />
            <Alert
              type="warning"
              title={t('updates:updatePage.downtimeTitle')}
              message={t('updates:updatePage.downtimeMessage')}
              variant="solid"
            />
          </div>
          <StyledSectionHeader title={t('updates:updatePage.earlyAccess')} className="mt-8" />
          <div className="bg-surface-primary rounded-lg border shadow-md overflow-hidden mt-6 p-6">
            <Switch
              checked={earlyAccessSetting.data?.value || false}
              onChange={(newVal) => {
                updateSettingMutation.mutate({ key: 'system.earlyAccess', value: newVal })
              }}
              disabled={updateSettingMutation.isPending}
              label={t('updates:updatePage.enableEarlyAccess')}
              description={t('updates:updatePage.earlyAccessDescription')}
            />
          </div>
          <CoreAutoUpdateSection />
          <AppAutoUpdateSection />
          <ContentAutoUpdateSection />
          <ContentUpdatesSection />
          <div className="bg-surface-primary rounded-lg border shadow-md overflow-hidden py-6 mt-12">
            <div className="flex flex-col md:flex-row justify-between items-center p-8 gap-y-8 md:gap-y-0 gap-x-8">
              <div>
                <h2 className="max-w-xl text-lg font-bold text-desert-green sm:text-xl lg:col-span-7">
                  {t('updates:updatePage.newsletterHeading')}
                </h2>
              </div>
              <div className="flex flex-col">
                <div className="flex gap-x-3">
                  <Input
                    name="email"
                    label=""
                    type="email"
                    placeholder={t('updates:updatePage.emailPlaceholder')}
                    disabled={false}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full"
                    containerClassName="!mt-0"
                  />
                  <StyledButton
                    variant="primary"
                    disabled={!email}
                    onClick={() => subscribeToReleaseNotesMutation.mutateAsync(email)}
                    loading={subscribeToReleaseNotesMutation.isPending}
                  >
                    {t('updates:updatePage.subscribe')}
                  </StyledButton>
                </div>
                <p className="mt-2 text-sm text-desert-stone-dark">
                  {t('updates:updatePage.privacyNote')}
                </p>
              </div>
            </div>
          </div>

          {showLogs && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
              <div className="bg-surface-primary rounded-lg shadow-2xl max-w-4xl w-full max-h-[80vh] flex flex-col">
                <div className="p-6 border-b border-desert-stone-light flex justify-between items-center">
                  <h3 className="text-xl font-bold text-desert-green">{t('updates:updatePage.updateLogs')}</h3>
                  <button
                    onClick={() => setShowLogs(false)}
                    className="text-desert-stone hover:text-desert-green transition-colors"
                  >
                    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
                <div className="p-6 overflow-auto flex-1">
                  <pre className="bg-black text-green-400 p-4 rounded text-xs font-mono whitespace-pre-wrap">
                    {logs || t('updates:updatePage.noLogsYet')}
                  </pre>
                </div>
                <div className="p-6 border-t border-desert-stone-light">
                  <StyledButton variant="secondary" onClick={() => setShowLogs(false)} fullWidth>
                    {t('updates:updatePage.close')}
                  </StyledButton>
                </div>
              </div>
            </div>
          )}
        </main>
      </div >
    </SettingsLayout >
  )
}
