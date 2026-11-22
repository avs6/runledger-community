'use client'

import { Suspense, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Columns3, Download, Search } from 'lucide-react'
import type { Page } from '@/lib/api/client'
import { EmptyState } from './empty-state'
import { SectionError } from './async-card'

export interface DataTableColumn<T> {
  /** Stable id; also the sort key sent to the server when `sortable`. */
  key: string
  header: string
  render?: (row: T) => ReactNode
  /** Plain value for sorting (client mode) and CSV export. Defaults to row[key]. */
  value?: (row: T) => string | number | null | undefined
  sortable?: boolean
  /** Hidden until the user turns it on in the column chooser. */
  defaultHidden?: boolean
  className?: string
}

export interface DataTableQuery {
  limit: number
  offset: number
  sort?: string
  dir?: 'asc' | 'desc'
  q?: string
}

interface BaseProps<T> {
  columns: DataTableColumn<T>[]
  rowKey: (row: T) => string
  /** Prefix for URL search params (`<prefix>page`, `<prefix>sort`, …) so two tables can share a page. */
  urlPrefix?: string
  pageSize?: number
  searchPlaceholder?: string
  /** Hide the search box (e.g. when the endpoint has no `q` filter). */
  searchable?: boolean
  csvFileName?: string
  emptyTitle?: string
  emptyDescription?: string
  onRowClick?: (row: T) => void
  /** Accessible name for the table. */
  label: string
}

interface ServerProps<T> extends BaseProps<T> {
  /** Server mode: fetch one page; total comes from X-Total-Count (see apiFetchPage). */
  fetchPage: (query: DataTableQuery) => Promise<Page<T>>
  rows?: never
}

interface ClientProps<T> extends BaseProps<T> {
  /** Client mode: all rows in memory; paging, sort and search happen locally. */
  rows: T[]
  fetchPage?: never
}

export type DataTableProps<T> = ServerProps<T> | ClientProps<T>

function cellValue<T>(col: DataTableColumn<T>, row: T): string | number | null | undefined {
  if (col.value) return col.value(row)
  const raw = (row as Record<string, unknown>)[col.key]
  return typeof raw === 'string' || typeof raw === 'number' ? raw : raw == null ? raw as null : String(raw)
}

function toCsv<T>(columns: DataTableColumn<T>[], rows: T[]): string {
  const esc = (v: unknown) => {
    const s = v == null ? '' : String(v)
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  return [columns.map((c) => esc(c.header)).join(','), ...rows.map((r) => columns.map((c) => esc(cellValue(c, r))).join(','))].join('\n')
}

/**
 * Shared table (inner; use DataTable): server or client paging, sortable columns, a column chooser (remembered
 * per table), CSV export of the visible rows, search, and page/sort/search kept in the URL.
 */
function DataTableInner<T>(props: DataTableProps<T>) {
  const { columns, rowKey, urlPrefix = '', pageSize = 25, searchable = true, label } = props
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()
  const p = (k: string) => `${urlPrefix}${k}`
  const page = Math.max(1, Number(params.get(p('page')) ?? 1) || 1)
  const sort = params.get(p('sort')) ?? undefined
  const dir = (params.get(p('dir')) as 'asc' | 'desc' | null) ?? 'asc'
  const q = params.get(p('q')) ?? ''

  const storageKey = `datatable:${pathname}:${urlPrefix}${label}`
  const [hidden, setHidden] = useState<Set<string>>(() => new Set(columns.filter((c) => c.defaultHidden).map((c) => c.key)))
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(storageKey)
      if (saved) setHidden(new Set(JSON.parse(saved) as string[]))
    } catch {
      /* storage unavailable: keep defaults */
    }
  }, [storageKey])
  const toggleColumn = (key: string) => {
    setHidden((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      try { window.localStorage.setItem(storageKey, JSON.stringify(Array.from(next))) } catch { /* ignore */ }
      return next
    })
  }
  const visible = columns.filter((c) => !hidden.has(c.key))

  const setParams = useCallback((patch: Record<string, string | null>) => {
    const next = new URLSearchParams(params.toString())
    for (const [k, v] of Object.entries(patch)) {
      if (v == null || v === '') next.delete(p(k))
      else next.set(p(k), v)
    }
    router.replace(`${pathname}${next.toString() ? `?${next}` : ''}`, { scroll: false })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params, pathname, router, urlPrefix])

  // Search input is debounced into the URL.
  const [search, setSearch] = useState(q)
  useEffect(() => setSearch(q), [q])
  useEffect(() => {
    if (search === q) return
    const t = setTimeout(() => setParams({ q: search, page: null }), 300)
    return () => clearTimeout(t)
  }, [search, q, setParams])

  const [serverPage, setServerPage] = useState<Page<T> | null>(null)
  const [loading, setLoading] = useState(Boolean(props.fetchPage))
  const [error, setError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const fetchRef = useRef(props.fetchPage)
  fetchRef.current = props.fetchPage

  useEffect(() => {
    const fetchPage = fetchRef.current
    if (!fetchPage) return
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchPage({ limit: pageSize, offset: (page - 1) * pageSize, sort, dir: sort ? dir : undefined, q: q || undefined })
      .then((res) => { if (!cancelled) setServerPage(res) })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [page, pageSize, sort, dir, q, reload])

  const clientView = useMemo(() => {
    if (!props.rows) return null
    let rows = props.rows
    if (q) {
      const needle = q.toLowerCase()
      rows = rows.filter((r) => columns.some((c) => String(cellValue(c, r) ?? '').toLowerCase().includes(needle)))
    }
    if (sort) {
      const col = columns.find((c) => c.key === sort)
      if (col) {
        rows = [...rows].sort((a, b) => {
          const av = cellValue(col, a); const bv = cellValue(col, b)
          const cmp = typeof av === 'number' && typeof bv === 'number' ? av - bv : String(av ?? '').localeCompare(String(bv ?? ''))
          return dir === 'desc' ? -cmp : cmp
        })
      }
    }
    return { items: rows.slice((page - 1) * pageSize, page * pageSize), total: rows.length }
  }, [props.rows, q, sort, dir, page, pageSize, columns])

  const view = clientView ?? serverPage ?? { items: [], total: 0 }
  const totalPages = Math.max(1, Math.ceil(view.total / pageSize))
  const [chooserOpen, setChooserOpen] = useState(false)

  const exportCsv = () => {
    const blob = new Blob([toCsv(visible, view.items)], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = props.csvFileName ?? `${label.toLowerCase().replace(/\s+/g, '-')}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const onSort = (key: string) => {
    if (sort !== key) setParams({ sort: key, dir: 'asc', page: null })
    else if (dir === 'asc') setParams({ dir: 'desc', page: null })
    else setParams({ sort: null, dir: null, page: null })
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {searchable && (
          <label className="relative min-w-[200px] flex-1">
            <span className="sr-only">Search {label}</span>
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={props.searchPlaceholder ?? 'Search…'}
              className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-8 pr-2.5 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
          </label>
        )}
        <div className="relative">
          <button type="button" aria-haspopup="true" aria-expanded={chooserOpen} onClick={() => setChooserOpen((o) => !o)}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
            <Columns3 className="h-3.5 w-3.5" /> Columns
          </button>
          {chooserOpen && (
            <div role="menu" className="absolute right-0 z-20 mt-1 w-48 rounded-lg border border-slate-200 bg-white p-2 shadow-lg dark:border-slate-700 dark:bg-slate-900">
              {columns.map((c) => (
                <label key={c.key} className="flex items-center gap-2 rounded px-1.5 py-1 text-xs text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800">
                  <input type="checkbox" checked={!hidden.has(c.key)} onChange={() => toggleColumn(c.key)} />
                  {c.header}
                </label>
              ))}
            </div>
          )}
        </div>
        <button type="button" onClick={exportCsv} disabled={!view.items.length}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
          <Download className="h-3.5 w-3.5" /> CSV
        </button>
      </div>

      {error ? (
        <SectionError message={error} onRetry={() => setReload((n) => n + 1)} />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
          <table aria-label={label} aria-busy={loading} className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
              <tr>
                {visible.map((c) => (
                  <th key={c.key} scope="col" aria-sort={sort === c.key ? (dir === 'asc' ? 'ascending' : 'descending') : undefined} className={`px-3 py-2 font-medium ${c.className ?? ''}`}>
                    {c.sortable ? (
                      <button type="button" onClick={() => onSort(c.key)} className="inline-flex items-center gap-1 hover:text-slate-900 dark:hover:text-white">
                        {c.header}
                        {sort === c.key && (dir === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                      </button>
                    ) : c.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading && !view.items.length ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <tr key={i}>{visible.map((c) => <td key={c.key} className="px-3 py-2"><div className="h-3 animate-pulse rounded bg-slate-100 dark:bg-slate-800" /></td>)}</tr>
                ))
              ) : view.items.map((row) => (
                <tr key={rowKey(row)} onClick={props.onRowClick ? () => props.onRowClick?.(row) : undefined}
                  className={props.onRowClick ? 'cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40' : undefined}>
                  {visible.map((c) => (
                    <td key={c.key} className={`px-3 py-2 text-slate-700 dark:text-slate-200 ${c.className ?? ''}`}>
                      {c.render ? c.render(row) : (cellValue(c, row) ?? '—')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {!loading && !view.items.length && (
            <EmptyState title={props.emptyTitle ?? (q ? `Nothing matches “${q}”` : 'Nothing here yet')} description={props.emptyDescription} compact />
          )}
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>{view.total.toLocaleString()} {view.total === 1 ? 'row' : 'rows'}</span>
        <div className="flex items-center gap-2">
          <button type="button" aria-label="Previous page" disabled={page <= 1} onClick={() => setParams({ page: String(page - 1) })}
            className="rounded border border-slate-200 p-1 disabled:opacity-40 dark:border-slate-700"><ChevronLeft className="h-3.5 w-3.5" /></button>
          <span>Page {page} of {totalPages}</span>
          <button type="button" aria-label="Next page" disabled={page >= totalPages} onClick={() => setParams({ page: String(page + 1) })}
            className="rounded border border-slate-200 p-1 disabled:opacity-40 dark:border-slate-700"><ChevronRight className="h-3.5 w-3.5" /></button>
        </div>
      </div>
    </div>
  )
}

/** Wrapped in Suspense because it reads useSearchParams (required for static pages in Next 14). */
export function DataTable<T>(props: DataTableProps<T>) {
  return (
    <Suspense fallback={<div className="h-24 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />}>
      <DataTableInner {...props} />
    </Suspense>
  )
}
