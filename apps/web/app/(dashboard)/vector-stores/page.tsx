import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getVectorCollections, getVectorStoresLifecyclePosture } from '@/lib/api'
import type { VectorCollectionResponse, VectorStoresLifecyclePosture } from '@/types/api'

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

function statusBadge(s: string) {
  const map: Record<string, string> = {
    active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    inactive: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    deleted: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  }
  return map[s] || 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
}

function CollectionCard({ c }: { c: VectorCollectionResponse }) {
  const totalCost = (c.total_query_cost || 0) + (c.total_embed_cost || 0)
  return (
    <Link
      href={`/vector-stores/${c.id}`}
      className="group rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm ring-1 ring-white/70 transition hover:shadow-md dark:border-slate-700 dark:bg-slate-900/80"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-slate-900 group-hover:text-blue-600 dark:text-slate-50 dark:group-hover:text-blue-400">
          {c.name}
        </h3>
        <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${statusBadge(c.status)}`}>
          {c.status}
        </span>
      </div>
      {c.description && <p className="mt-1 text-sm text-slate-500 line-clamp-2">{c.description}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
          {c.distance_metric}
        </span>
        {c.embedding_model && (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {c.embedding_model}
          </span>
        )}
        {c.dimensions && (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {c.dimensions}d
          </span>
        )}
      </div>
      <div className="mt-4 grid grid-cols-3 gap-3 text-center">
        <div>
          <p className="text-lg font-semibold text-slate-900 dark:text-slate-50">{c.document_count.toLocaleString()}</p>
          <p className="text-[10px] text-slate-500">Documents</p>
        </div>
        <div>
          <p className="text-lg font-semibold text-slate-900 dark:text-slate-50">{bytes(c.size_bytes)}</p>
          <p className="text-[10px] text-slate-500">Size</p>
        </div>
        <div>
          <p className="text-lg font-semibold text-slate-900 dark:text-slate-50">{c.total_queries.toLocaleString()}</p>
          <p className="text-[10px] text-slate-500">Queries</p>
        </div>
      </div>
      <p className="mt-3 text-right text-xs text-slate-500">Total cost: {money(totalCost)}</p>
    </Link>
  )
}

export default async function VectorStoresPage() {
  const session = await getServerSession(authOptions)
  const apiKey = (session as Record<string, string> | null)?.apiKey
  if (!apiKey) return <p className="p-8 text-slate-500">Sign in to view vector stores.</p>

  let collections: VectorCollectionResponse[] = []
  let total = 0
  try {
    const data = await getVectorCollections(apiKey)
    collections = data.collections
    total = data.total
  } catch {
    return <p className="p-8 text-slate-500">Failed to load vector stores.</p>
  }

  const lifecyclePosture: VectorStoresLifecyclePosture | null = await getVectorStoresLifecyclePosture(apiKey).catch(() => null)

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 md:p-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          Vector Stores
        </h1>
        <span className="text-sm text-slate-500">{total} collection{total !== 1 ? 's' : ''}</span>
      </div>

      {lifecyclePosture && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm dark:border-amber-900 dark:bg-amber-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">Workspace, Cost &amp; Build Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-5">
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Workspace</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{lifecyclePosture.workspace_context.workspace_name}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Provider Calls 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{lifecyclePosture.observe_context.provider_calls_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Cost 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">${Number(lifecyclePosture.cost_context.cost_30d).toFixed(2)}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Workflows</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{lifecyclePosture.build_context.workflows}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Eval Experiments</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{lifecyclePosture.build_context.eval_experiments}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-amber-200 dark:border-amber-800">
            <Link href="/workspaces" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Workspaces</Link>
            <Link href="/request-explorer" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Request Explorer</Link>
            <Link href="/chargeback" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Chargeback</Link>
            <Link href="/workflows" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Workflows</Link>
            <Link href="/evaluation?tab=scores" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Evaluation Studio</Link>
            <Link href="/optimization-opportunities" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Optimization</Link>
          </div>
        </div>
      )}

      {collections.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-10 text-center dark:border-slate-700 dark:bg-slate-900/40">
          <p className="text-sm text-slate-500">No vector store collections registered yet.</p>
          <pre className="mx-auto mt-4 max-w-lg rounded-lg bg-slate-100 p-4 text-left text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300">
{`POST /vector-stores
{
  "name": "knowledge-base",
  "qdrant_collection": "kb_v1",
  "embedding_model": "bge-small-en-v1.5",
  "dimensions": 384
}`}
          </pre>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {collections.map((c) => (
            <CollectionCard key={c.id} c={c} />
          ))}
        </div>
      )}
    </div>
  )
}
