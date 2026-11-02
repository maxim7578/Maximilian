import { useState } from 'react'
import Alert from '~/components/Alert'
import StyledModal from '~/components/StyledModal'
import Input from '~/components/inputs/Input'
import { useNotifications } from '~/context/NotificationContext'
import { useModals } from '~/context/ModalContext'
import api from '~/lib/api'
import type { GpuHealthStatus } from '../../types/system'
import { useTranslation } from 'react-i18next'

const DISMISS_KEY = 'nomad:gpu-banner-dismissed'
const HSA_OVERRIDE_PATTERN = /^\d{1,2}\.\d{1,2}\.\d{1,2}$/

/**
 * Banner for gpuHealth.status === 'passthrough_failed'.
 *
 * NVIDIA, and AMD whose container differs from what a reinstall would create, get
 * the one-click reinstall. AMD whose container already matches gets an HSA override
 * prompt instead: reinstalling it rebuilds the same CPU-bound container (#1344).
 */
export default function GpuPassthroughAlert({
  gpuHealth,
  assistantName,
  className,
}: {
  gpuHealth: GpuHealthStatus | undefined
  assistantName: string
  className?: string
}) {
  const { t } = useTranslation()
  const { addNotification } = useNotifications()
  const { openModal, closeAllModals } = useModals()
  const [reinstalling, setReinstalling] = useState(false)
  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem(DISMISS_KEY) === 'true'
    } catch {
      return false
    }
  })

  if (gpuHealth?.status !== 'passthrough_failed' || dismissed) return null

  const isAmd = gpuHealth.gpuVendor === 'amd'
  const needsHsaOverride = isAmd && gpuHealth.amdReinstallWouldChange === false

  const handleDismiss = () => {
    setDismissed(true)
    try {
      localStorage.setItem(DISMISS_KEY, 'true')
    } catch {}
  }

  const reinstall = async () => {
    setReinstalling(true)
    try {
      const response = await api.forceReinstallService('nomad_ollama')
      if (!response || !response.success) {
        throw new Error(response?.message || t('apps:gpuAlert.forceReinstallFailed'))
      }
      addNotification({
        message: t('apps:gpuAlert.reinstalling', { name: assistantName }),
        type: 'success',
      })
      try {
        localStorage.removeItem(DISMISS_KEY)
      } catch {}
      setTimeout(() => window.location.reload(), 5000)
    } catch (error) {
      addNotification({
        message: t('apps:gpuAlert.reinstallFailed', {
          message: error instanceof Error ? error.message : t('apps:status.unknownError'),
        }),
        type: 'error',
      })
      setReinstalling(false)
    }
  }

  const openReinstallModal = () => {
    openModal(
      <StyledModal
        title={t('apps:gpuAlert.reinstallTitle', { name: assistantName })}
        onConfirm={() => {
          closeAllModals()
          reinstall()
        }}
        onCancel={closeAllModals}
        open={true}
        confirmText={t('apps:actions.reinstall')}
        cancelText={t('apps:actions.cancel')}
      >
        <p className="text-text-primary">
          {t('apps:gpuAlert.reinstallBody', { name: assistantName })}
        </p>
      </StyledModal>,
      'gpu-health-force-reinstall-modal'
    )
  }

  const openHsaOverrideModal = () => {
    openModal(
      <HsaOverrideModal
        gpuHealth={gpuHealth}
        assistantName={assistantName}
        onCancel={closeAllModals}
        onSaved={() => {
          closeAllModals()
          reinstall()
        }}
      />,
      'gpu-health-hsa-override-modal'
    )
  }

  const message = needsHsaOverride
    ? gpuHealth.amdGfxTarget
      ? t('apps:gpuAlert.needsOverrideWithTarget', {
          name: assistantName,
          target: gpuHealth.amdGfxTarget,
        })
      : t('apps:gpuAlert.needsOverride', { name: assistantName })
    : isAmd
      ? t('apps:gpuAlert.noAccessAmd', { name: assistantName })
      : t('apps:gpuAlert.noAccessNvidia', { name: assistantName })

  return (
    <Alert
      type="warning"
      variant="bordered"
      title={t('apps:gpuAlert.title', { name: assistantName })}
      message={message}
      className={className}
      dismissible={true}
      onDismiss={handleDismiss}
      buttonProps={{
        children: needsHsaOverride
          ? t('apps:gpuAlert.fixOverride')
          : t('apps:gpuAlert.fixReinstall', { name: assistantName }),
        icon: needsHsaOverride ? 'IconTool' : 'IconRefresh',
        variant: 'action',
        size: 'sm',
        onClick: needsHsaOverride ? openHsaOverrideModal : openReinstallModal,
        loading: reinstalling,
        disabled: reinstalling,
      }}
    />
  )
}

function HsaOverrideModal({
  gpuHealth,
  assistantName,
  onCancel,
  onSaved,
}: {
  gpuHealth: GpuHealthStatus
  assistantName: string
  onCancel: () => void
  onSaved: () => void
}) {
  const { t } = useTranslation()
  const { addNotification } = useNotifications()
  const [value, setValue] = useState(gpuHealth.suggestedHsaOverride ?? '')
  const [saving, setSaving] = useState(false)
  const valid = HSA_OVERRIDE_PATTERN.test(value.trim())

  const save = async () => {
    setSaving(true)
    try {
      const response = await api.updateSetting('ai.amdHsaOverride', value.trim())
      // catchInternal already notified on a request failure and returned undefined.
      if (!response) {
        setSaving(false)
        return
      }
      if (!response.success) throw new Error(response.message)
      onSaved()
    } catch (error) {
      addNotification({
        message: t('apps:gpuAlert.saveOverrideFailed', {
          message: error instanceof Error ? error.message : t('apps:status.unknownError'),
        }),
        type: 'error',
      })
      setSaving(false)
    }
  }

  return (
    <StyledModal
      title={t('apps:gpuAlert.overrideTitle')}
      onConfirm={save}
      onCancel={onCancel}
      open={true}
      confirmText={t('apps:gpuAlert.saveAndReinstall')}
      cancelText={t('apps:actions.cancel')}
      confirmLoading={saving}
      confirmDisabled={!valid || saving}
    >
      <div className="space-y-4 text-text-primary">
        <p>
          {t('apps:gpuAlert.rocmIntro')}
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li>Radeon 780M / 760M (gfx1103): 11.0.0</li>
          <li>{t('apps:gpuAlert.rdna2')}</li>
        </ul>
        <p className="text-sm text-text-secondary">
          {t('apps:gpuAlert.detected', {
            gpu: gpuHealth.amdGfxTarget ?? t('apps:gpuAlert.notReported'),
            override: gpuHealth.currentHsaOverride ?? t('apps:gpuAlert.none'),
          })}
          {gpuHealth.suggestedHsaOverride
            ? ` ${t('apps:gpuAlert.recommended', { version: gpuHealth.suggestedHsaOverride })}`
            : ''}
        </p>
        <Input
          name="amdHsaOverride"
          label={t('apps:gpuAlert.overrideLabel')}
          placeholder="11.0.0"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          error={value.trim() !== '' && !valid}
          helpText={t('apps:gpuAlert.overrideHelp', { name: assistantName })}
        />
      </div>
    </StyledModal>
  )
}
