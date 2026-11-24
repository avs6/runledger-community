'use client'

/**
 * Real search-test and Qdrant sync (review B-19). Errors from Qdrant or the
 * embedding service are shown as-is; nothing is recorded when they fail.
 */

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { Loader2, RefreshCw, Search } from 'lucide-react'
import { toast } from 'sonner'
import { syncVectorCollection, testVectorSearch } from '@/lib/api'
import type { VectorSearchTestResponse } from '@/types/api'
import { SectionError } from '@/components/ui/async-card'

export function SearchTestPanel({ collectionId }: { collectionId: string }) {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''
  const router = useRouter()
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [result, setResult] = useState<VectorSearchTestResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<'search' | 'sync' | null>(null)

  const search = async () => {
    if (!query.trim()) return
    setBusy('search')
    setError(null)
    try {
      setResult(await testVectorSearch(apiKey, collectionId, { query: query.trim(), top_k: topK }))
      router.refresh()
    } catch (e) {
      setResult(null)
      setError(e instanceof Error ? e.message : 'Search failed')
    } finally {
      setBusy(null)
    }
  }

  const sync = async () => {
    setBusy('sync')
    try {
      const c = await syncVectorCollection(apiKey, collectionId)
      toast.success(`Synced from Qdrant: ${c.document_count} documents`)
      router.refresh()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Sync failed')
    } finally {
      setBusy(null)
    }
  }

  return (
    <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/80">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-widest text-slate-500">Search test</h2>
        <button
          type="button"
          onClick={() => void sync()}
          disabled={busy !== null || !apiKey}
          aria-label="Refresh document count and dimensions from Qdrant"
          className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-2.5 py-1 text-xs hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:hover:bg-slate-800"
        >
          <RefreshCw className={`h-3 w-3 ${busy === 'sync' ? 'animate-spin' : ''}`} /> Sync from Qdrant
        </button>
      </div>
      <p className="text-xs text-slate-500">
        Embeds the query with the self-hosted embedding service and searches this collection in Qdrant. Self-hosted
        embeddings have no per-query provider cost.
      </p>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          void search()
        }}
      >
        <input
          aria-label="Search query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What is our refund policy?"
          className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
        />
        <input
          aria-label="Top K"
          type="number"
          min={1}
          max={100}
          value={topK}
          onChange={(e) => setTopK(Number(e.target.value) || 5)}
          className="w-20 rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
        />
        <button
          type="submit"
          disabled={busy !== null || !query.trim() || !apiKey}
          className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {busy === 'search' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
          Search
        </button>
      </form>
      {error ? <SectionError message={error} onRetry={() => void search()} /> : null}
      {result ? (
        <div className="space-y-2">
          <p className="text-xs text-slate-500">
            {result.result_count} result(s) in {result.latency_ms ?? '—'} ms
          </p>
          {result.results.map((r, i) => (
            <div key={i} className="rounded-lg bg-slate-50 p-2 text-xs dark:bg-slate-800">
              <p className="font-mono text-slate-500">score {Number(r.score).toFixed(4)}</p>
              <pre className="whitespace-pre-wrap">{JSON.stringify(r.payload, null, 2)}</pre>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  )
}
