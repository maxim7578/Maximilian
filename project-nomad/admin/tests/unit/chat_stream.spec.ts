import assert from 'node:assert/strict'
import test from 'node:test'
import { chatStreamErrorMessage } from '../../inertia/lib/chat_stream.js'

test('chat stream preserves an actionable server error message', () => {
  assert.equal(
    chatStreamErrorMessage({
      error: true,
      message:
        'NOMAD cannot confirm that this model accepts images. Choose a model marked “Supports images”.',
    }),
    'NOMAD cannot confirm that this model accepts images. Choose a model marked “Supports images”.'
  )
  // Without a server message the generic error is returned as a translation key.
  assert.equal(chatStreamErrorMessage({ error: true }), 'chat:stream.genericError')
  assert.equal(chatStreamErrorMessage({ done: true }), null)
})
