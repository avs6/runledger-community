import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getVectorCollection, getVectorCollectionStats, getVectorQueries } from '@/lib/api'
import type { VectorCollectionStats, VectorQueryResponse } from '@/types/api'

function bytes(n: number) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function money(v: number | null | undefined) {
  if (!v) return '$0.00'
  if (v >= 1) return `$${v.toFixed(2)}`
  if (v >= 0.001) return `$${v.toFixed(4)}`
  return `$${v.toFixed(6)}`
}

function timeAgo(iso: string | null) {
  if (!iso) return '-'
  const ms = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(ms / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm ring-1 ring-white/70 dark:border-slate-700 dark:bg-slate-900/80">
      <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-950 dark:text-slate-50">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  )
}

function QueryRow({ q }: { q: VectorQueryResponse }) {
  const preview = q.query_text.length > 80 ? q.query_text.slice(0, 80) + '…' : q.query_text
  return (
    <tr className="border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50">
      <td className="px-4 py-3 text-sm text-slate-800 dark:text-slate-200 max-w-xs truncate">{preview}</td>
      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">{q.result_count}</td>
      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">{q.best_score ? Number(q.best_score).toFixed(4) : '-'}</td>
      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">{q.latency_ms != null ? `${q.latency_ms}ms` : '-'}</td>
      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">{money(Number(q.embed_cost) + Number(q.query_cost))}</td>
      <td className="px-4 py-3 text-xs text-slate-500">{timeAgo(q.created_at)}</td>
    </tr>
  )
}

export default async function VectorStoreDetailPage({ params }: { params: Promise<{ collection_id: string }> }) {
  const { collection_id } = await params
  const session = await getServerSession(authOptions)
  const apiKey = (session as Record<string, string> | null)?.apiKey
  if (!apiKey) return <p className="p-8 text-slate-500">Sign in to view collection.</p>

  let coll, stats: VectorCollectionStats | null = null, queries
  try {
    ;[coll, stats, queries] = await Promise.all([
      getVectorCollection(apiKey, collection_id),
      getVectorCollectionStats(apiKey, collection_id),
      getVectorQueries(apiKey, collection_id, { limit: 50 }),
    ])
  } catch {
    return (
      <div className="p-8">
        <p className="text-slate-500">Collection not found or API unavailable.</p>
        <Link href="/vector-stores" className="mt-2 inline-block text-sm text-blue-600 hover:underline">Back to Vector Stores</Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6 md:p-10">
      <div className="flex items-center gap-3">
        <Link href="/vector-stores" className="text-sm text-blue-600 hover:underline dark:text-blue-400">
          ← Vector Stores
        </Link>
        <span className="text-slate-400">/</span>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">{coll.name}</h1>
      </div>

      {coll.description && <p className="text-sm text-slate-600 dark:text-slate-400">{coll.description}</p>}

      <div className="flex flex-wrap gap-2">
        <span className="rounded-full bg-blue-100 px-2.5 py-1 text-[11px] font-semibold text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
          {coll.distance_metric}
        </span>
        {coll.embedding_model && (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {coll.embedding_model}
          </span>
        )}
        {coll.dimensions && (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {coll.dimensions} dimensions
          </span>
        )}
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-mono font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {coll.qdrant_collection}
        </span>
      </div>

      {stats && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <StatCard label="Documents" value={stats.document_count.toLocaleString()} />
          <StatCard label="Size" value={bytes(stats.size_bytes)} />
          <StatCard label="Total Queries" value={stats.total_queries.toLocaleString()} />
          <StatCard label="Total Cost" value={money(stats.total_cost)} sub={`Query: ${money(stats.total_query_cost)} / Embed: ${money(stats.total_embed_cost)}`} />
          <StatCard label="Avg Latency" value={stats.avg_query_latency_ms != null ? `${stats.avg_query_latency_ms.toFixed(0)}ms` : '-'} sub={stats.avg_results_per_query != null ? `${stats.avg_results_per_query.toFixed(1)} results/query` : ''} />
        </div>
      )}

      <section>
        <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">
          Recent Queries ({queries.total})
        </h2>
        {queries.queries.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-10 text-center dark:border-slate-700 dark:bg-slate-900/40">
            <p className="text-sm text-slate-500">No queries recorded yet.</p>
            <p className="mt-2 text-xs text-slate-400">
              Use <code className="rounded bg-slate-100 px-1 py-0.5 dark:bg-slate-800">POST /vector-stores/{collection_id}/search-test</code> to test searches.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Query</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Results</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Best Score</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Latency</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Cost</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">When</th>
                </tr>
              </thead>
              <tbody>
                {queries.queries.map((q) => (
                  <QueryRow key={q.id} q={q} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
