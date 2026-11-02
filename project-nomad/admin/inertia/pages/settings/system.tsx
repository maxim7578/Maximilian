import { Head } from '@inertiajs/react'
import SettingsLayout from '~/layouts/SettingsLayout'
import { SystemInformationResponse } from '../../../types/system'
import { formatBytes } from '~/lib/util'
import { getAllDiskDisplayItems } from '~/hooks/useDiskDisplayData'
import CircularGauge from '~/components/systeminfo/CircularGauge'
import HorizontalBarChart from '~/components/HorizontalBarChart'
import InfoCard from '~/components/systeminfo/InfoCard'
import Alert from '~/components/Alert'
import GpuPassthroughAlert from '~/components/GpuPassthroughAlert'
import { useSystemInfo } from '~/hooks/useSystemInfo'
import StatusCard from '~/components/systeminfo/StatusCard'
import { IconCpu, IconDatabase, IconServer, IconDeviceDesktop, IconComponents } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { formatDateTime } from '~/i18n'

export default function SettingsPage(props: {
  system: { info: SystemInformationResponse | undefined }
}) {
  const { t } = useTranslation()
  const { data: info } = useSystemInfo({
    initialData: props.system.info,
  })

  // Use (total - available) to reflect actual memory pressure.
  // mem.used includes reclaimable buff/cache on Linux, which inflates the number.
  const memoryUsed = info?.mem.total && info?.mem.available != null
    ? info.mem.total - info.mem.available
    : info?.mem.used || 0
  const memoryUsagePercent = info?.mem.total
    ? ((memoryUsed / info.mem.total) * 100).toFixed(1)
    : 0

  const swapUsagePercent = info?.mem.swaptotal
    ? ((info.mem.swapused / info.mem.swaptotal) * 100).toFixed(1)
    : 0

  const uptimeSeconds = info?.uptime.uptime || 0
  const uptimeDays = Math.floor(uptimeSeconds / 86400)
  const uptimeHours = Math.floor((uptimeSeconds % 86400) / 3600)
  const uptimeMinutes = Math.floor((uptimeSeconds % 3600) / 60)
  const uptimeDisplay = uptimeDays > 0
    ? t('system:system.uptimeDaysHoursMinutes', { days: uptimeDays, hours: uptimeHours, minutes: uptimeMinutes })
    : uptimeHours > 0
      ? t('system:system.uptimeHoursMinutes', { hours: uptimeHours, minutes: uptimeMinutes })
      : t('system:system.uptimeMinutes', { minutes: uptimeMinutes })

  // Build storage display items - fall back to fsSize when disk array is empty
  const storageItems = getAllDiskDisplayItems(info?.disk, info?.fsSize)

  return (
    <SettingsLayout>
      <Head title={t('system:system.title')} />
      <div className="xl:pl-72 w-full">
        <main className="px-6 lg:px-12 py-6 lg:py-8">
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-desert-green mb-2">{t('system:system.title')}</h1>
            <p className="text-desert-stone-dark">
              {t('system:system.subtitle', { lastUpdated: formatDateTime(new Date()) })}
            </p>
          </div>
          {Number(memoryUsagePercent) > 90 && (
            <div className="mb-6">
              <Alert
                type="error"
                title={t('system:system.highMemoryTitle')}
                message={t('system:system.highMemoryMessage')}
                variant="bordered"
              />
            </div>
          )}
          <section className="mb-12">
            <h2 className="text-2xl font-bold text-desert-green mb-6 flex items-center gap-2">
              <div className="w-1 h-6 bg-desert-green" />
              {t('system:system.resourceUsage')}
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              <div className="bg-desert-white rounded-lg p-6 border border-desert-stone-light shadow-sm hover:shadow-lg transition-shadow">
                <CircularGauge
                  value={info?.currentLoad.currentLoad || 0}
                  label={t('system:system.cpuUsage')}
                  size="lg"
                  variant="cpu"
                  subtext={t('system:system.coresCount', { count: info?.cpu.cores || 0 })}
                  icon={<IconCpu className="w-8 h-8" />}
                />
              </div>
              <div className="bg-desert-white rounded-lg p-6 border border-desert-stone-light shadow-sm hover:shadow-lg transition-shadow">
                <CircularGauge
                  value={Number(memoryUsagePercent)}
                  label={t('system:system.memoryUsage')}
                  size="lg"
                  variant="memory"
                  subtext={`${formatBytes(memoryUsed)} / ${formatBytes(info?.mem.total || 0)}`}
                  icon={<IconDatabase className="w-8 h-8" />}
                />
              </div>
              <div className="bg-desert-white rounded-lg p-6 border border-desert-stone-light shadow-sm hover:shadow-lg transition-shadow">
                <CircularGauge
                  value={Number(swapUsagePercent)}
                  label={t('system:system.swapUsage')}
                  size="lg"
                  variant="disk"
                  subtext={`${formatBytes(info?.mem.swapused || 0)} / ${formatBytes(info?.mem.swaptotal || 0)}`}
                  icon={<IconServer className="w-8 h-8" />}
                />
              </div>
            </div>
          </section>
          <section className="mb-12">
            <h2 className="text-2xl font-bold text-desert-green mb-6 flex items-center gap-2">
              <div className="w-1 h-6 bg-desert-green" />
              {t('system:system.systemDetails')}
            </h2>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <InfoCard
                title={t('system:system.operatingSystem')}
                icon={<IconDeviceDesktop className="w-6 h-6" />}
                variant="elevated"
                data={[
                  { label: t('system:system.distribution'), value: info?.os.distro },
                  { label: t('system:system.kernelVersion'), value: info?.os.kernel },
                  { label: t('system:system.architecture'), value: info?.os.arch },
                  { label: t('system:system.hostname'), value: info?.os.hostname },
                  { label: t('system:system.platform'), value: info?.os.platform },
                ]}
              />
              <InfoCard
                title={t('system:system.processor')}
                icon={<IconCpu className="w-6 h-6" />}
                variant="elevated"
                data={[
                  { label: t('system:system.manufacturer'), value: info?.cpu.manufacturer },
                  { label: t('system:system.brand'), value: info?.cpu.brand },
                  { label: t('system:system.cores'), value: info?.cpu.cores },
                  { label: t('system:system.physicalCores'), value: info?.cpu.physicalCores },
                  {
                    label: t('system:system.virtualization'),
                    value: info?.cpu.virtualization ? t('system:system.enabled') : t('system:system.disabled'),
                  },
                ]}
              />
              {info?.gpuHealth?.status === 'passthrough_failed' && (
                <div className="lg:col-span-2">
                  <GpuPassthroughAlert gpuHealth={info.gpuHealth} assistantName={t('system:system.aiAssistant')} />
                </div>
              )}
              {info?.graphics?.controllers && info.graphics.controllers.length > 0 && (
                <InfoCard
                  title={t('system:system.graphics')}
                  icon={<IconComponents className="w-6 h-6" />}
                  variant="elevated"
                  data={info.graphics.controllers.map((gpu, i) => {
                    const multiple = info.graphics.controllers.length > 1
                    const gpuNumber = i + 1
                    return [
                      { label: multiple ? t('system:system.gpuModelNumbered', { number: gpuNumber }) : t('system:system.gpuModel'), value: gpu.model },
                      { label: multiple ? t('system:system.gpuVendorNumbered', { number: gpuNumber }) : t('system:system.gpuVendor'), value: gpu.vendor },
                      { label: multiple ? t('system:system.gpuVramNumbered', { number: gpuNumber }) : t('system:system.gpuVram'), value: gpu.vram ? `${gpu.vram} MB` : t('system:system.notAvailable') },
                    ]
                  }).flat()}
                />
              )}
            </div>
          </section>
          <section className="mb-12">
            <h2 className="text-2xl font-bold text-desert-green mb-6 flex items-center gap-2">
              <div className="w-1 h-6 bg-desert-green" />
              {t('system:system.memoryAllocation')}
            </h2>
            <div className="bg-desert-white rounded-lg p-8 border border-desert-stone-light shadow-sm hover:shadow-lg transition-shadow">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
                <div className="text-center">
                  <div className="text-3xl font-bold text-desert-green mb-1">
                    {formatBytes(info?.mem.total || 0)}
                  </div>
                  <div className="text-sm text-desert-stone-dark uppercase tracking-wide">
                    {t('system:system.totalRam')}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-desert-green mb-1">
                    {formatBytes(memoryUsed)}
                  </div>
                  <div className="text-sm text-desert-stone-dark uppercase tracking-wide">
                    {t('system:system.usedRam')}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-desert-green mb-1">
                    {formatBytes(info?.mem.available || 0)}
                  </div>
                  <div className="text-sm text-desert-stone-dark uppercase tracking-wide">
                    {t('system:system.availableRam')}
                  </div>
                </div>
              </div>
              <div className="relative h-12 bg-desert-stone-lighter rounded-lg overflow-hidden border border-desert-stone-light">
                <div
                  className="absolute left-0 top-0 h-full bg-desert-orange transition-all duration-1000"
                  style={{ width: `${memoryUsagePercent}%` }}
                ></div>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-sm font-bold text-white drop-shadow-md z-10">
                    {t('system:system.utilized', { percent: memoryUsagePercent })}
                  </span>
                </div>
              </div>
            </div>
          </section>
          <section className="mb-12">
            <h2 className="text-2xl font-bold text-desert-green mb-6 flex items-center gap-2">
              <div className="w-1 h-6 bg-desert-green" />
              {t('system:system.storageDevices')}
            </h2>

            <div className="bg-desert-white rounded-lg p-8 border border-desert-stone-light shadow-sm hover:shadow-lg transition-shadow">
              {storageItems.length > 0 ? (
                <HorizontalBarChart
                  items={storageItems}
                  progressiveBarColor={true}
                  statuses={[
                    {
                      label: t('system:system.storageNormal'),
                      min_threshold: 0,
                      color_class: 'bg-desert-olive',
                    },
                    {
                      label: t('system:system.storageWarning'),
                      min_threshold: 75,
                      color_class: 'bg-desert-orange',
                    },
                    {
                      label: t('system:system.storageCritical'),
                      min_threshold: 90,
                      color_class: 'bg-desert-red',
                    },
                  ]}
                />
              ) : (
                <div className="text-center text-desert-stone-dark py-8">
                  {t('system:system.noStorageDevices')}
                </div>
              )}
            </div>
          </section>
          <section>
            <h2 className="text-2xl font-bold text-desert-green mb-6 flex items-center gap-2">
              <div className="w-1 h-6 bg-desert-green" />
              {t('system:system.systemStatus')}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatusCard title={t('system:system.systemUptime')} value={uptimeDisplay} />
              <StatusCard title={t('system:system.cpuCores')} value={info?.cpu.cores || 0} />
              <StatusCard title={t('system:system.storageDevices')} value={storageItems.length} />
            </div>
          </section>
        </main>
      </div>
    </SettingsLayout>
  )
}
