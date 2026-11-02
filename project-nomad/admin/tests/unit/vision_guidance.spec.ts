import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { visionAttachmentGuidance } from '../../inertia/lib/vision_guidance.js'

// visionAttachmentGuidance returns a translation key; the checks run against the English text.
const englishChat = JSON.parse(
  readFileSync(join(import.meta.dirname, '../../inertia/locales/en/chat.json'), 'utf-8')
)
function english(key: string): string {
  const [namespace, path] = key.split(':')
  assert.equal(namespace, 'chat')
  const text = path.split('.').reduce((node: any, part) => node?.[part], englishChat)
  assert.equal(typeof text, 'string', `Schlüssel ${key} fehlt in en/chat.json`)
  return text
}

test('vision guidance makes temporary image handling explicit', () => {
  const guidance = english(visionAttachmentGuidance('supported'))

  assert.match(guidance, /only with this request/i)
  assert.match(guidance, /not saved/i)
  assert.match(guidance, /reload/i)
})

test('unknown vision guidance explains the user choice without backend jargon', () => {
  const guidance = english(visionAttachmentGuidance('unknown'))

  assert.match(guidance, /cannot confirm/i)
  assert.match(guidance, /try/i)
  assert.match(guidance, /request will fail/i)
  assert.doesNotMatch(guidance, /backend|metadata|projector/i)
})

test('unsupported vision guidance points users to a compatible model', () => {
  assert.match(english(visionAttachmentGuidance('unsupported')), /supports images/i)
})
