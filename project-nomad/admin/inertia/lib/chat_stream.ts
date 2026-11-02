import { tk } from '../i18n/language.js'

/**
 * Translation key returned when the stream reports an error without a usable
 * message. Server-provided messages are returned unchanged; the chat component
 * only translates a message that is exactly this key.
 */
export const GENERIC_CHAT_STREAM_ERROR = tk('chat:stream.genericError')

export function chatStreamErrorMessage(event: unknown): string | null {
  if (!event || typeof event !== 'object' || !('error' in event) || !event.error) {
    return null
  }

  const message = 'message' in event ? event.message : undefined
  return typeof message === 'string' && message.trim() ? message : GENERIC_CHAT_STREAM_ERROR
}
