import KVStore from '#models/kv_store'

/**
 * The AI assistant's display name is shared with every Inertia page, so it is
 * cached at module scope for 60 seconds. SystemService.updateSetting calls
 * invalidateAssistantNameCache() when the name changes, so the common case
 * takes effect immediately; the TTL bounds staleness if that is ever missed.
 */
const CACHE_TTL_MS = 60_000
const DEFAULT_ASSISTANT_NAME = 'AI Assistant'

let assistantNameCache: { value: string; expiresAt: number } | null = null

export function invalidateAssistantNameCache() {
  assistantNameCache = null
}

export async function getAssistantName(): Promise<string> {
  const now = Date.now()
  if (assistantNameCache && now < assistantNameCache.expiresAt) {
    return assistantNameCache.value
  }
  const customName = await KVStore.getValue('ai.assistantCustomName')
  const value = customName && customName.trim() ? customName : DEFAULT_ASSISTANT_NAME
  assistantNameCache = { value, expiresAt: now + CACHE_TTL_MS }
  return value
}
