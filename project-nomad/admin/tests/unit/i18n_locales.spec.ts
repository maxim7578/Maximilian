import * as assert from 'node:assert/strict'
import { test } from 'node:test'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

/**
 * Prüft die Sprachdateien der Oberfläche (inertia/locales/<sprache>/<namensraum>.json):
 * gleiche Namensräume und Schlüssel in allen Sprachen, keine leeren Texte, gleiche
 * Platzhalter, und jeder im Code verwendete Schlüssel existiert in jeder Sprache.
 */

const INERTIA_DIR = join(import.meta.dirname, '../../inertia')
const LOCALES_DIR = join(INERTIA_DIR, 'locales')
const LANGUAGES = ['en', 'de'] as const

type Flat = Record<string, string>

function flatten(value: unknown, prefix = '', out: Flat = {}): Flat {
  if (typeof value === 'string') {
    out[prefix] = value
    return out
  }
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    for (const [key, child] of Object.entries(value)) {
      flatten(child, prefix ? `${prefix}.${key}` : key, out)
    }
    return out
  }
  throw new Error(`Ungültiger Wert bei "${prefix}": nur Texte und Objekte sind erlaubt`)
}

function loadLanguage(language: string): Map<string, Flat> {
  const dir = join(LOCALES_DIR, language)
  const namespaces = new Map<string, Flat>()
  for (const file of readdirSync(dir).filter((name) => name.endsWith('.json')).sort()) {
    const namespace = file.replace(/\.json$/, '')
    namespaces.set(namespace, flatten(JSON.parse(readFileSync(join(dir, file), 'utf-8'))))
  }
  return namespaces
}

function placeholders(text: string): string[] {
  return [...text.matchAll(/\{\{\s*([\w.]+)[^}]*\}\}/g)].map((match) => match[1]).sort()
}

function sourceFiles(dir: string): string[] {
  const files: string[] = []
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry)
    if (entry === 'locales' || entry === 'node_modules') continue
    if (statSync(path).isDirectory()) files.push(...sourceFiles(path))
    else if (/\.(ts|tsx)$/.test(entry)) files.push(path)
  }
  return files
}

const PLURAL_SUFFIXES = ['_zero', '_one', '_two', '_few', '_many', '_other']

function hasKey(flat: Flat, key: string): boolean {
  return key in flat || PLURAL_SUFFIXES.some((suffix) => `${key}${suffix}` in flat)
}

const locales = new Map(LANGUAGES.map((language) => [language, loadLanguage(language)]))
const english = locales.get('en')!

test('alle Sprachen haben dieselben Namensräume', () => {
  const expected = [...english.keys()]
  assert.ok(expected.length > 0, 'keine Sprachdateien in inertia/locales/en gefunden')
  for (const language of LANGUAGES) {
    assert.deepEqual([...locales.get(language)!.keys()], expected, `Namensräume in "${language}"`)
  }
})

test('alle Sprachen haben dieselben Schlüssel', () => {
  for (const [namespace, englishKeys] of english) {
    for (const language of LANGUAGES) {
      const keys = locales.get(language)!.get(namespace) ?? {}
      const missing = Object.keys(englishKeys).filter((key) => !(key in keys))
      const extra = Object.keys(keys).filter((key) => !(key in englishKeys))
      assert.deepEqual(missing, [], `in ${language}/${namespace}.json fehlen Schlüssel`)
      assert.deepEqual(extra, [], `in ${language}/${namespace}.json gibt es zusätzliche Schlüssel`)
    }
  }
})

test('kein Text ist leer', () => {
  for (const language of LANGUAGES) {
    for (const [namespace, flat] of locales.get(language)!) {
      const empty = Object.entries(flat).filter(([, text]) => text.trim() === '')
      assert.deepEqual(empty, [], `leere Texte in ${language}/${namespace}.json`)
    }
  }
})

test('Platzhalter stimmen in allen Sprachen überein', () => {
  for (const [namespace, englishKeys] of english) {
    for (const [key, englishText] of Object.entries(englishKeys)) {
      for (const language of LANGUAGES) {
        const text = locales.get(language)!.get(namespace)?.[key]
        if (text === undefined) continue
        assert.deepEqual(
          placeholders(text),
          placeholders(englishText),
          `Platzhalter in ${language}/${namespace}.json bei "${key}"`
        )
      }
    }
  }
})

test('jeder im Code verwendete Schlüssel existiert in jeder Sprache', () => {
  const usage = /\b(?:t|tk|i18n\.t)\(\s*['"`]([^'"`$]+)['"`]|i18nKey=\{?\s*['"`]([^'"`$]+)['"`]/g
  const problems: string[] = []
  for (const file of sourceFiles(INERTIA_DIR)) {
    const source = readFileSync(file, 'utf-8')
    for (const match of source.matchAll(usage)) {
      const fullKey = match[1] ?? match[2]
      const where = `${relative(INERTIA_DIR, file)}: "${fullKey}"`
      const separator = fullKey.indexOf(':')
      if (separator < 1) {
        problems.push(`${where} (Namensraum fehlt, Form "namensraum:schlüssel")`)
        continue
      }
      const namespace = fullKey.slice(0, separator)
      const key = fullKey.slice(separator + 1)
      for (const language of LANGUAGES) {
        const flat = locales.get(language)!.get(namespace)
        if (!flat || !hasKey(flat, key)) problems.push(`${where} fehlt in ${language}`)
      }
    }
  }
  assert.deepEqual(problems, [])
})
