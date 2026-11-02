import { Head, Link, usePage } from '@inertiajs/react'
import { useState } from 'react'
import SettingsLayout from '~/layouts/SettingsLayout'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import CircularGauge from '~/components/systeminfo/CircularGauge'
import InfoCard from '~/components/systeminfo/InfoCard'
import Alert from '~/components/Alert'
import StyledButton from '~/components/StyledButton'
import InfoTooltip from '~/components/InfoTooltip'
import BuilderTagSelector from '~/components/BuilderTagSelector'
import {
  IconRobot,
  IconChartBar,
  IconCpu,
  IconDatabase,
  IconServer,
  IconChevronDown,
  IconClock,
} from '@tabler/icons-react'
import { BenchmarkStatus } from '../../../types/benchmark'
import BenchmarkResult from '#models/benchmark_result'
import api from '~/lib/api'
import useServiceInstalledStatus from '~/hooks/useServiceInstalledStatus'
import { SERVICE_NAMES } from '../../../constants/service_names'
import { useBenchmarkRun } from '~/hooks/useBenchmarkRun'
import BenchmarkRunView from '~/components/benchmark/BenchmarkRunView'
import ScoreReveal from '~/components/benchmark/ScoreReveal'
import { getScoreDisplay } from '~/lib/benchmarkScore'
import { Trans, useTranslation } from 'react-i18next'
import { formatDate, formatDateTime, formatNumber } from '~/i18n'

export default function BenchmarkPage(props: {
  benchmark: {
    latestResult: BenchmarkResult | null
    status: BenchmarkStatus
    currentBenchmarkId: string | null
  }
}) {
  const { t } = useTranslation()
  const { aiAssistantName } = usePage<{ aiAssistantName: string }>().props
  const queryClient = useQueryClient()
  const aiInstalled = useServiceInstalledStatus(SERVICE_NAMES.OLLAMA)
  const [isRunning, setIsRunning] = useState(props.benchmark.status !== 'idle')
  const [revealing, setRevealing] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [showDetails, setShowDetails] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [showAIRequiredAlert, setShowAIRequiredAlert] = useState(false)
  const [shareAnonymously, setShareAnonymously] = useState(false)
  const [currentBuilderTag, setCurrentBuilderTag] = useState<string | null>(
    props.benchmark.latestResult?.builder_tag || null
  )

  // Fetch latest result
  const { data: latestResult, refetch: refetchLatest } = useQuery({
    queryKey: ['benchmark', 'latest'],
    queryFn: async () => {
      const res = await api.getLatestBenchmarkResult()
      if (res && res.result) {
        return res.result
      }
      return null
    },
    initialData: props.benchmark.latestResult,
  })

  // Live run state: owns the progress + telemetry SSE subscriptions.
  const run = useBenchmarkRun({
    onFinished: (status, message) => {
      setIsRunning(false)
      if (status === 'completed') {
        refetchLatest()
        setRevealing(true)
      } else {
        setErrorMsg(message || t('benchmark:page.benchmarkFailedFallback'))
      }
    },
  })

  // Fetch all benchmark results for history
  const { data: benchmarkHistory } = useQuery({
    queryKey: ['benchmark', 'history'],
    queryFn: async () => {
      const res = await api.getBenchmarkResults()
      if (res && res.results && Array.isArray(res.results)) {
        return res.results
      }
      return []
    },
  })

  // Run benchmark mutation (async: dispatched to the queue worker; live progress
  // and completion arrive over SSE via useBenchmarkRun).
  const runBenchmark = useMutation({
    mutationFn: async (type: 'full' | 'system' | 'ai') => {
      setErrorMsg(null)
      run.reset()
      setIsRunning(true)

      // Use sync mode - runs inline without needing Redis/queue worker
      return await api.runBenchmark(type, true)
    },
    onSuccess: (data) => {
      // Dispatch only confirms the job started; the 'completed'/'error' SSE event
      // drives the rest (see useBenchmarkRun's onFinished).
      if (!data?.success) {
        setIsRunning(false)
        setErrorMsg(t('benchmark:page.failedToStart'))
      }
    },
    onError: (error) => {
      setIsRunning(false)
      setErrorMsg(error.message || t('benchmark:page.failedToStart'))
    },
  })

  // Update builder tag mutation
  const updateBuilderTag = useMutation({
    mutationFn: async ({
      benchmarkId,
      builderTag,
    }: {
      benchmarkId: string
      builderTag: string
      invalidate?: boolean
    }) => {
      const res = await api.updateBuilderTag(benchmarkId, builderTag)
      if (!res || !res.success) {
        throw new Error(res?.error || t('benchmark:page.failedToUpdateTag'))
      }
      return res
    },
    onSuccess: (_, variables) => {
      if (variables.invalidate) {
        refetchLatest()
        queryClient.invalidateQueries({ queryKey: ['benchmark', 'history'] })
      }
    },
  })

  // Submit to repository mutation
  const [submitError, setSubmitError] = useState<string | null>(null)
  const submitResult = useMutation({
    mutationFn: async ({ benchmarkId, anonymous }: { benchmarkId: string; anonymous: boolean }) => {
      setSubmitError(null)

      // First, save the current builder tag to the benchmark (don't refetch yet)
      if (currentBuilderTag && !anonymous) {
        await updateBuilderTag.mutateAsync({
          benchmarkId,
          builderTag: currentBuilderTag,
          invalidate: false,
        })
      }

      const res = await api.submitBenchmark(benchmarkId, anonymous)
      if (!res || !res.success) {
        throw new Error(res?.error || t('benchmark:page.failedToSubmit'))
      }
      return res
    },
    onSuccess: () => {
      refetchLatest()
      queryClient.invalidateQueries({ queryKey: ['benchmark', 'history'] })
    },
    onError: (error: any) => {
      // Check if this is a 409 Conflict error (already submitted)
      if (error.status === 409) {
        setSubmitError(t('benchmark:page.alreadySubmitted'))
      } else {
        setSubmitError(error.message)
      }
    },
  })

  // Check if the latest result is a full benchmark with AI data (eligible for sharing)
  const canShareBenchmark =
    latestResult &&
    latestResult.benchmark_type === 'full' &&
    latestResult.ai_tokens_per_second !== null &&
    latestResult.ai_tokens_per_second > 0 &&
    !latestResult.submitted_to_repository

  // How to present the headline score: partial (System/AI Only) runs are NOT the
  // NOMAD Score and are relabelled + flagged so users don't mistake them for it.
  const scoreInfo = latestResult ? getScoreDisplay(latestResult.benchmark_type) : null

  // Handle Full Benchmark click with pre-flight check
  const handleFullBenchmarkClick = () => {
    if (!aiInstalled) {
      setShowAIRequiredAlert(true)
      return
    }
    setShowAIRequiredAlert(false)
    runBenchmark.mutate('full')
  }

  const benchmarkTypeLabel = (type: string) =>
    ({
      full: t('benchmark:page.types.full'),
      system: t('benchmark:page.types.system'),
      ai: t('benchmark:page.types.ai'),
    })[type] ?? type

  const formatBytes = (bytes: number) => {
    const gb = bytes / (1024 * 1024 * 1024)
    return `${gb.toFixed(1)} GB`
  }

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-green-600'
    if (score >= 40) return 'text-yellow-600'
    return 'text-red-600'
  }

  // Calculate AI score from tokens per second (normalized to 0-100)
  // Reference: 30 tok/s = 50 score, 60 tok/s = 100 score
  const getAIScore = (tokensPerSecond: number | null): number => {
    if (!tokensPerSecond) return 0
    const score = (tokensPerSecond / 60) * 100
    return Math.min(100, Math.max(0, score))
  }

  return (
    <SettingsLayout>
      <Head title={t('benchmark:page.title')} />
      <div className="xl:pl-72 w-full">
        <main className="px-6 lg:px-12 py-6 lg:py-8">
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-desert-green mb-2">{t('benchmark:page.title')}</h1>
            <p className="text-desert-stone-dark">
              {t('benchmark:page.subtitle')}
            </p>
          </div>

          {/* Run Benchmark Section */}
          <section className="mb-12">
            <h2 className="text-2xl font-bold text-desert-green mb-6 flex items-center gap-2">
              <div className="w-1 h-6 bg-desert-green" />
              {t('benchmark:page.runBenchmark')}
            </h2>

            {isRunning ? (
              <BenchmarkRunView run={run} />
            ) : revealing ? (
              // Reveal slot: wait for the refetched latest result to be the one
              // from this run, then hand it to the score reveal.
              (() => {
                const ready =
                  latestResult && latestResult.benchmark_id === run.progress?.benchmark_id
                return ready ? (
                  <ScoreReveal result={latestResult} onDone={() => setRevealing(false)} />
                ) : (
                  <div className="bg-desert-white rounded-lg p-8 border border-desert-stone-light shadow-sm">
                    <div className="flex items-center justify-center gap-3 text-desert-green animate-pulse">
                      <div className="animate-spin h-6 w-6 border-2 border-desert-green border-t-transparent rounded-full" />
                      <span className="text-lg font-medium">{t('benchmark:page.compilingReport')}</span>
                    </div>
                  </div>
                )
              })()
            ) : (
              <div className="bg-desert-white rounded-lg p-8 border border-desert-stone-light shadow-sm">
                <div className="space-y-6">
                  {errorMsg && (
                    <Alert
                      type="error"
                      title={t('benchmark:page.benchmarkFailedTitle')}
                      message={errorMsg}
                      variant="bordered"
                      dismissible
                      onDismiss={() => setErrorMsg(null)}
                    />
                  )}
                  {showAIRequiredAlert && (
                    <Alert
                      type="warning"
                      title={t('benchmark:page.aiRequiredTitle', { name: aiAssistantName })}
                      message={t('benchmark:page.aiRequiredMessage', { name: aiAssistantName })}
                      variant="bordered"
                      dismissible
                      onDismiss={() => setShowAIRequiredAlert(false)}
                    >
                      <Link
                        href="/settings/apps"
                        className="text-sm text-desert-green hover:underline mt-2 inline-block font-medium"
                      >
                        {t('benchmark:page.goToApps', { name: aiAssistantName })}
                      </Link>
                    </Alert>
                  )}
                  <p className="text-desert-stone-dark">
                    {t('benchmark:page.runDescription')}
                  </p>
                  <div className="flex flex-wrap gap-4">
                    <StyledButton
                      onClick={handleFullBenchmarkClick}
                      disabled={runBenchmark.isPending}
                      icon="IconPlayerPlay"
                    >
                      {t('benchmark:page.runFull')}
                    </StyledButton>
                    <StyledButton
                      variant="secondary"
                      onClick={() => runBenchmark.mutate('system')}
                      disabled={runBenchmark.isPending}
                      icon="IconCpu"
                    >
                      {t('benchmark:page.systemOnly')}
                    </StyledButton>
                    <StyledButton
                      variant="secondary"
                      onClick={() => runBenchmark.mutate('ai')}
                      disabled={runBenchmark.isPending || !aiInstalled}
                      icon="IconWand"
                      title={
                        !aiInstalled
                          ? t('benchmark:page.aiMustBeInstalled', { name: aiAssistantName })
                          : undefined
                      }
                    >
                      {t('benchmark:page.aiOnly')}
                    </StyledButton>
                  </div>
                  {!aiInstalled && (
                    <p className="text-sm text-desert-stone-dark">
                      <Trans
                        i18nKey="benchmark:page.aiNotInstalledNote"
                        values={{ name: aiAssistantName }}
                        components={{
                          note: <span className="text-amber-600" />,
                          link: (
                            <Link
                              href="/settings/apps"
                              className="text-desert-green hover:underline ml-1"
                            />
                          ),
                        }}
                      />
                    </p>
                  )}
                </div>
              </div>
            )}
          </section>

          {/* Results Section */}
          {latestResult && (
            <>
              <section className="mb-12">
                <h2 className="text-2xl font-bold text-desert-green mb-6 flex items-center gap-2">
                  <div className="w-1 h-6 bg-desert-green" />
                  {scoreInfo?.label ?? t('benchmark:score.nomadScore')}
                  {scoreInfo?.isPartial && (
                    <span className="ml-1 px-2 py-0.5 rounded-full bg-desert-stone-light text-desert-stone-dark text-xs font-semibold uppercase tracking-wide">
                      {t('benchmark:page.partial')}
                    </span>
                  )}
                </h2>

                <div className="bg-desert-white rounded-lg p-8 border border-desert-stone-light shadow-sm">
                  <div className="flex flex-col md:flex-row items-center gap-8">
                    <div className="shrink-0">
                      <CircularGauge
                        value={latestResult.nomad_score}
                        label={latestResult.nomad_score_v2 != null ? t('benchmark:page.legacyScore') : t('benchmark:score.nomadScore')}
                        size="lg"
                        variant="cpu"
                        subtext={t('benchmark:scoreReveal.outOf100')}
                        muted={scoreInfo?.isPartial}
                        icon={<IconChartBar className="w-8 h-8" />}
                      />
                    </div>
                    <div className="flex-1 space-y-4">
                      {latestResult.nomad_score_v2 != null ? (
                        <>
                          <div className="flex items-baseline gap-3">
                            <div className="text-5xl font-bold text-desert-green">
                              {latestResult.nomad_score_v2.toFixed(1)}
                            </div>
                            <div className="text-sm text-desert-stone-dark flex items-center gap-1">
                              {t('benchmark:score.nomadScore')}
                              <InfoTooltip text={t('benchmark:page.scoreV2Tooltip')} />
                            </div>
                          </div>
                          <p className="text-sm text-desert-stone-dark">
                            {t('benchmark:page.referenceBuild')}{' '}
                            <span className="text-desert-stone">
                              {t('benchmark:page.legacyScale', { score: latestResult.nomad_score.toFixed(1) })}
                            </span>
                          </p>
                        </>
                      ) : (
                        <>
                          <div className="flex items-center gap-3">
                        <div
                              className={`text-5xl font-bold ${
                            scoreInfo?.isPartial
                              ? 'text-desert-stone-dark'
                              : getScoreColor(latestResult.nomad_score)
                          }`}
                            >
                              {latestResult.nomad_score.toFixed(1)}
                            </div>
                        {scoreInfo?.isPartial && (
                          <span className="px-2 py-1 rounded-md bg-desert-stone-light text-desert-stone-dark text-xs font-semibold uppercase tracking-wide">
                            {t('benchmark:page.partial')}
                          </span>
                        )}
                      </div>
                          <p className="text-desert-stone-dark">
                            {scoreInfo?.isPartial
                          ? scoreInfo.cta
                          : t('benchmark:scoreReveal.compositeExplanation')}
                          </p>
                        </>
                      )}

                      {/* Share with Community - Only for full benchmarks with AI data */}
                      {canShareBenchmark && (
                        <div className="space-y-4 mt-6 pt-6 border-t border-desert-stone-light">
                          <h3 className="font-semibold text-desert-green">{t('benchmark:page.shareTitle')}</h3>
                          <p className="text-sm text-desert-stone-dark">
                            {t('benchmark:page.shareDescription')}
                          </p>

                          {/* Builder Tag Selector */}
                          <div className="space-y-2">
                            <label className="block text-sm font-medium text-desert-stone-dark">
                              {t('benchmark:page.yourBuilderTag')}
                            </label>
                            <BuilderTagSelector
                              value={currentBuilderTag}
                              onChange={setCurrentBuilderTag}
                              disabled={shareAnonymously || submitResult.isPending}
                            />
                          </div>

                          {/* Anonymous checkbox */}
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={shareAnonymously}
                              onChange={(e) => setShareAnonymously(e.target.checked)}
                              disabled={submitResult.isPending}
                              className="w-4 h-4 rounded border-desert-stone-light text-desert-green focus:ring-desert-green"
                            />
                            <span className="text-sm text-desert-stone-dark">
                              {t('benchmark:page.shareAnonymously')}
                            </span>
                          </label>

                          <StyledButton
                            onClick={() =>
                              submitResult.mutate({
                                benchmarkId: latestResult.benchmark_id,
                                anonymous: shareAnonymously,
                              })
                            }
                            disabled={submitResult.isPending}
                            icon="IconCloudUpload"
                          >
                            {submitResult.isPending ? t('benchmark:page.submitting') : t('benchmark:page.shareTitle')}
                          </StyledButton>
                          {submitError && (
                            <Alert
                              type="error"
                              title={t('benchmark:page.submissionFailed')}
                              message={submitError}
                              variant="bordered"
                              dismissible
                              onDismiss={() => setSubmitError(null)}
                            />
                          )}
                        </div>
                      )}

                      {/* Show message for partial benchmarks */}
                      {latestResult &&
                        !latestResult.submitted_to_repository &&
                        !canShareBenchmark && (
                          <Alert
                            type="info"
                            title={t('benchmark:page.partialBenchmarkTitle')}
                            message={t('benchmark:page.partialBenchmarkMessage', { type: benchmarkTypeLabel(latestResult.benchmark_type), name: aiAssistantName })}
                            variant="bordered"
                          />
                        )}

                      {latestResult.submitted_to_repository && (
                        <Alert
                          type="success"
                          title={t('benchmark:page.sharedTitle')}
                          message={t('benchmark:page.sharedMessage')}
                          variant="bordered"
                        >
                          <a
                            href="https://benchmark.projectnomad.us"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-desert-green hover:underline mt-2 inline-block"
                          >
                            {t('benchmark:page.viewLeaderboard')}
                          </a>
                        </Alert>
                      )}
                    </div>
                  </div>
                </div>
              </section>

              <section className="mb-12">
                <h2 className="text-2xl font-bold text-desert-green mb-6 flex items-center gap-2">
                  <div className="w-1 h-6 bg-desert-green" />
                  {t('benchmark:page.systemPerformance')}
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div className="bg-desert-white rounded-lg p-6 border border-desert-stone-light shadow-sm">
                    <CircularGauge
                      value={latestResult.cpu_score * 100}
                      label={t('benchmark:scoreReveal.cpu')}
                      size="md"
                      variant="cpu"
                      icon={<IconCpu className="w-6 h-6" />}
                    />
                  </div>
                  <div className="bg-desert-white rounded-lg p-6 border border-desert-stone-light shadow-sm">
                    <CircularGauge
                      value={latestResult.memory_score * 100}
                      label={t('benchmark:scoreReveal.memory')}
                      size="md"
                      variant="memory"
                      icon={<IconDatabase className="w-6 h-6" />}
                    />
                  </div>
                  <div className="bg-desert-white rounded-lg p-6 border border-desert-stone-light shadow-sm">
                    <CircularGauge
                      value={latestResult.disk_read_score * 100}
                      label={t('benchmark:scoreReveal.diskRead')}
                      size="md"
                      variant="disk"
                      icon={<IconServer className="w-6 h-6" />}
                    />
                  </div>
                  <div className="bg-desert-white rounded-lg p-6 border border-desert-stone-light shadow-sm">
                    <CircularGauge
                      value={latestResult.disk_write_score * 100}
                      label={t('benchmark:scoreReveal.diskWrite')}
                      size="md"
                      variant="disk"
                      icon={<IconServer className="w-6 h-6" />}
                    />
                  </div>
                </div>
              </section>

              {/* AI Performance Section */}
              <section className="mb-12">
                <h2 className="text-2xl font-bold text-desert-green mb-6 flex items-center gap-2">
                  <div className="w-1 h-6 bg-desert-green" />
                  {t('benchmark:page.aiPerformance')}
                </h2>

                {latestResult.ai_tokens_per_second ? (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-desert-white rounded-lg p-6 border border-desert-stone-light shadow-sm">
                      <CircularGauge
                        value={getAIScore(latestResult.ai_tokens_per_second)}
                        label={t('benchmark:score.aiScore')}
                        size="md"
                        variant="cpu"
                        icon={<IconRobot className="w-6 h-6" />}
                      />
                    </div>
                    <div className="bg-desert-white rounded-lg p-6 border border-desert-stone-light shadow-sm flex items-center justify-center">
                      <div className="flex items-center gap-4">
                        <IconRobot className="w-10 h-10 text-desert-green" />
                        <div>
                          <div className="text-3xl font-bold text-desert-green">
                            {latestResult.ai_tokens_per_second.toFixed(1)}
                          </div>
                          <div className="text-sm text-desert-stone-dark flex items-center gap-1">
                            {t('benchmark:runView.tokensPerSecond')}
                            <InfoTooltip text={t('benchmark:page.tokensPerSecondTooltip')} />
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="bg-desert-white rounded-lg p-6 border border-desert-stone-light shadow-sm flex items-center justify-center">
                      <div className="flex items-center gap-4">
                        <IconRobot className="w-10 h-10 text-desert-green" />
                        <div>
                          <div className="text-3xl font-bold text-desert-green">
                            {latestResult.ai_time_to_first_token?.toFixed(0) || t('benchmark:page.notAvailable')} ms
                          </div>
                          <div className="text-sm text-desert-stone-dark flex items-center gap-1">
                            {t('benchmark:page.timeToFirstToken')}
                            <InfoTooltip text={t('benchmark:page.timeToFirstTokenTooltip')} />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-desert-white rounded-lg p-6 border border-desert-stone-light shadow-sm">
                    <div className="text-center text-desert-stone-dark">
                      <IconRobot className="w-12 h-12 mx-auto mb-3 opacity-40" />
                      <p className="font-medium">{t('benchmark:page.noAiData')}</p>
                      <p className="text-sm mt-1">
                        {t('benchmark:page.noAiDataDescription')}
                      </p>
                    </div>
                  </div>
                )}
              </section>

              <section className="mb-12">
                <h2 className="text-2xl font-bold text-desert-green mb-6 flex items-center gap-2">
                  <div className="w-1 h-6 bg-desert-green" />
                  {t('benchmark:page.hardwareInformation')}
                </h2>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <InfoCard
                    title={t('benchmark:page.processor')}
                    icon={<IconCpu className="w-6 h-6" />}
                    variant="elevated"
                    data={[
                      { label: t('benchmark:page.model'), value: latestResult.cpu_model },
                      { label: t('benchmark:page.cores'), value: latestResult.cpu_cores },
                      { label: t('benchmark:page.threads'), value: latestResult.cpu_threads },
                    ]}
                  />
                  <InfoCard
                    title={t('benchmark:page.system')}
                    icon={<IconServer className="w-6 h-6" />}
                    variant="elevated"
                    data={[
                      { label: t('benchmark:page.ram'), value: formatBytes(latestResult.ram_bytes) },
                      { label: t('benchmark:page.diskType'), value: latestResult.disk_type.toUpperCase() },
                      { label: t('benchmark:page.gpu'), value: latestResult.gpu_model || t('benchmark:page.notDetected') },
                    ]}
                  />
                </div>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-desert-green mb-6 flex items-center gap-2">
                  <div className="w-1 h-6 bg-desert-green" />
                  {t('benchmark:page.benchmarkDetails')}
                </h2>

                <div className="bg-desert-white rounded-lg border border-desert-stone-light shadow-sm overflow-hidden">
                  {/* Summary row - always visible */}
                  <button
                    onClick={() => setShowDetails(!showDetails)}
                    className="w-full p-6 flex items-center justify-between hover:bg-desert-stone-lighter/30 transition-colors"
                  >
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-left flex-1">
                      <div>
                        <div className="text-desert-stone-dark">{t('benchmark:page.benchmarkId')}</div>
                        <div className="font-mono text-xs">
                          {latestResult.benchmark_id.slice(0, 8)}...
                        </div>
                      </div>
                      <div>
                        <div className="text-desert-stone-dark">{t('benchmark:page.type')}</div>
                        <div className="capitalize">{benchmarkTypeLabel(latestResult.benchmark_type)}</div>
                      </div>
                      <div>
                        <div className="text-desert-stone-dark">{t('benchmark:page.date')}</div>
                        <div>
                          {formatDate(latestResult.created_at as unknown as string)}
                        </div>
                      </div>
                      <div>
                        <div className="text-desert-stone-dark">{t('benchmark:score.nomadScore')}</div>
                        <div className="font-bold text-desert-green">
                          {(latestResult.nomad_score_v2 ?? latestResult.nomad_score).toFixed(1)}
                        </div>
                      </div>
                    </div>
                    <IconChevronDown
                      className={`w-5 h-5 text-desert-stone-dark transition-transform ${showDetails ? 'rotate-180' : ''}`}
                    />
                  </button>

                  {/* Expanded details */}
                  {showDetails && (
                    <div className="border-t border-desert-stone-light p-6 bg-desert-stone-lighter/20">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Raw Scores */}
                        <div>
                          <h4 className="font-semibold text-desert-green mb-3">{t('benchmark:page.rawScores')}</h4>
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span className="text-desert-stone-dark">{t('benchmark:page.cpuScore')}</span>
                              <span className="font-mono">
                                {(latestResult.cpu_score * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-desert-stone-dark">{t('benchmark:page.memoryScore')}</span>
                              <span className="font-mono">
                                {(latestResult.memory_score * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-desert-stone-dark">{t('benchmark:page.diskReadScore')}</span>
                              <span className="font-mono">
                                {(latestResult.disk_read_score * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-desert-stone-dark">{t('benchmark:page.diskWriteScore')}</span>
                              <span className="font-mono">
                                {(latestResult.disk_write_score * 100).toFixed(1)}%
                              </span>
                            </div>
                            {latestResult.ai_tokens_per_second && (
                              <>
                                <div className="flex justify-between">
                                  <span className="text-desert-stone-dark">{t('benchmark:page.aiTokensPerSec')}</span>
                                  <span className="font-mono">
                                    {latestResult.ai_tokens_per_second.toFixed(1)}
                                  </span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-desert-stone-dark">
                                    {t('benchmark:page.aiTimeToFirstToken')}
                                  </span>
                                  <span className="font-mono">
                                    {latestResult.ai_time_to_first_token?.toFixed(0) || t('benchmark:page.notAvailable')} ms
                                  </span>
                                </div>
                              </>
                            )}
                          </div>
                        </div>

                        {/* Benchmark Info */}
                        <div>
                          <h4 className="font-semibold text-desert-green mb-3">{t('benchmark:page.benchmarkInfo')}</h4>
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span className="text-desert-stone-dark">{t('benchmark:page.fullBenchmarkId')}</span>
                              <span className="font-mono text-xs">{latestResult.benchmark_id}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-desert-stone-dark">{t('benchmark:page.benchmarkType')}</span>
                              <span className="capitalize">{benchmarkTypeLabel(latestResult.benchmark_type)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-desert-stone-dark">{t('benchmark:page.runDate')}</span>
                              <span>
                                {formatDateTime(latestResult.created_at as unknown as string)}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-desert-stone-dark">{t('benchmark:page.builderTag')}</span>
                              <span className="font-mono">
                                {latestResult.builder_tag || t('benchmark:page.notSet')}
                              </span>
                            </div>
                            {latestResult.ai_model_used && (
                              <div className="flex justify-between">
                                <span className="text-desert-stone-dark">{t('benchmark:page.aiModelUsed')}</span>
                                <span>{latestResult.ai_model_used}</span>
                              </div>
                            )}
                            <div className="flex justify-between">
                              <span className="text-desert-stone-dark">
                                {t('benchmark:page.submittedToRepository')}
                              </span>
                              <span>{latestResult.submitted_to_repository ? t('benchmark:page.yes') : t('benchmark:page.no')}</span>
                            </div>
                            {latestResult.repository_id && (
                              <div className="flex justify-between">
                                <span className="text-desert-stone-dark">{t('benchmark:page.repositoryId')}</span>
                                <span className="font-mono text-xs">
                                  {latestResult.repository_id}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* v2 raw measurements + run environment */}
                      {latestResult.cpu_events_multi != null && (
                        <div className="mt-6 pt-6 border-t border-desert-stone-light grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div>
                            <h4 className="font-semibold text-desert-green mb-3">
                              {t('benchmark:page.measuredPerformance')}
                            </h4>
                            <div className="space-y-2 text-sm">
                              <div className="flex justify-between">
                                <span className="text-desert-stone-dark">{t('benchmark:page.cpuSingleThread')}</span>
                                <span className="font-mono">
                                  {latestResult.cpu_events_single?.toFixed(1)} events/s
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-desert-stone-dark">
                                  {t('benchmark:page.cpuMultiThread', { threads: latestResult.cpu_benchmark_threads })}
                                </span>
                                <span className="font-mono">
                                  {latestResult.cpu_events_multi?.toFixed(1)} events/s
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-desert-stone-dark">
                                  {t('benchmark:page.memoryThreads', { threads: latestResult.memory_threads })}
                                </span>
                                <span className="font-mono">
                                  {latestResult.memory_ops_per_sec != null && formatNumber(latestResult.memory_ops_per_sec)} ops/s
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-desert-stone-dark">
                                  {t('benchmark:page.diskReadDirect')}
                                </span>
                                <span className="font-mono">
                                  {latestResult.disk_read_mb_per_sec?.toFixed(1)} MB/s
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-desert-stone-dark">
                                  {t('benchmark:page.diskWriteDirect')}
                                </span>
                                <span className="font-mono">
                                  {latestResult.disk_write_mb_per_sec?.toFixed(1)} MB/s
                                </span>
                              </div>
                            </div>
                          </div>

                          <div>
                            <h4 className="font-semibold text-desert-green mb-3">{t('benchmark:page.environment')}</h4>
                            <div className="space-y-2 text-sm">
                              <div className="flex justify-between">
                                <span className="text-desert-stone-dark">{t('benchmark:page.runEnvironment')}</span>
                                <span className="font-mono">
                                  {latestResult.run_environment || t('benchmark:page.unknown')}
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-desert-stone-dark">{t('benchmark:page.storageBackend')}</span>
                                <span className="font-mono">
                                  {latestResult.storage_path_type || t('benchmark:page.unknown')}
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-desert-stone-dark">{t('benchmark:page.gpuCompute')}</span>
                                <span className="font-mono">
                                  {latestResult.gpu_compute_detected == null
                                    ? t('benchmark:page.unknown')
                                    : latestResult.gpu_compute_detected
                                      ? t('benchmark:page.detected')
                                      : t('benchmark:page.notDetected')}
                                </span>
                              </div>
                              {latestResult.sysbench_digest && (
                                <div className="flex justify-between">
                                  <span className="text-desert-stone-dark">sysbench</span>
                                  <span className="font-mono text-xs">
                                    {latestResult.sysbench_digest.replace('sha256:', '').slice(0, 12)}
                                  </span>
                                </div>
                              )}
                              {latestResult.ollama_version && (
                                <div className="flex justify-between">
                                  <span className="text-desert-stone-dark">Ollama</span>
                                  <span className="font-mono text-xs">
                                    {latestResult.ollama_version}
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </section>

              {/* Benchmark History */}
              {benchmarkHistory && benchmarkHistory.length > 1 && (
                <section className="mb-12">
                  <h2 className="text-2xl font-bold text-desert-green mb-6 flex items-center gap-2">
                    <div className="w-1 h-6 bg-desert-green" />
                    {t('benchmark:page.history')}
                  </h2>

                  <div className="bg-desert-white rounded-lg border border-desert-stone-light shadow-sm overflow-hidden">
                    <button
                      onClick={() => setShowHistory(!showHistory)}
                      className="w-full p-4 flex items-center justify-between hover:bg-desert-stone-lighter/30 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <IconClock className="w-5 h-5 text-desert-stone-dark" />
                        <span className="font-medium text-desert-green">
                          {t('benchmark:page.benchmarksRecorded', { count: benchmarkHistory.length })}
                        </span>
                      </div>
                      <IconChevronDown
                        className={`w-5 h-5 text-desert-stone-dark transition-transform ${showHistory ? 'rotate-180' : ''}`}
                      />
                    </button>

                    {showHistory && (
                      <div className="border-t border-desert-stone-light">
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead className="bg-desert-stone-lighter/50">
                              <tr>
                                <th className="text-left p-3 font-medium text-desert-stone-dark">
                                  {t('benchmark:page.date')}
                                </th>
                                <th className="text-left p-3 font-medium text-desert-stone-dark">
                                  {t('benchmark:page.type')}
                                </th>
                                <th className="text-left p-3 font-medium text-desert-stone-dark">
                                  {t('benchmark:page.score')}
                                </th>
                                <th className="text-left p-3 font-medium text-desert-stone-dark">
                                  {t('benchmark:page.builderTag')}
                                </th>
                                <th className="text-left p-3 font-medium text-desert-stone-dark">
                                  {t('benchmark:page.shared')}
                                </th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-desert-stone-lighter">
                              {benchmarkHistory.map((result) => (
                                <tr
                                  key={result.benchmark_id}
                                  className={`hover:bg-desert-stone-lighter/30 ${
                                    result.benchmark_id === latestResult?.benchmark_id
                                      ? 'bg-desert-green/5'
                                      : ''
                                  }`}
                                >
                                  <td className="p-3">
                                    {formatDate(result.created_at as unknown as string)}
                                  </td>
                                  <td className="p-3 capitalize">{benchmarkTypeLabel(result.benchmark_type)}</td>
                                  {/*
                                    Show the v2 score when the run has one.

                                    This column rendered nomad_score for every
                                    row, so a v2 run showed its legacy score
                                    while the Benchmark Details card directly
                                    above showed the v2 one. The same run read
                                    as 65.0 here and 1036.1 there.

                                    Rows predating v2 have no v2 score and can
                                    only show the legacy number, so the two
                                    scales end up in one column. They differ by
                                    more than 10x, and without the scale on
                                    screen a v2 run next to older runs reads as
                                    a collapse rather than a rescale. The "/ 100"
                                    suffix names the legacy scale in place,
                                    matching the wording the details card
                                    already uses.
                                  */}
                                  <td className="p-3">
                                    <span className="font-bold text-desert-green">
                                      {(result.nomad_score_v2 ?? result.nomad_score).toFixed(1)}
                                    </span>
                                    {result.nomad_score_v2 == null && (
                                      <span className="ml-1 text-xs text-desert-stone-dark">
                                        / 100
                                      </span>
                                    )}
                                  </td>
                                  <td className="p-3 font-mono text-xs">
                                    {result.builder_tag || '—'}
                                  </td>
                                  <td className="p-3">
                                    {result.submitted_to_repository ? (
                                      <span className="text-green-600">✓</span>
                                    ) : (
                                      <span className="text-desert-stone-dark">—</span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                </section>
              )}
            </>
          )}

          {!latestResult && !isRunning && (
            <Alert
              type="info"
              title={t('benchmark:page.noResultsTitle')}
              message={t('benchmark:page.noResultsMessage')}
              variant="bordered"
            />
          )}
        </main>
      </div>
    </SettingsLayout>
  )
}
