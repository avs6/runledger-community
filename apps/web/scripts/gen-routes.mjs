#!/usr/bin/env node
// Regenerate lib/routes.ts from the page.tsx files under app/ (review Wave 0.4).
// Route groups "(x)" are dropped; "_private" and "@slot" folders are skipped.
import { readdirSync, statSync, writeFileSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(fileURLToPath(new URL('.', import.meta.url)), '..')
const appDir = join(root, 'app')

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (name === 'page.tsx') out.push(dir)
  }
  return out
}

const routes = [...new Set(walk(appDir).map((dir) => {
  const parts = relative(appDir, dir).split(sep).filter((s) => s && !(s.startsWith('(') && s.endsWith(')')))
  if (parts.some((s) => s.startsWith('_') || s.startsWith('@'))) return null
  return '/' + parts.join('/')
}).filter(Boolean))].sort()

const stat = routes.filter((r) => !r.includes('['))
const dyn = routes.filter((r) => r.includes('['))
const key = (r) => {
  const words = r.replace(/[[\]]/g, '').split(/[^a-zA-Z0-9]+/).filter(Boolean)
  const k = words.map((w) => w[0].toUpperCase() + w.slice(1)).join('')
  return k ? k[0].toLowerCase() + k.slice(1) : 'home'
}
const builder = (r) => {
  const params = [...r.matchAll(/\[([^\]]+)\]/g)].map((m) => m[1].replace(/[^a-zA-Z0-9_]/g, ''))
  let path = r
  for (const m of r.matchAll(/\[([^\]]+)\]/g)) path = path.replace(m[0], '${encodeURIComponent(' + m[1].replace(/[^a-zA-Z0-9_]/g, '') + ')}')
  return `  ${key(r)}: (${params.map((p) => `${p}: string`).join(', ')}) => \`${path}\`,`
}

const out = [
  '/**',
  '* Every page route in the app, generated from the page.tsx files under app/ (review Wave 0.4).',
  '* Link with these instead of string literals; scripts/check-routes.mjs fails CI on hrefs that',
  '* match none of them. Regenerate with `node scripts/gen-routes.mjs` after adding a page.',
  '*/',
  '',
  'export const STATIC_ROUTES = [',
  ...stat.map((r) => `  '${r}',`),
  '] as const',
  '',
  'export type StaticRoute = (typeof STATIC_ROUTES)[number]',
  '',
  '/** Dynamic route patterns (segments in brackets). */',
  'export const DYNAMIC_ROUTES = [',
  ...dyn.map((r) => `  '${r}',`),
  '] as const',
  '',
  '/** Typed builders for dynamic routes. */',
  'export const routes = {',
  ...dyn.map(builder),
  '} as const',
  '',
  'const DYNAMIC_PATTERNS = DYNAMIC_ROUTES.map(',
  "  (r) => new RegExp('^' + r.replace(/\\[[^\\]]+\\]/g, '[^/]+') + '$'),",
  ')',
  '',
  '/** True when `href` (path only, query and hash ignored) matches a page in the app. */',
  'export function isKnownRoute(href: string): boolean {',
  "  const path = href.split(/[?#]/)[0].replace(/\\/$/, '') || '/'",
  '  return (STATIC_ROUTES as readonly string[]).includes(path) || DYNAMIC_PATTERNS.some((re) => re.test(path))',
  '}',
  '',
]
writeFileSync(join(root, 'lib', 'routes.ts'), out.join('\n'))
console.log(`lib/routes.ts: ${stat.length} static, ${dyn.length} dynamic routes`)
