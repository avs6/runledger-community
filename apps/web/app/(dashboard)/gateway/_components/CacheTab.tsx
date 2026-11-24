'use client'

import Link from 'next/link'
import { RefreshCw, Plus, Trash2, Pencil, ChevronUp } from 'lucide-react'
import { num } from '@/lib/utils'
import { inputCls } from './shared'
import { SectionError } from '@/components/ui/async-card'
import { useGateway } from './useGatewayState'

export function CacheTab() {
  const {
    sectionErrors,
    loadTabData,
    cacheConfigs,
    cacheStats,
    showCacheForm,
    setShowCacheForm,
    creatingCacheConfig,
    cacheEditState,
    setCacheEditState,
    savingCacheEdit,
    cacheConfigError,
    setCacheConfigError,
    expandedCacheId,
    cacheDetails,
    loadingCacheDetail,
    newCacheName,
    setNewCacheName,
    newCacheEnabled,
    setNewCacheEnabled,
    newCacheTtlSeconds,
    setNewCacheTtlSeconds,
    newCacheMaxEntries,
    setNewCacheMaxEntries,
    newCacheEvictionPolicy,
    setNewCacheEvictionPolicy,
    newCacheSimilarityThreshold,
    setNewCacheSimilarityThreshold,
    newCacheEmbeddingModel,
    setNewCacheEmbeddingModel,
    newCacheScopeModels,
    setNewCacheScopeModels,
    newCacheConfigStr,
    setNewCacheConfigStr,
    beginCacheEdit,
    handleCreateCacheConfig,
    handleLoadCacheDetails,
    handleSaveCacheEdit,
    handleDeleteCacheConfig,
  } = useGateway()
  return (
  <div className="space-y-3">
  {sectionErrors.cacheConfigs && <SectionError message={sectionErrors.cacheConfigs} onRetry={() => void loadTabData('cache', true)} />}
  {sectionErrors.cacheStats && <SectionError message={sectionErrors.cacheStats} onRetry={() => void loadTabData('cache', true)} />}


  <section className="space-y-4">
    <div className="flex items-center justify-between gap-4">
      <div>
        <h2 className="text-base font-semibold dark:text-white">Response Cache Profiles</h2>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
          Cache lifecycle is collapsed into Gateway. Manage cache profiles here, then apply route-level cache toggles further down this page.
        </p>
        <div className="mt-1 flex flex-wrap gap-3">
          <Link href="/budgets" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Budgets</Link>
          <Link href="/billing" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Billing Periods</Link>
          <Link href="/chargeback" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Chargeback</Link>
          <Link href="/cost-savings" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Cost & Savings</Link>
          <Link href="/workspace" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Workspaces</Link>
          <Link href="/api-keys" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">API Keys</Link>
          <Link href="/settings" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Platform Settings</Link>
        </div>
      </div>
      <button
        onClick={() => {
          setShowCacheForm((value) => !value)
          setCacheConfigError('')
        }}
        className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
      >
        {showCacheForm ? <ChevronUp className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
        {showCacheForm ? 'Cancel' : 'Add Cache Profile'}
      </button>
    </div>

    {cacheStats && (
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {[
          { label: 'Profiles', value: cacheStats.config_count.toLocaleString() },
          { label: 'Enabled', value: cacheStats.enabled_config_count.toLocaleString() },
          { label: 'Hit Rate', value: cacheStats.hit_rate != null ? `${(num(cacheStats.hit_rate) * 100).toFixed(1)}%` : '—' },
          { label: 'Savings', value: `$${Number(cacheStats.total_savings_usd || 0).toFixed(2)}` },
          { label: 'Live Capacity', value: cacheStats.live_entry_count.toLocaleString() },
        ].map((item) => (
          <div key={item.label} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 px-4 py-3">
            <p className="text-xs text-slate-500 dark:text-slate-400">{item.label}</p>
            <p className="mt-0.5 text-xl font-semibold dark:text-white">{item.value}</p>
          </div>
        ))}
      </div>
    )}

    {showCacheForm && (
      <form onSubmit={handleCreateCacheConfig} className="grid gap-3 rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-900/10 p-4 sm:grid-cols-2 lg:grid-cols-3">
        <input value={newCacheName} onChange={(e) => setNewCacheName(e.target.value)} className={inputCls} placeholder="Profile name" required />
        <input value={newCacheTtlSeconds} onChange={(e) => setNewCacheTtlSeconds(e.target.value)} className={inputCls} placeholder="TTL seconds" type="number" min="1" />
        <input value={newCacheMaxEntries} onChange={(e) => setNewCacheMaxEntries(e.target.value)} className={inputCls} placeholder="Max entries" type="number" min="1" />
        <input value={newCacheEvictionPolicy} onChange={(e) => setNewCacheEvictionPolicy(e.target.value)} className={inputCls} placeholder="Eviction policy" />
        <input value={newCacheSimilarityThreshold} onChange={(e) => setNewCacheSimilarityThreshold(e.target.value)} className={inputCls} placeholder="Similarity threshold" type="number" min="0" max="1" step="0.01" />
        <input value={newCacheEmbeddingModel} onChange={(e) => setNewCacheEmbeddingModel(e.target.value)} className={inputCls} placeholder="Embedding model (optional)" />
        <input value={newCacheScopeModels} onChange={(e) => setNewCacheScopeModels(e.target.value)} className={`${inputCls} sm:col-span-2`} placeholder="Scoped models (csv)" />
        <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
          <input type="checkbox" checked={newCacheEnabled} onChange={(e) => setNewCacheEnabled(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
          Profile enabled
        </label>
        <textarea value={newCacheConfigStr} onChange={(e) => { setNewCacheConfigStr(e.target.value); setCacheConfigError('') }} className={`${inputCls} min-h-[110px] font-mono text-xs sm:col-span-2 lg:col-span-3`} placeholder='{"mode":"semantic"}' />
        {cacheConfigError && <p className="text-xs text-red-500 sm:col-span-2 lg:col-span-3">{cacheConfigError}</p>}
        <div className="sm:col-span-2 lg:col-span-3">
          <button type="submit" disabled={creatingCacheConfig} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
            {creatingCacheConfig ? 'Creating...' : 'Create cache profile'}
          </button>
        </div>
      </form>
    )}

    <div className="grid gap-3 lg:grid-cols-2">
      {cacheConfigs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400 lg:col-span-2">
          No response cache profiles configured yet.
        </div>
      ) : cacheConfigs.map((config) => {
        const detail = cacheDetails[config.id] ?? config
        const isExpanded = expandedCacheId === config.id
        return (
          <div key={config.id} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm dark:text-slate-100">{config.name}</span>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${config.is_enabled ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'}`}>
                    {config.is_enabled ? 'enabled' : 'disabled'}
                  </span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                    {config.eviction_policy}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                  <span className="rounded-full bg-sky-100 px-2 py-0.5 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300">ttl: {config.ttl_seconds}s</span>
                  <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">entries: {config.max_entries.toLocaleString()}</span>
                  <span className="rounded-full bg-violet-100 px-2 py-0.5 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300">threshold: {Number(config.similarity_threshold).toFixed(2)}</span>
                  <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">hits: {config.total_hits.toLocaleString()}</span>
                  <span className="rounded-full bg-rose-100 px-2 py-0.5 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300">misses: {config.total_misses.toLocaleString()}</span>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => void handleLoadCacheDetails(config.id)} className="rounded-lg px-2 py-1 text-xs text-slate-500 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors">
                  {isExpanded ? 'Hide details' : 'Details'}
                </button>
                <button onClick={() => beginCacheEdit(config)} className="rounded-lg p-1.5 text-slate-400 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors">
                  <Pencil className="h-3.5 w-3.5" />
                </button>
                <button onClick={() => void handleDeleteCacheConfig(config.id)} className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            {isExpanded && (
              <div className="mt-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/30 p-4">
                {loadingCacheDetail[config.id] ? (
                  <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Loading cache details...
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                      <div>
                        <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">Embedding</p>
                        <p className="mt-1 text-sm dark:text-white">{detail.embedding_model || '—'}</p>
                      </div>
                      <div>
                        <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">Scoped models</p>
                        <p className="mt-1 text-sm dark:text-white">{detail.scope_models.length ? detail.scope_models.join(', ') : 'All models'}</p>
                      </div>
                      <div>
                        <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">Savings</p>
                        <p className="mt-1 text-sm dark:text-white">${Number(detail.total_savings_usd || 0).toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">Updated</p>
                        <p className="mt-1 text-sm dark:text-white">{new Date(detail.updated_at).toLocaleString()}</p>
                      </div>
                    </div>
                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">Config JSON</p>
                      <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-950/95 px-3 py-3 text-xs text-slate-100">{JSON.stringify(detail.config ?? {}, null, 2)}</pre>
                    </div>
                  </div>
                )}
              </div>
            )}

            {cacheEditState?.id === config.id && (
              <div className="mt-4 grid gap-3 rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/40 dark:bg-indigo-900/10 p-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <p className="text-sm font-semibold text-indigo-800 dark:text-indigo-300">Edit cache profile</p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Update TTL, scope, and JSON config without leaving Gateway.</p>
                </div>
                <input value={cacheEditState.name} onChange={(e) => setCacheEditState({ ...cacheEditState, name: e.target.value })} className={inputCls} placeholder="Profile name" />
                <input value={cacheEditState.ttlSeconds} onChange={(e) => setCacheEditState({ ...cacheEditState, ttlSeconds: e.target.value })} className={inputCls} placeholder="TTL seconds" type="number" min="1" />
                <input value={cacheEditState.maxEntries} onChange={(e) => setCacheEditState({ ...cacheEditState, maxEntries: e.target.value })} className={inputCls} placeholder="Max entries" type="number" min="1" />
                <input value={cacheEditState.evictionPolicy} onChange={(e) => setCacheEditState({ ...cacheEditState, evictionPolicy: e.target.value })} className={inputCls} placeholder="Eviction policy" />
                <input value={cacheEditState.similarityThreshold} onChange={(e) => setCacheEditState({ ...cacheEditState, similarityThreshold: e.target.value })} className={inputCls} placeholder="Similarity threshold" type="number" min="0" max="1" step="0.01" />
                <input value={cacheEditState.embeddingModel} onChange={(e) => setCacheEditState({ ...cacheEditState, embeddingModel: e.target.value })} className={inputCls} placeholder="Embedding model" />
                <input value={cacheEditState.scopeModels} onChange={(e) => setCacheEditState({ ...cacheEditState, scopeModels: e.target.value })} className={`${inputCls} sm:col-span-2`} placeholder="Scoped models (csv)" />
                <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                  <input type="checkbox" checked={cacheEditState.isEnabled} onChange={(e) => setCacheEditState({ ...cacheEditState, isEnabled: e.target.checked })} className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                  Profile enabled
                </label>
                <textarea value={cacheEditState.configStr} onChange={(e) => { setCacheEditState({ ...cacheEditState, configStr: e.target.value }); setCacheConfigError('') }} className={`${inputCls} min-h-[110px] font-mono text-xs sm:col-span-2`} placeholder='{"mode":"semantic"}' />
                {cacheConfigError && <p className="text-xs text-red-500 sm:col-span-2">{cacheConfigError}</p>}
                <div className="sm:col-span-2 flex items-center gap-2">
                  <button onClick={() => void handleSaveCacheEdit()} disabled={savingCacheEdit} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                    {savingCacheEdit ? 'Saving...' : 'Save changes'}
                  </button>
                  <button onClick={() => setCacheEditState(null)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  </section>

  </div>
  )
}
