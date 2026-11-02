import { computeJobHealth, type JobHealthStatus } from '../../app/utils/kb_job_health.js'
import { tk } from '../i18n/language.js'

export { computeJobHealth, type JobHealthStatus } from '../../app/utils/kb_job_health.js'

/**
 * Visual presentation for each health status — pill color, dot color, and the
 * translation keys of the short label rendered alongside the dot and of its
 * accessible description (render them with t(key)). Kept in one place so
 * backend health decisions (`computeJobHealth`) and frontend rendering stay in
 * sync. The module stays free of i18next so it remains importable in Node.
 */
export const JOB_HEALTH_DISPLAY = {
  waiting: {
    dot: 'bg-gray-400 dark:bg-gray-500',
    labelKey: tk('knowledgeBase:embedJobs.health.waiting'),
    ariaLabelKey: tk('knowledgeBase:embedJobs.healthAria.waiting'),
  },
  healthy: {
    dot: 'bg-green-500',
    labelKey: tk('knowledgeBase:embedJobs.health.healthy'),
    ariaLabelKey: tk('knowledgeBase:embedJobs.healthAria.healthy'),
  },
  slow: {
    dot: 'bg-yellow-500',
    labelKey: tk('knowledgeBase:embedJobs.health.slow'),
    ariaLabelKey: tk('knowledgeBase:embedJobs.healthAria.slow'),
  },
  stalled: {
    dot: 'bg-red-500',
    labelKey: tk('knowledgeBase:embedJobs.health.stalled'),
    ariaLabelKey: tk('knowledgeBase:embedJobs.healthAria.stalled'),
  },
  failed: {
    dot: 'bg-red-700',
    labelKey: tk('knowledgeBase:embedJobs.health.failed'),
    ariaLabelKey: tk('knowledgeBase:embedJobs.healthAria.failed'),
  },
} satisfies Record<JobHealthStatus, { dot: string; labelKey: string; ariaLabelKey: string }>

/**
 * Relative timestamp for the KB Processing Queue's "Last activity" line as a
 * translation key plus count ("Xs ago", "Xm ago", "Xh ago" with sensible
 * thresholds). Render with `t(result.key, { count: result.count })`.
 */
export function formatTimeAgo(
  timestampMs: number,
  now: number
):
  | { key: 'knowledgeBase:embedJobs.timeAgo.justNow'; count: number }
  | { key: 'knowledgeBase:embedJobs.timeAgo.seconds'; count: number }
  | { key: 'knowledgeBase:embedJobs.timeAgo.minutes'; count: number }
  | { key: 'knowledgeBase:embedJobs.timeAgo.hours'; count: number } {
  const seconds = Math.max(0, Math.floor((now - timestampMs) / 1000))
  if (seconds < 5) return { key: tk('knowledgeBase:embedJobs.timeAgo.justNow'), count: seconds }
  if (seconds < 60) return { key: tk('knowledgeBase:embedJobs.timeAgo.seconds'), count: seconds }
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return { key: tk('knowledgeBase:embedJobs.timeAgo.minutes'), count: minutes }
  const hours = Math.floor(minutes / 60)
  return { key: tk('knowledgeBase:embedJobs.timeAgo.hours'), count: hours }
}

/**
 * Convenience wrapper that resolves a job's health status without the caller
 * having to remember to pass `now`. Mostly for ergonomic frontend use.
 */
export function computeJobHealthNow(
  input: Omit<Parameters<typeof computeJobHealth>[0], 'now'>
): JobHealthStatus {
  return computeJobHealth({ ...input, now: Date.now() })
}
