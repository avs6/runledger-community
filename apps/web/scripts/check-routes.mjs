#!/usr/bin/env node
// Dead-link check (review Wave 0.5): every internal href, router.push/replace and redirect
// target in app/, components/ and lib/ must match a page in lib/routes.ts.
// Template-literal expressions count as one path segment. Exits 1 on any unknown target.
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(fileURLToPath(new URL('.', import.meta.url)), '..')
const routesSrc = readFileSync(join(root, 'lib', 'routes.ts'), 'utf8')
const list = (name) => {
  const start = routesSrc.indexOf(`export const ${name} = [`)
  const m = start < 0 ? null : routesSrc.slice(start).match(/^[^[]*\[([\s\S]*?)\] as const/)
  return m ? [...m[1].matchAll(/'([^']+)'/g)].map((x) => x[1]) : []
}
const STATIC = new Set(list('STATIC_ROUTES'))
const DYNAMIC = list('DYNAMIC_ROUTES').map((r) => new RegExp('^' + r.replace(/\[[^\]]+\]/g, '[^/]+') + '$'))
const known = (p) => STATIC.has(p) || DYNAMIC.some((re) => re.test(p))

// Paths served by Next itself or the API proxy, not pages.
const IGNORE = [/^\/api(\/|$)/, /^\/_next\//, /^\/favicon/, /^\/[^/]+\.(png|svg|ico|txt|json|xml)$/]

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    if (name === 'node_modules' || name.startsWith('.')) continue
    const p = join(dir, name)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (/\.(tsx?|jsx?)$/.test(name)) out.push(p)
  }
  return out
}

const patterns = [
  /href=\{?["'`](\/[^"'`\s]*)["'`]/g,
  /href:\s*["'`](\/[^"'`\s]*)["'`]/g,
  /\b(?:router\.(?:push|replace)|redirect)\(\s*["'`](\/[^"'`\s]*)["'`]/g,
]
const problems = []
for (const dir of ['app', 'components', 'lib']) {
  for (const file of walk(join(root, dir))) {
    const src = readFileSync(file, 'utf8')
    for (const re of patterns) {
      for (const m of src.matchAll(re)) {
        let target = m[1]
        // A template expression stands in for one dynamic segment; a trailing one may also be a query.
        target = target.replace(/\$\{[^}]*\}/g, 'x').split(/[?#]/)[0].replace(/\/$/, '') || '/'
        if (IGNORE.some((ig) => ig.test(target))) continue
        if (known(target)) continue
        const line = src.slice(0, m.index).split('\n').length
        problems.push(`${relative(root, file)}:${line}  ${m[1]}`)
      }
    }
  }
}
if (problems.length) {
  console.error(`Links to pages that don't exist (${problems.length}):`)
  for (const p of problems) console.error('  ' + p)
  process.exit(1)
}
console.log('check-routes: every internal link matches a page')
