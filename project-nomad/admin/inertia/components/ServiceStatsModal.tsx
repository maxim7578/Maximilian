import { useEffect, useState } from 'react'
import StyledModal from './StyledModal'
import { formatBytes } from '~/lib/util'
import api from '~/lib/api'
import { formatNumber } from '~/i18n'
import { useTranslation } from 'react-i18next'

interface Stats {
  cpuPercent: number
  memUsageBytes: number
  memLimitBytes: number
  memPercent: number
}

interface ServiceStatsModalProps {
  serviceName: string
  friendlyName: string
  open: boolean
  onClose: () => void
}

function Bar({ percent, label, value }: { percent: number; label: string; value: string }) {
  const clamped = Math.min(100, Math.max(0, percent))
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="font-medium text-text-primary">{label}</span>
        <span className="text-text-muted font-mono">{value}</span>
      </div>
      <div className="h-2 w-full rounded-full bg-surface-secondary overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            clamped > 90 ? 'bg-desert-red' : clamped > 70 ? 'bg-desert-orange' : 'bg-desert-green'
          }`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  )
}

function formatPercent(value: number): string {
  return formatNumber(value, { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

/** Polls and displays live CPU/memory usage for a running service container. */
export default function ServiceStatsModal({
  serviceName,
  friendlyName,
  open,
  onClose,
}: ServiceStatsModalProps) {
  const { t } = useTranslation()
  const [stats, setStats] = useState<Stats | null>(null)
  const [running, setRunning] = useState(true)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    let cancelled = false

    async function poll() {
      const res = await api.getServiceStats(serviceName)
      if (cancelled || !res) return
      setRunning(res.running)
      setStats(res.stats)
      setLoading(false)
    }

    setLoading(true)
    poll()
    const id = setInterval(poll, 2000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [open, serviceName])

  return (
    <StyledModal
      title={t('apps:serviceStatsModal.title', { name: friendlyName })}
      open={open}
      onCancel={onClose}
      cancelText={t('apps:actions.close')}
    >
      <div className="space-y-4 text-sm">
        {!running ? (
          <p className="text-text-muted text-center py-6">
            {t('apps:serviceStatsModal.notRunning')}
          </p>
        ) : !stats ? (
          <p className="text-text-muted text-center py-6">
            {loading ? t('apps:status.loading') : t('apps:serviceStatsModal.noStats')}
          </p>
        ) : (
          <>
            <Bar label="CPU" percent={stats.cpuPercent} value={`${formatPercent(stats.cpuPercent)}%`} />
            <Bar
              label={t('apps:serviceStatsModal.memory')}
              percent={stats.memPercent}
              value={`${formatBytes(stats.memUsageBytes)} / ${formatBytes(stats.memLimitBytes)} (${formatPercent(stats.memPercent)}%)`}
            />
            <p className="text-xs text-text-muted">{t('apps:serviceStatsModal.interval')}</p>
          </>
        )}
      </div>
    </StyledModal>
  )
}
