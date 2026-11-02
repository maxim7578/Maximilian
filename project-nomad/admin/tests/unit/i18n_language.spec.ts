import * as assert from 'node:assert/strict'
import { test } from 'node:test'

import { isSupportedLanguage, localeFor, pickLanguage, tk } from '../../inertia/i18n/language.js'

test('eine gespeicherte Sprache hat Vorrang vor der Browsersprache', () => {
  assert.equal(pickLanguage('en', ['de-DE', 'de']), 'en')
  assert.equal(pickLanguage('de', ['en-US']), 'de')
})

test('ohne gespeicherte Sprache entscheidet die erste passende Browsersprache', () => {
  assert.equal(pickLanguage(null, ['de-AT', 'en-US']), 'de')
  assert.equal(pickLanguage(null, ['fr-FR', 'en-GB', 'de-DE']), 'en')
  assert.equal(pickLanguage(null, ['FR', 'DE']), 'de')
})

test('eine ungültige gespeicherte Sprache wird ignoriert', () => {
  assert.equal(pickLanguage('fr', ['de-CH']), 'de')
  assert.equal(pickLanguage('', ['en-US']), 'en')
})

test('ohne passende Sprache wird Englisch verwendet', () => {
  assert.equal(pickLanguage(null, []), 'en')
  assert.equal(pickLanguage(undefined, ['fr-FR', 'es']), 'en')
})

test('nur Deutsch und Englisch gelten als unterstützt', () => {
  assert.equal(isSupportedLanguage('de'), true)
  assert.equal(isSupportedLanguage('en'), true)
  assert.equal(isSupportedLanguage('fr'), false)
  assert.equal(isSupportedLanguage('de-DE'), false)
  assert.equal(isSupportedLanguage(undefined), false)
})

test('jede Sprache hat ein Gebietsschema für Zahlen und Datumsangaben', () => {
  assert.equal(localeFor('de'), 'de-DE')
  assert.equal(localeFor('en'), 'en-US')
})

test('tk gibt den Übersetzungsschlüssel unverändert zurück', () => {
  assert.equal(tk('common:status.loading'), 'common:status.loading')
})
