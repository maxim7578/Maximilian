import type { ModelVisionCapability } from '../../types/ollama.js'
import { tk } from '../i18n/language.js'

/** Returns the translation key of the image-attachment hint; render it with t(key). */
export function visionAttachmentGuidance(capability: ModelVisionCapability) {
  if (capability === 'unsupported') {
    return tk('chat:vision.unsupported')
  }

  if (capability === 'unknown') {
    return tk('chat:vision.unknown')
  }

  return tk('chat:vision.temporary')
}
