import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { formatDate, formatNumber } from '~/i18n'
import FileUploader from '~/components/file-uploader'
import StyledButton from '~/components/StyledButton'
import type { DynamicIconName } from '~/lib/icons'
import StyledSectionHeader from '~/components/StyledSectionHeader'
import StyledTable from '~/components/StyledTable'
import { useNotifications } from '~/context/NotificationContext'
import api from '~/lib/api'
import {
  groupAndSortKbFiles,
  UNCATEGORIZED_COLLECTION_KEY,
  type KbFileGroup,
  type KbFileSort,
  type KbFileSortKey,
} from '~/lib/kb_file_grouping'
import type { KbIngestStateValue } from '../../../types/kb_ingest_state'
import { formatBytes } from '~/lib/util'
import {
  IconArrowsSort,
  IconChevronDown,
  IconChevronRight,
  IconDownload,
  IconEye,
  IconSortAscending,
  IconSortDescending,
  IconX,
} from '@tabler/icons-react'
import { useModals } from '~/context/ModalContext'
import StyledModal from '../StyledModal'
import ActiveEmbedJobs from '~/components/ActiveEmbedJobs'
import { SERVICE_NAMES } from '../../../constants/service_names'
import CollectionsManager from './CollectionsManager'
import { KB_COLLECTIONS } from '../../../constants/kb_collections'
import CollectionCombobox from './CollectionCombobox'
import Switch from '~/components/inputs/Switch'

interface KnowledgeBaseModalProps {
  aiAssistantName?: string
  onClose: () => void
}

// File extensions the in-browser viewer can render. Must stay in sync with
// `RagService.VIEWABLE_TEXT_EXTENSIONS` -- anything outside this set falls back
// to Download.
const VIEWABLE_EXTENSIONS = new Set([
  'md',
  'txt',
  'csv',
  'json',
  'yaml',
  'yml',
  'toml',
  'xml',
  'html',
])

function isViewableExtension(filename: string): boolean {
  const ext = filename.split('.').at(-1)?.toLowerCase() ?? ''
  return VIEWABLE_EXTENSIONS.has(ext)
}

function renderSortHeader(
  label: string,
  key: KbFileSortKey,
  sort: KbFileSort,
  setSort: (s: KbFileSort) => void
): React.ReactNode {
  const active = sort.key === key
  const Icon = !active
    ? IconArrowsSort
    : sort.direction === 'asc'
      ? IconSortAscending
      : IconSortDescending
  return (
    <button
      type="button"
      className="inline-flex items-center gap-1 text-left hover:text-text-primary transition-colors"
      onClick={() => {
        if (!active) {
          setSort({ key, direction: 'asc' })
        } else {
          setSort({ key, direction: sort.direction === 'asc' ? 'desc' : 'asc' })
        }
      }}
    >
      <span>{label}</span>
      <Icon
        size={14}
        className={active ? 'text-text-primary' : 'text-text-muted'}
        aria-hidden="true"
      />
    </button>
  )
}

/**
 * Compact label for the per-row ingestion state. Files that exist in Qdrant
 * with no `kb_ingest_state` row (`state === null`) are legacy/pre-RFC-883
 * installs whose chunks are real, so we display them as "Indexed" rather than
 * surfacing the absent-row detail. Admin-docs group has no pill (the "Managed
 * by NOMAD" message in the action column carries the same signal).
 */
function renderStatePill(record: KbFileGroup, t: TFunction): React.ReactNode {
  if (record.bucket === 'admin_docs') return null
  const effective: KbIngestStateValue = record.state ?? 'indexed'

  const base = 'inline-flex items-center text-xs font-medium rounded px-2 py-0.5 border'
  switch (effective) {
    case 'indexed':
      return (
        <span
          className={`${base} text-green-700 bg-green-50 border-green-200 dark:text-green-300 dark:bg-green-950/40 dark:border-green-800`}
        >
          {t('knowledgeBase:modal.state.indexed')}
        </span>
      )
    case 'pending_decision':
    case 'browse_only':
      return (
        <span className={`${base} text-text-secondary bg-surface-secondary border-border-subtle`}>
          {t('knowledgeBase:modal.state.notIndexed')}
        </span>
      )
    case 'failed':
      return (
        <span
          className={`${base} text-red-700 bg-red-50 border-red-200 dark:text-red-300 dark:bg-red-950/40 dark:border-red-800`}
        >
          {t('knowledgeBase:modal.state.failed')}
        </span>
      )
    case 'stalled':
      return (
        <span
          className={`${base} text-amber-700 bg-amber-50 border-amber-200 dark:text-amber-300 dark:bg-amber-950/40 dark:border-amber-800`}
        >
          {t('knowledgeBase:modal.state.stalled')}
        </span>
      )
  }
}

type RowAction =
  | { kind: 'index'; label: string; force: boolean; variant: 'primary'; icon: DynamicIconName }
  | { kind: 'reembed'; label: string; force: true; variant: 'secondary'; icon: DynamicIconName }

/**
 * Pick the single adaptive per-row action button. Returns null when no action
 * makes sense for the current state (e.g. healthy indexed file with no
 * warnings -- bulk Re-embed All covers that case). `hasWarnings` lets us
 * surface a Re-embed affordance specifically when a file *looks* indexed but
 * has zero chunks or a stalled-mid-ingestion warning attached.
 */
function pickRowAction(record: KbFileGroup, hasWarnings: boolean, t: TFunction): RowAction | null {
  if (record.bucket === 'admin_docs') return null
  const effective: KbIngestStateValue = record.state ?? 'indexed'
  switch (effective) {
    case 'indexed':
      return hasWarnings
        ? {
            kind: 'reembed',
            label: t('knowledgeBase:modal.actions.reembed'),
            force: true,
            variant: 'secondary',
            icon: 'IconRefreshAlert',
          }
        : null
    case 'pending_decision':
      return {
        kind: 'index',
        label: t('knowledgeBase:modal.actions.index'),
        force: false,
        variant: 'primary',
        icon: 'IconDownload',
      }
    case 'browse_only':
      return {
        kind: 'index',
        label: t('knowledgeBase:modal.actions.index'),
        force: true,
        variant: 'primary',
        icon: 'IconDownload',
      }
    case 'failed':
    case 'stalled':
      return {
        kind: 'index',
        label: t('knowledgeBase:modal.actions.retry'),
        force: true,
        variant: 'primary',
        icon: 'IconRefresh',
      }
  }
}

export default function KnowledgeBaseModal({
  aiAssistantName: aiAssistantNameProp,
  onClose,
}: KnowledgeBaseModalProps) {
  const { t } = useTranslation()
  const aiAssistantName = aiAssistantNameProp ?? t('knowledgeBase:modal.assistantFallback')
  const { addNotification } = useNotifications()
  const [files, setFiles] = useState<File[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [uploadCollection, setUploadCollection] = useState<string>('')
  const [collectionFilter, setCollectionFilter] = useState<string>('All')
  const [manageCollectionsOpen, setManageCollectionsOpen] = useState(false)
  const [confirmDeleteSource, setConfirmDeleteSource] = useState<string | null>(null)
  const [confirmReembed, setConfirmReembed] = useState<{
    source: string
    displayName: string
  } | null>(null)
  const [bulkMode, setBulkMode] = useState<null | 'reembed' | 'reset'>(null)
  const [resetTyped, setResetTyped] = useState('')
  const [sort, setSort] = useState<KbFileSort>({ key: 'name', direction: 'asc' })
  // KB-collection group keys (see UNCATEGORIZED_COLLECTION_KEY) whose member
  // files are currently expanded into individual rows. Collapsed by default
  // so grouping actually declutters the panel.
  const [expandedCollections, setExpandedCollections] = useState<Set<string>>(new Set())
  const [viewerSource, setViewerSource] = useState<string | null>(null)
  const fileUploaderRef = useRef<React.ComponentRef<typeof FileUploader>>(null)
  const { openModal, closeModal } = useModals()
  const queryClient = useQueryClient()

  const [isStartingQdrant, setIsStartingQdrant] = useState(false)

  const { data: healthStatus } = useQuery({
    queryKey: ['qdrantHealth'],
    queryFn: () => api.checkRAGHealth(),
    refetchInterval: isStartingQdrant ? 3_000 : 30_000,
  })
  const qdrantOffline = healthStatus?.online === false

  useEffect(() => {
    if (!qdrantOffline) setIsStartingQdrant(false)
  }, [qdrantOffline])

  const { data: storedFiles = [], isLoading: isLoadingFiles } = useQuery({
    queryKey: ['storedFiles'],
    queryFn: () => api.getStoredRAGFiles(),
    select: (data) => data || [],
  })

  const { data: knownCollections = [] } = useQuery({
    queryKey: ['kbCollections'],
    queryFn: () => api.getKnowledgeCollections(),
    select: (data) => data?.collections ?? [],
  })

  const comboboxOptions = useMemo(() => {
    return Array.from(new Set([...KB_COLLECTIONS, ...knownCollections])).sort()
  }, [knownCollections])

  // Per-file conditional warnings (RFC #883 section 6). `ok: false` means the
  // computation itself failed (Qdrant/DB/FS) -- distinct from `ok: true` with
  // an empty map, which means everything is healthy. We surface the failure
  // explicitly so a silent backend failure doesn't masquerade as health.
  const { data: warningsResult } = useQuery({
    queryKey: ['kbFileWarnings'],
    queryFn: () => api.getKbFileWarnings(),
    refetchInterval: 30_000,
  })
  const fileWarnings = warningsResult?.warnings ?? {}
  const warningsUnavailable = warningsResult !== undefined && warningsResult.ok === false

  // Global auto-index policy. KVStore returns `null` for an unset key, which
  // we treat as 'Always' for backward compatibility with installs that predate
  // this UI. The user can opt into Manual mode from the toggle below.
  const { data: ingestPolicySetting } = useQuery({
    queryKey: ['ingestPolicy'],
    queryFn: () => api.getSetting('rag.defaultIngestPolicy'),
  })
  const ingestPolicy: 'Always' | 'Manual' =
    ingestPolicySetting?.value === 'Manual' ? 'Manual' : 'Always'

  const updateIngestPolicyMutation = useMutation({
    mutationFn: (policy: 'Always' | 'Manual') =>
      api.updateSetting('rag.defaultIngestPolicy', policy),
    onSuccess: (_data, policy) => {
      queryClient.invalidateQueries({ queryKey: ['ingestPolicy'] })
      addNotification({
        type: 'success',
        message:
          policy === 'Always'
            ? t('knowledgeBase:modal.notifications.policyAlways')
            : t('knowledgeBase:modal.notifications.policyManual'),
      })
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        message: error?.message || t('knowledgeBase:modal.notifications.policyFailed'),
      })
    },
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploadDocument(file, uploadCollection || undefined),
  })

  const updateCollectionMutation = useMutation({
    mutationFn: ({ source, collection }: { source: string; collection: string }) =>
      api.updateFileCollection(source, collection || null),
    onSuccess: (data) => {
      addNotification({ type: 'success', message: data?.message || t('knowledgeBase:modal.notifications.collectionUpdated') })
      queryClient.invalidateQueries({ queryKey: ['storedFiles'] })
      queryClient.invalidateQueries({ queryKey: ['kbCollections'] })
    },
    onError: (error: any) => {
      addNotification({ type: 'error', message: error?.message || t('knowledgeBase:modal.notifications.collectionUpdateFailed') })
    },
  })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ source, active }: { source: string; active: boolean }) =>
      api.setFileActive(source, active),
    onSuccess: (data) => {
      addNotification({ type: 'success', message: data?.message || t('knowledgeBase:modal.notifications.activeUpdated') })
      queryClient.invalidateQueries({ queryKey: ['storedFiles'] })
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        message: error?.message || t('knowledgeBase:modal.notifications.activeUpdateFailed'),
      })
    },
  })

  const toggleCollectionActiveMutation = useMutation({
    mutationFn: ({ collection, active }: { collection: string | null; active: boolean }) =>
      api.setKnowledgeCollectionActive(collection, active),
    onSuccess: (data) => {
      addNotification({
        type: 'success',
        message: data?.message || t('knowledgeBase:modal.notifications.collectionActiveUpdated'),
      })
      queryClient.invalidateQueries({ queryKey: ['storedFiles'] })
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        message: error?.message || t('knowledgeBase:modal.notifications.collectionActiveUpdateFailed'),
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (source: string) => api.deleteRAGFile(source),
    onSuccess: () => {
      addNotification({ type: 'success', message: t('knowledgeBase:modal.notifications.fileRemoved') })
      setConfirmDeleteSource(null)
      queryClient.invalidateQueries({ queryKey: ['storedFiles'] })
    },
    onError: (error: any) => {
      addNotification({ type: 'error', message: error?.message || t('knowledgeBase:modal.notifications.deleteFailed') })
      setConfirmDeleteSource(null)
    },
  })

  const embedMutation = useMutation({
    mutationFn: ({ source, force }: { source: string; force: boolean }) =>
      api.embedSingleRAGFile(source, force),
    onSuccess: (data) => {
      addNotification({
        type: 'success',
        message: data?.message || t('knowledgeBase:modal.notifications.fileQueued'),
      })
      setConfirmReembed(null)
      queryClient.invalidateQueries({ queryKey: ['storedFiles'] })
      queryClient.invalidateQueries({ queryKey: ['embed-jobs'] })
      queryClient.invalidateQueries({ queryKey: ['kbFileWarnings'] })
    },
    onError: (error: any) => {
      addNotification({ type: 'error', message: error?.message || t('knowledgeBase:modal.notifications.queueFailed') })
      setConfirmReembed(null)
    },
  })

  const cleanupFailedMutation = useMutation({
    mutationFn: () => api.cleanupFailedEmbedJobs(),
    onSuccess: (data) => {
      addNotification({ type: 'success', message: data?.message || t('knowledgeBase:modal.notifications.failedJobsCleaned') })
      queryClient.invalidateQueries({ queryKey: ['failedEmbedJobs'] })
    },
    onError: (error: any) => {
      addNotification({ type: 'error', message: error?.message || t('knowledgeBase:modal.notifications.cleanupFailed') })
    },
  })

  const cancelAllMutation = useMutation({
    mutationFn: () => api.cancelAllEmbedJobs(),
    onSuccess: (data) => {
      addNotification({
        type: 'success',
        message: data?.message || t('knowledgeBase:modal.notifications.allJobsCancelled'),
      })
      queryClient.invalidateQueries({ queryKey: ['embed-jobs'] })
      queryClient.invalidateQueries({ queryKey: ['failedEmbedJobs'] })
      queryClient.invalidateQueries({ queryKey: ['storedFiles'] })
      queryClient.invalidateQueries({ queryKey: ['kbFileWarnings'] })
    },
    onError: (error: any) => {
      addNotification({ type: 'error', message: error?.message || t('knowledgeBase:modal.notifications.cancelFailed') })
    },
  })

  const startQdrantMutation = useMutation({
    mutationFn: () => api.affectService(SERVICE_NAMES.QDRANT, 'start'),
    onSuccess: () => {
      setIsStartingQdrant(true)
      queryClient.invalidateQueries({ queryKey: ['qdrantHealth'] })
    },
    onError: (error: any) => {
      addNotification({ type: 'error', message: error?.message || t('knowledgeBase:modal.notifications.startQdrantFailed') })
    },
  })

  const syncMutation = useMutation({
    mutationFn: () => api.syncRAGStorage(),
    onSuccess: (data) => {
      addNotification({
        type: 'success',
        message:
          data?.message || t('knowledgeBase:modal.notifications.syncSuccess'),
      })
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        message: error?.message || t('knowledgeBase:modal.notifications.syncFailed'),
      })
    },
  })

  const reembedMutation = useMutation({
    mutationFn: () => api.reembedAllRAG(),
    onSuccess: (data) => {
      addNotification({
        type: data?.success ? 'success' : 'error',
        message: data?.message || t('knowledgeBase:modal.notifications.reembedDone'),
      })
      queryClient.invalidateQueries({ queryKey: ['storedFiles'] })
      queryClient.invalidateQueries({ queryKey: ['embed-jobs'] })
      setBulkMode(null)
      setResetTyped('')
    },
    onError: () => {
      addNotification({ type: 'error', message: t('knowledgeBase:modal.notifications.reembedFailed') })
      setBulkMode(null)
    },
  })

  const resetMutation = useMutation({
    mutationFn: () => api.resetAndRebuildRAG(),
    onSuccess: (data) => {
      addNotification({
        type: data?.success ? 'success' : 'error',
        message: data?.message || t('knowledgeBase:modal.notifications.resetDone'),
      })
      queryClient.invalidateQueries({ queryKey: ['storedFiles'] })
      queryClient.invalidateQueries({ queryKey: ['embed-jobs'] })
      setBulkMode(null)
      setResetTyped('')
    },
    onError: () => {
      addNotification({ type: 'error', message: t('knowledgeBase:modal.notifications.resetFailed') })
      setBulkMode(null)
    },
  })

  const bulkBusy = reembedMutation.isPending || resetMutation.isPending

  // Grouped rows (admin docs, KB-collection headers) carry a translatable label;
  // individual file rows show the file name as is.
  const rowName = (record: KbFileGroup): string => {
    const label = record.label
    if (!label) return record.displayName
    return t(label.key, { count: label.count, name: 'name' in label ? label.name : undefined })
  }

  const handleUpload = async () => {
    if (files.length === 0) return
    setIsUploading(true)
    let successCount = 0
    const failedNames: string[] = []

    for (const file of files) {
      try {
        await uploadMutation.mutateAsync(file)
        successCount++
      } catch (error: any) {
        failedNames.push(file.name)
      }
    }

    setIsUploading(false)
    setFiles([])
    fileUploaderRef.current?.clear()
    queryClient.invalidateQueries({ queryKey: ['embed-jobs'] })

    if (successCount > 0) {
      addNotification({
        type: 'success',
        message: t('knowledgeBase:modal.notifications.filesQueued', { count: successCount }),
      })
    }
    for (const name of failedNames) {
      addNotification({
        type: 'error',
        message: t('knowledgeBase:modal.notifications.uploadFailed', { name }),
      })
    }
  }

  const toggleCollectionExpanded = (key: string) => {
    setExpandedCollections((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  const handleConfirmCancelAll = () => {
    openModal(
      <StyledModal
        title={t('knowledgeBase:modal.confirmCancelAll.title')}
        onConfirm={() => {
          cancelAllMutation.mutate()
          closeModal('confirm-cancel-all-modal')
        }}
        onCancel={() => closeModal('confirm-cancel-all-modal')}
        open={true}
        confirmText={t('knowledgeBase:modal.confirmCancelAll.confirm')}
        cancelText={t('knowledgeBase:modal.confirmCancelAll.cancel')}
        confirmVariant="danger"
      >
        <p className="text-text-primary">
          <Trans
            i18nKey="knowledgeBase:modal.confirmCancelAll.body"
            components={{ bold: <strong /> }}
          />
        </p>
      </StyledModal>,
      'confirm-cancel-all-modal'
    )
  }

  const handleConfirmSync = () => {
    openModal(
      <StyledModal
        title={t('knowledgeBase:modal.confirmSync.title')}
        onConfirm={() => {
          syncMutation.mutate()
          closeModal('confirm-sync-modal')
        }}
        onCancel={() => closeModal('confirm-sync-modal')}
        open={true}
        confirmText={t('knowledgeBase:modal.confirmSync.confirm')}
        cancelText={t('knowledgeBase:modal.actions.cancel')}
        confirmVariant="primary"
      >
        <p className="text-text-primary">
          {t('knowledgeBase:modal.confirmSync.body')}
        </p>
      </StyledModal>,
      'confirm-sync-modal'
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-sm transition-opacity">
      {/* 6xl, not 5xl: the Active column added ~57px and put the table back over the
          modal width, which is the exact defect #1198 fixed (the Delete button falls
          off the right edge at every viewport). Measured on NOMAD3: table 1018px
          against 961px of usable width at 5xl. */}
      <div className="bg-surface-primary rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-border-subtle shrink-0">
          <h2 className="text-2xl font-semibold text-text-primary">{t('knowledgeBase:modal.title')}</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-surface-secondary rounded-lg transition-colors"
          >
            <IconX className="h-6 w-6 text-text-muted" />
          </button>
        </div>
        <div className="overflow-y-auto flex-1 p-6">
          {qdrantOffline && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm dark:bg-red-950 dark:border-red-800 dark:text-red-300 flex items-center justify-between gap-4">
              <span>
                <Trans
                  i18nKey="knowledgeBase:modal.qdrantOffline"
                  components={{ bold: <strong /> }}
                />
              </span>
              <StyledButton
                variant="danger"
                size="sm"
                onClick={() => startQdrantMutation.mutate()}
                loading={startQdrantMutation.isPending || isStartingQdrant}
                disabled={startQdrantMutation.isPending || isStartingQdrant}
              >
                {isStartingQdrant
                  ? t('knowledgeBase:modal.startingQdrant')
                  : t('knowledgeBase:modal.startQdrant')}
              </StyledButton>
            </div>
          )}
          <div className="bg-surface-primary rounded-lg border shadow-md overflow-hidden">
            <div className="p-6">
              <FileUploader
                ref={fileUploaderRef}
                minFiles={1}
                maxFiles={5}
                onUpload={(uploadedFiles) => {
                  setFiles(Array.from(uploadedFiles))
                }}
              />
              <div className="flex justify-center items-center gap-4 my-6">
                <label className="flex items-center gap-2 text-sm text-text-secondary">
                  {t('knowledgeBase:modal.collectionLabel')}
                  <CollectionCombobox
                    value={uploadCollection}
                    onChange={setUploadCollection}
                    options={comboboxOptions}
                    className="w-48"
                  />
                </label>
                <StyledButton
                  variant="primary"
                  size="lg"
                  icon="IconUpload"
                  onClick={handleUpload}
                  disabled={files.length === 0 || isUploading || qdrantOffline}
                  loading={isUploading}
                >
                  {t('knowledgeBase:modal.upload')}
                </StyledButton>
              </div>
            </div>
            <div className="border-t bg-surface-primary p-6">
              <h3 className="text-lg font-semibold text-desert-green mb-4">
                {t('knowledgeBase:modal.why.title')}
              </h3>
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <div className="shrink-0 w-6 h-6 rounded-full bg-desert-green text-white flex items-center justify-center text-sm font-bold">
                    1
                  </div>
                  <div>
                    <p className="font-medium text-desert-stone-dark">
                      {t('knowledgeBase:modal.why.assistantTitle', { name: aiAssistantName })}
                    </p>
                    <p className="text-sm text-desert-stone">
                      {t('knowledgeBase:modal.why.assistantBody', { name: aiAssistantName })}
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="shrink-0 w-6 h-6 rounded-full bg-desert-green text-white flex items-center justify-center text-sm font-bold">
                    2
                  </div>
                  <div>
                    <p className="font-medium text-desert-stone-dark">
                      {t('knowledgeBase:modal.why.ocrTitle')}
                    </p>
                    <p className="text-sm text-desert-stone">
                      {t('knowledgeBase:modal.why.ocrBody')}
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="shrink-0 w-6 h-6 rounded-full bg-desert-green text-white flex items-center justify-center text-sm font-bold">
                    3
                  </div>
                  <div>
                    <p className="font-medium text-desert-stone-dark">
                      {t('knowledgeBase:modal.why.libraryTitle')}
                    </p>
                    <p className="text-sm text-desert-stone">
                      {t('knowledgeBase:modal.why.libraryBody', { name: aiAssistantName })}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="my-8 p-4 rounded-lg border border-border-subtle bg-surface-secondary">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex-1 min-w-[14rem]">
                <p className="text-sm font-medium text-text-primary">
                  {t('knowledgeBase:modal.policy.question')}
                </p>
                <p className="text-xs text-text-muted mt-1">
                  {t('knowledgeBase:modal.policy.hint')}
                </p>
              </div>
              <div
                role="radiogroup"
                aria-label={t('knowledgeBase:modal.policy.ariaLabel')}
                className="inline-flex rounded-md overflow-hidden border border-border-subtle"
              >
                {(['Always', 'Manual'] as const).map((option) => {
                  const isActive = ingestPolicy === option
                  return (
                    <button
                      key={option}
                      type="button"
                      role="radio"
                      aria-checked={isActive}
                      onClick={() => !isActive && updateIngestPolicyMutation.mutate(option)}
                      disabled={updateIngestPolicyMutation.isPending}
                      className={`px-4 py-2 text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-desert-green text-white'
                          : 'bg-surface-primary text-text-secondary hover:bg-surface-tertiary'
                      } ${updateIngestPolicyMutation.isPending ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                    >
                      {option === 'Always'
                        ? t('knowledgeBase:modal.policy.always')
                        : t('knowledgeBase:modal.policy.manual')}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          <div className="my-8">
            <div className="flex items-center justify-between mb-4 gap-2 flex-wrap">
              <StyledSectionHeader title={t('knowledgeBase:embedJobs.title')} className="!mb-0" />
              <div className="flex items-center gap-2 flex-wrap">
                <StyledButton
                  variant="danger"
                  size="md"
                  icon="IconTrash"
                  onClick={() => cleanupFailedMutation.mutate()}
                  loading={cleanupFailedMutation.isPending}
                  disabled={cleanupFailedMutation.isPending || qdrantOffline}
                >
                  {t('knowledgeBase:modal.queue.cleanUpFailed')}
                </StyledButton>
                <StyledButton
                  variant="danger"
                  size="md"
                  icon="IconPlayerStop"
                  onClick={handleConfirmCancelAll}
                  loading={cancelAllMutation.isPending}
                  disabled={cancelAllMutation.isPending}
                  title={t('knowledgeBase:modal.queue.cancelAllTitle')}
                >
                  {t('knowledgeBase:modal.queue.cancelAll')}
                </StyledButton>
              </div>
            </div>
            <ActiveEmbedJobs withHeader={false} />
          </div>

          <div className="my-12">
            <div className="flex items-center justify-between mb-6 gap-2 flex-wrap">
              <StyledSectionHeader title={t('knowledgeBase:modal.stored.title')} className="!mb-0" />
              <div className="flex items-center gap-2 flex-wrap">
                <label className="flex items-center gap-2 text-sm text-text-secondary">
                  {t('knowledgeBase:modal.stored.searchIn')}
                  <select
                    value={collectionFilter}
                    onChange={(e) => setCollectionFilter(e.target.value)}
                    className="rounded border border-border-subtle bg-surface-primary px-3 py-2 text-text-primary"
                  >
                    <option value="All">{t('knowledgeBase:modal.stored.all')}</option>
                    {knownCollections.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                    <option value={UNCATEGORIZED_COLLECTION_KEY}>
                      {t('knowledgeBase:modal.stored.uncategorized')}
                    </option>
                  </select>
                </label>
                <StyledButton
                  variant="secondary"
                  size="md"
                  icon="IconSettings"
                  onClick={() => setManageCollectionsOpen(true)}
                >
                  {t('knowledgeBase:modal.stored.manageCollections')}
                </StyledButton>
                <StyledButton
                  variant="danger"
                  size="md"
                  icon="IconAlertTriangle"
                  onClick={() => {
                    setResetTyped('')
                    setBulkMode('reset')
                  }}
                  disabled={isUploading || qdrantOffline || bulkBusy}
                  loading={resetMutation.isPending}
                  title={t('knowledgeBase:modal.stored.resetRebuildTitle')}
                >
                  {t('knowledgeBase:modal.stored.resetRebuild')}
                </StyledButton>
                <StyledButton
                  variant="secondary"
                  size="md"
                  icon="IconRefreshAlert"
                  onClick={() => setBulkMode('reembed')}
                  disabled={isUploading || qdrantOffline || bulkBusy || storedFiles.length === 0}
                  loading={reembedMutation.isPending}
                  title={t('knowledgeBase:modal.stored.reembedAllTitle')}
                >
                  {t('knowledgeBase:modal.stored.reembedAll')}
                </StyledButton>
                <StyledButton
                  variant="secondary"
                  size="md"
                  icon="IconRefresh"
                  onClick={handleConfirmSync}
                  disabled={syncMutation.isPending || isUploading || qdrantOffline || bulkBusy}
                  loading={syncMutation.isPending || isUploading}
                  title={t('knowledgeBase:modal.stored.syncStorageTitle')}
                >
                  {t('knowledgeBase:modal.stored.syncStorage')}
                </StyledButton>
              </div>
            </div>
            {warningsUnavailable && (
              <div className="mb-4 inline-flex items-center gap-2 text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded px-3 py-2">
                <span aria-hidden="true">⚠</span>
                <span>{t('knowledgeBase:modal.stored.warningsUnavailable')}</span>
              </div>
            )}
            <StyledTable<KbFileGroup>
              className="font-semibold"
              rowLines={true}
              columns={[
                {
                  accessor: 'source',
                  title: renderSortHeader(t('knowledgeBase:modal.columns.fileName'), 'name', sort, setSort),
                  render(record) {
                    if (record.isCollectionHeader) {
                      const key = record.collection ?? UNCATEGORIZED_COLLECTION_KEY
                      const expanded = expandedCollections.has(key)
                      return (
                        <button
                          type="button"
                          className="inline-flex items-center gap-1.5 font-semibold text-text-primary hover:text-desert-green transition-colors"
                          onClick={() => toggleCollectionExpanded(key)}
                          aria-expanded={expanded}
                        >
                          {expanded ? (
                            <IconChevronDown
                              size={16}
                              className="text-text-muted"
                              aria-hidden="true"
                            />
                          ) : (
                            <IconChevronRight
                              size={16}
                              className="text-text-muted"
                              aria-hidden="true"
                            />
                          )}
                          {rowName(record)}
                        </button>
                      )
                    }
                    const warnings = fileWarnings[record.source] ?? []
                    const pill = renderStatePill(record, t)
                    return (
                      <div className="flex flex-col gap-1.5">
                        <span className="text-text-primary">
                          {rowName(record)}
                        </span>
                        {(pill || warnings.length > 0) && (
                          <div className="flex flex-wrap items-center gap-1.5">
                            {pill}
                            {warnings.map((w, i) => (
                              <span
                                key={i}
                                className="inline-flex items-center gap-1.5 self-start text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded px-2 py-0.5"
                              >
                                <span aria-hidden="true">⚠</span>
                                {w.kind === 'zero_chunks' && (
                                  <span>{t('knowledgeBase:modal.warnings.zeroChunks')}</span>
                                )}
                                {w.kind === 'partial_stall' && (
                                  <span>
                                    {t('knowledgeBase:modal.warnings.partialStall', {
                                      embedded: formatNumber(w.chunksEmbedded),
                                      expected: formatNumber(w.chunksExpected),
                                    })}
                                  </span>
                                )}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )
                  },
                },
                {
                  accessor: 'size',
                  title: renderSortHeader(t('knowledgeBase:modal.columns.size'), 'size', sort, setSort),
                  className: 'whitespace-nowrap',
                  render(record) {
                    if (record.bucket === 'admin_docs' || record.size === null) {
                      return <span className="text-text-muted">—</span>
                    }
                    return <span className="text-text-secondary">{formatBytes(record.size)}</span>
                  },
                },
                {
                  accessor: 'uploadedAt',
                  title: renderSortHeader(
                    t('knowledgeBase:modal.columns.uploaded'),
                    'uploadedAt',
                    sort,
                    setSort
                  ),
                  className: 'whitespace-nowrap',
                  render(record) {
                    if (record.bucket === 'admin_docs' || !record.uploadedAt) {
                      return <span className="text-text-muted">—</span>
                    }
                    const d = new Date(record.uploadedAt)
                    return (
                      <span className="text-text-secondary" title={d.toISOString()}>
                        {formatDate(d)}
                      </span>
                    )
                  },
                },
                {
                  accessor: 'collection',
                  title: t('knowledgeBase:modal.columns.collection'),
                  className: 'whitespace-nowrap',
                  noTruncate: true,
                  render(record) {
                    if (record.bucket === 'admin_docs' || record.isCollectionHeader) {
                      return <span className="text-text-muted">—</span>
                    }
                    const isSaving =
                      updateCollectionMutation.isPending &&
                      updateCollectionMutation.variables?.source === record.source
                    return (
                      <CollectionCombobox
                        value={record.collection ?? ''}
                        onChange={(val) =>
                          updateCollectionMutation.mutate({
                            source: record.source,
                            collection: val,
                          })
                        }
                        options={comboboxOptions}
                        disabled={isSaving}
                        className="w-40"
                      />
                    )
                  },
                },
                {
                  accessor: 'active',
                  title: t('knowledgeBase:modal.columns.active'),
                  render(record) {
                    if (record.bucket === 'admin_docs') {
                      return <span className="text-text-muted">—</span>
                    }
                    if (record.isCollectionHeader) {
                      const isSaving =
                        toggleCollectionActiveMutation.isPending &&
                        toggleCollectionActiveMutation.variables?.collection === record.collection
                      return (
                        <Switch
                          checked={record.collectionActiveState === 'all-active'}
                          indeterminate={record.collectionActiveState === 'mixed'}
                          onChange={(val) =>
                            toggleCollectionActiveMutation.mutate({
                              collection: record.collection,
                              active: val,
                            })
                          }
                          disabled={isSaving}
                        />
                      )
                    }
                    const isSaving =
                      toggleActiveMutation.isPending &&
                      toggleActiveMutation.variables?.source === record.source
                    return (
                      <Switch
                        checked={record.active}
                        onChange={(val) =>
                          toggleActiveMutation.mutate({ source: record.source, active: val })
                        }
                        disabled={isSaving}
                      />
                    )
                  },
                },
                {
                  accessor: 'source',
                  title: '',
                  render(record) {
                    if (record.bucket === 'admin_docs') {
                      return (
                        <div className="flex justify-end">
                          <span className="text-sm text-text-muted italic">
                            {t('knowledgeBase:modal.actions.managedByNomad')}
                          </span>
                        </div>
                      )
                    }
                    if (record.isCollectionHeader) {
                      return null
                    }

                    const isConfirming = confirmDeleteSource === record.source
                    const isDeleting =
                      deleteMutation.isPending && confirmDeleteSource === record.source
                    if (isConfirming) {
                      return (
                        <div className="flex items-center gap-2 justify-end">
                          <span className="text-sm text-text-secondary">
                            {t('knowledgeBase:modal.actions.confirmRemove')}
                          </span>
                          <StyledButton
                            variant="danger"
                            size="sm"
                            onClick={() => deleteMutation.mutate(record.source)}
                            disabled={isDeleting}
                          >
                            {isDeleting
                              ? t('knowledgeBase:modal.actions.deleting')
                              : t('knowledgeBase:modal.actions.confirm')}
                          </StyledButton>
                          <StyledButton
                            variant="ghost"
                            size="sm"
                            onClick={() => setConfirmDeleteSource(null)}
                            disabled={isDeleting}
                          >
                            {t('knowledgeBase:modal.actions.cancel')}
                          </StyledButton>
                        </div>
                      )
                    }

                    const warnings = fileWarnings[record.source] ?? []
                    const action = pickRowAction(record, warnings.length > 0, t)
                    const actionPendingForThisRow =
                      embedMutation.isPending && embedMutation.variables?.source === record.source

                    const canView =
                      record.isUserUpload &&
                      isViewableExtension(record.displayName) &&
                      record.size !== null
                    const canDownload = record.isUserUpload && record.size !== null

                    return (
                      <div className="flex justify-end items-center gap-2">
                        {action && (
                          <StyledButton
                            variant={action.variant}
                            size="sm"
                            icon={action.icon}
                            onClick={() => {
                              if (action.kind === 'reembed') {
                                setConfirmReembed({
                                  source: record.source,
                                  displayName: record.displayName,
                                })
                              } else {
                                embedMutation.mutate({ source: record.source, force: action.force })
                              }
                            }}
                            disabled={
                              qdrantOffline || deleteMutation.isPending || embedMutation.isPending
                            }
                            loading={actionPendingForThisRow}
                          >
                            {action.label}
                          </StyledButton>
                        )}
                        {canView && (
                          <StyledButton
                            variant="ghost"
                            size="sm"
                            icon="IconEye"
                            onClick={() => setViewerSource(record.source)}
                          >
                            {t('knowledgeBase:modal.actions.view')}
                          </StyledButton>
                        )}
                        {canDownload && (
                          <StyledButton
                            variant="ghost"
                            size="sm"
                            icon="IconDownload"
                            onClick={() => {
                              window.location.href = `/api/rag/files/download?source=${encodeURIComponent(record.source)}`
                            }}
                          >
                            {t('knowledgeBase:modal.actions.download')}
                          </StyledButton>
                        )}
                        <StyledButton
                          variant="danger"
                          size="sm"
                          icon="IconTrash"
                          onClick={() => setConfirmDeleteSource(record.source)}
                          disabled={deleteMutation.isPending || embedMutation.isPending}
                          loading={
                            deleteMutation.isPending && confirmDeleteSource === record.source
                          }
                        >
                          {t('knowledgeBase:modal.actions.delete')}
                        </StyledButton>
                      </div>
                    )
                  },
                },
              ]}
              data={groupAndSortKbFiles(
                collectionFilter === 'All'
                  ? storedFiles
                  : storedFiles.filter((f) =>
                      collectionFilter === UNCATEGORIZED_COLLECTION_KEY
                        ? f.collection === null
                        : f.collection === collectionFilter
                    ),
                sort,
                expandedCollections
              )}
              loading={isLoadingFiles}
            />
          </div>
        </div>
      </div>

      {bulkMode === 'reembed' && (
        <StyledModal
          title={t('knowledgeBase:modal.reembedAll.title')}
          open={true}
          confirmText={
            reembedMutation.isPending
              ? t('knowledgeBase:modal.reembedAll.confirming')
              : t('knowledgeBase:modal.reembedAll.confirm')
          }
          cancelText={t('knowledgeBase:modal.actions.cancel')}
          confirmVariant="primary"
          confirmLoading={reembedMutation.isPending}
          onConfirm={() => reembedMutation.mutate()}
          onCancel={() => setBulkMode(null)}
        >
          <div className="text-text-primary text-sm space-y-3 text-left">
            <p>
              <Trans
                i18nKey="knowledgeBase:modal.reembedAll.intro"
                count={storedFiles.length}
                components={{ bold: <strong /> }}
              />
            </p>
            <div className="rounded border border-border-subtle bg-surface-secondary p-3">
              <p className="font-semibold mb-1">{t('knowledgeBase:modal.reembedAll.purposeTitle')}</p>
              <p className="text-text-secondary">
                <Trans
                  i18nKey="knowledgeBase:modal.reembedAll.purposeBody"
                  components={{ em: <em /> }}
                />
              </p>
            </div>
            <div className="rounded border border-amber-300 bg-amber-50 dark:bg-amber-950 dark:border-amber-800 p-3 text-amber-900 dark:text-amber-200">
              <p className="font-semibold mb-1">{t('knowledgeBase:modal.reembedAll.headsUp')}</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>
                  {t('knowledgeBase:modal.reembedAll.durationWarning', {
                    count: storedFiles.length,
                  })}
                </li>
                <li>{t('knowledgeBase:modal.reembedAll.cpuWarning')}</li>
                <li>{t('knowledgeBase:modal.reembedAll.searchWarning')}</li>
                <li>{t('knowledgeBase:modal.reembedAll.busyWarning')}</li>
              </ul>
            </div>
          </div>
        </StyledModal>
      )}

      {bulkMode === 'reset' && (
        <StyledModal
          title={t('knowledgeBase:modal.reset.title')}
          open={true}
          confirmText={
            resetMutation.isPending
              ? t('knowledgeBase:modal.reset.confirming')
              : t('knowledgeBase:modal.reset.confirm')
          }
          cancelText={t('knowledgeBase:modal.actions.cancel')}
          confirmVariant="danger"
          confirmLoading={resetMutation.isPending}
          onConfirm={() => {
            if (resetTyped === 'RESET') resetMutation.mutate()
          }}
          onCancel={() => {
            setBulkMode(null)
            setResetTyped('')
          }}
        >
          <div className="text-text-primary text-sm space-y-3 text-left">
            <p>
              <Trans
                i18nKey="knowledgeBase:modal.reset.intro"
                count={storedFiles.length}
                components={{ bold: <strong />, code: <code /> }}
              />
            </p>
            <div className="rounded border border-border-subtle bg-surface-secondary p-3">
              <p className="font-semibold mb-1">{t('knowledgeBase:modal.reset.differenceTitle')}</p>
              <ul className="list-disc pl-5 space-y-1 text-text-secondary">
                <li>
                  <Trans
                    i18nKey="knowledgeBase:modal.reset.differenceReembed"
                    components={{ bold: <strong /> }}
                  />
                </li>
                <li>
                  <Trans
                    i18nKey="knowledgeBase:modal.reset.differenceReset"
                    components={{ bold: <strong /> }}
                  />
                </li>
              </ul>
            </div>
            <div className="rounded border border-red-300 bg-red-50 dark:bg-red-950 dark:border-red-800 p-3 text-red-900 dark:text-red-200">
              <p className="font-semibold mb-1">{t('knowledgeBase:modal.reset.destructiveTitle')}</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>{t('knowledgeBase:modal.reset.emptyWarning')}</li>
                <li>{t('knowledgeBase:modal.reset.missingCollectionWarning')}</li>
                <li>{t('knowledgeBase:modal.reset.busyWarning')}</li>
              </ul>
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">
                <Trans
                  i18nKey="knowledgeBase:modal.reset.typeToConfirm"
                  components={{ code: <code /> }}
                />
              </label>
              <input
                type="text"
                value={resetTyped}
                onChange={(e) => setResetTyped(e.target.value)}
                placeholder="RESET"
                autoFocus
                className="w-full rounded border border-border-subtle bg-surface-primary px-3 py-2 text-text-primary focus:outline-none focus:ring-2 focus:ring-red-500"
              />
              {resetTyped.length > 0 && resetTyped !== 'RESET' && (
                <p className="text-xs text-red-600 mt-1">
                  {t('knowledgeBase:modal.reset.typeExactly')}
                </p>
              )}
            </div>
          </div>
        </StyledModal>
      )}

      {confirmReembed && (
        <StyledModal
          title={t('knowledgeBase:modal.reembedFile.title')}
          open={true}
          confirmText={
            embedMutation.isPending
              ? t('knowledgeBase:modal.reembedFile.confirming')
              : t('knowledgeBase:modal.reembedFile.confirm')
          }
          cancelText={t('knowledgeBase:modal.actions.cancel')}
          confirmVariant="primary"
          confirmLoading={embedMutation.isPending}
          onConfirm={() => embedMutation.mutate({ source: confirmReembed.source, force: true })}
          onCancel={() => setConfirmReembed(null)}
        >
          <div className="text-text-primary text-sm space-y-3 text-left">
            <p>
              <Trans
                i18nKey="knowledgeBase:modal.reembedFile.body"
                values={{ name: confirmReembed.displayName }}
                components={{ bold: <strong /> }}
              />
            </p>
            <div className="rounded border border-amber-300 bg-amber-50 dark:bg-amber-950 dark:border-amber-800 p-3 text-amber-900 dark:text-amber-200">
              <p className="font-semibold mb-1">{t('knowledgeBase:modal.reembedFile.headsUp')}</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>{t('knowledgeBase:modal.reembedFile.durationWarning')}</li>
                <li>{t('knowledgeBase:modal.reembedFile.searchWarning')}</li>
                <li>{t('knowledgeBase:modal.reembedFile.busyWarning')}</li>
              </ul>
            </div>
          </div>
        </StyledModal>
      )}

      {viewerSource && (
        <FileViewerModal source={viewerSource} onClose={() => setViewerSource(null)} />
      )}

      {manageCollectionsOpen && (
        <CollectionsManager onClose={() => setManageCollectionsOpen(false)} />
      )}
    </div>
  )
}

function FileViewerModal({ source, onClose }: { source: string; onClose: () => void }) {
  const { t } = useTranslation()
  const { data, isLoading, isFetched } = useQuery({
    queryKey: ['rag', 'file-content', source],
    queryFn: () => api.getFileContent(source),
    staleTime: 60_000,
  })

  // Title falls back to the trailing path segment so the modal still has a
  // useful header while the fetch is in-flight or if it failed.
  const fallbackName = source.split(/[/\\]/).at(-1) ?? source
  const title = data?.fileName ?? fallbackName
  // `catchInternal` swallows errors and resolves to undefined, surfacing a
  // toast -- so the "couldn't load" branch is gated on a finished-but-empty
  // fetch rather than on react-query's `isError`.
  const showError = isFetched && !data

  return (
    <StyledModal
      title={title}
      open={true}
      onClose={onClose}
      onCancel={onClose}
      cancelText={t('knowledgeBase:modal.viewer.close')}
      large
    >
      <div className="text-left text-sm">
        {isLoading && <div className="text-text-secondary">{t('knowledgeBase:modal.viewer.loading')}</div>}
        {showError && (
          <div className="text-amber-700 dark:text-amber-300">
            {t('knowledgeBase:modal.viewer.error')}
          </div>
        )}
        {data && (
          <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded border border-border-subtle bg-surface-secondary p-3 font-mono text-xs text-text-primary">
            {data.content}
          </pre>
        )}
      </div>
    </StyledModal>
  )
}
