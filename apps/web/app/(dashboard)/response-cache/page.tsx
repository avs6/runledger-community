import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { getResponseCacheConfigs, getResponseCacheStats } from '@/lib/api'

function pct(value: number | null) {
  if (value == null) return '—'
  return `${(value * 100).toFixed(1)}%`
}

export default async function ResponseCachePage() {
  const session = await getServerSession(authOptions)
  const apiKey = (session as Record<string, string> | null)?.apiKey
  if (!apiKey) return <p className="p-8 text-slate-500">Sign in to view response cache settings.</p>

  try {
    const [configs, stats] = await Promise.all([
      getResponseCacheConfigs(apiKey),
      getResponseCacheStats(apiKey),
    ])

    return (
      <div className="mx-auto max-w-7xl space-y-8 p-6 md:p-10">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Response Cache Management
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Semantic cache tuning, hit-rate visibility, and configuration health in one place.
            </p>
          </div>
          <span className="text-sm text-slate-500">{configs.total} cache profiles</span>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Enabled</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{stats.enabled_config_count}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Hit Rate</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{pct(stats.hit_rate)}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Total Hits</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{stats.total_hits}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Estimated Savings</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
              ${stats.total_savings_usd.toFixed(2)}
            </p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="space-y-4">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Semantic Cache Tuning</h2>
            {configs.items.map((config) => (
              <div key={config.id} className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-slate-900 dark:text-slate-50">{config.name}</p>
                    <p className="text-sm text-slate-500">{config.embedding_model || 'default embedding model'}</p>
                  </div>
                  <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-semibold uppercase text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    {config.is_enabled ? 'enabled' : 'disabled'}
                  </span>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600 dark:bg-slate-800/70 dark:text-slate-300">
                    TTL: {config.ttl_seconds}s
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600 dark:bg-slate-800/70 dark:text-slate-300">
                    Similarity: {(config.similarity_threshold * 100).toFixed(1)}%
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600 dark:bg-slate-800/70 dark:text-slate-300">
                    Max entries: {config.max_entries.toLocaleString()}
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600 dark:bg-slate-800/70 dark:text-slate-300">
                    Policy: {config.eviction_policy}
                  </div>
                </div>
              </div>
            ))}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Top Cached Models</h2>
            <div className="mt-4 space-y-3">
              {stats.top_models.length === 0 ? (
                <p className="text-sm text-slate-500">No live cache entries yet.</p>
              ) : (
                stats.top_models.map((item) => (
                  <div key={item.model} className="flex items-center justify-between rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                    <span className="font-medium text-slate-900 dark:text-slate-50">{item.model}</span>
                    <span className="text-sm text-slate-500">{item.hit_count} hits</span>
                  </div>
                ))
              )}
            </div>
            <div className="mt-6 rounded-xl bg-slate-50 p-4 text-sm text-slate-600 dark:bg-slate-800/70 dark:text-slate-300">
              Live entry capacity currently tracks enabled profiles and sums to {stats.live_entry_count.toLocaleString()} available slots.
            </div>
          </section>
        </div>
      </div>
    )
  } catch {
    return <p className="p-8 text-slate-500">Failed to load response cache management.</p>
  }
}
