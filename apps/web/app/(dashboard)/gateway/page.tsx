'use client'

import Link from 'next/link'
import { Network, RefreshCw } from 'lucide-react'
import { OverviewTab } from './_components/OverviewTab'
import { RateLimitsTab } from './_components/RateLimitsTab'
import { CacheTab } from './_components/CacheTab'
import { RoutesTab } from './_components/RoutesTab'
import { PoliciesTab } from './_components/PoliciesTab'
import { AdvancedTab } from './_components/AdvancedTab'
import { RouteDiffDialog } from './_components/RouteDiffDialog'
import { SectionError } from '@/components/ui/async-card'
import { GatewayContext, useGatewayState, type Tab } from './_components/useGatewayState'

export default function GatewayPage() {
  const gateway = useGatewayState()
  const {
    canView,
    canManage,
    sectionErrors,
    confirmDialog,
    gatewayRoutes,
    gatewayStats,
    routingGroups,
    routingPolicies,
    cacheConfigs,
    loading,
    activeTab,
    setTab,
    load,
  } = gateway

  if (!canView) {
    return (
      <div className="p-8" role="alert">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Model Gateway</h1>
        <p className="mt-2 text-sm text-slate-500">Viewing the Model Gateway needs a workspace admin; changing it needs an organization admin.</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <RefreshCw className="h-5 w-5 animate-spin text-slate-400" />
      </div>
    )
  }

  return (
    <GatewayContext.Provider value={gateway}>
    {confirmDialog}
    <RouteDiffDialog />
    <div className="space-y-3">
      {/* ── Header ─────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/25">
            <Network className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Model Gateway</h1>
            <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">
              OpenAI-compatible proxy with caching, fallback, and intelligent routing. Point <code className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">base_url</code> to <code className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">/gateway</code>.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <button onClick={load} aria-label="Refresh gateway data" className="flex items-center gap-1 rounded-lg bg-slate-100 dark:bg-slate-800 px-2.5 py-1 text-[10px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700">
            <RefreshCw className="h-3 w-3" />Refresh
          </button>
          {[
            { label: 'Provider Profiles', href: '/provider-profiles' },
            { label: 'Guardrails', href: '/guardrails' },
            { label: 'API Keys', href: '/api-keys' },
            { label: 'Telemetry', href: '/monitoring/telemetry' },
            { label: 'MCP', href: '/mcp-registry' },
          ].map(({ label, href }) => (
            <Link key={label} href={href} className="rounded-full bg-violet-100 dark:bg-violet-900/30 px-2.5 py-1 text-[10px] font-semibold text-violet-700 dark:text-violet-300 hover:bg-violet-200 dark:hover:bg-violet-800/40 transition-colors">{label}</Link>
          ))}
        </div>
      </div>

      {!canManage && (
        <p role="status" className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
          Read-only: routes, groups and policies are changed by an organization admin.
        </p>
      )}
      {(['routes', 'groups', 'stats', 'policies'] as const).map((name) =>
        sectionErrors[name] ? <SectionError key={name} message={sectionErrors[name]} onRetry={load} /> : null,
      )}

      {/* ── KPI strip ──────────────────────────────────── */}
      <div className="grid grid-cols-8 gap-2">
        {[
          { label: 'Requests', value: gatewayStats?.total_requests?.toLocaleString() ?? '—' },
          { label: 'Cache Hits', value: gatewayStats?.cache_hits?.toLocaleString() ?? '—' },
          { label: 'Hit Rate', value: gatewayStats?.cache_hit_rate ? `${(parseFloat(gatewayStats.cache_hit_rate) * 100).toFixed(1)}%` : '—', accent: true },
          { label: 'Avg Latency', value: gatewayStats?.avg_latency_ms ? `${parseFloat(gatewayStats.avg_latency_ms).toFixed(0)}ms` : '—' },
          { label: 'Routes', value: gatewayRoutes.length },
          { label: 'Groups', value: routingGroups.length },
          { label: 'Policies', value: routingPolicies.length },
          { label: 'Cache Configs', value: activeTab === 'cache' || cacheConfigs.length ? cacheConfigs.length : '—' },
        ].map(({ label, value, accent }) => (
          <div key={label} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-2.5 py-2 text-center">
            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{label}</p>
            <p className={`text-sm font-bold ${accent ? 'text-violet-600 dark:text-violet-400' : 'text-slate-900 dark:text-white'}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* ── Tab bar ────────────────────────────────────── */}
      <div role="tablist" aria-label="Gateway sections" className="flex items-center gap-1 border-b border-slate-200 dark:border-slate-700 pb-px">
        {([
          ['overview', 'Overview'],
          ['routes', 'Routes'],
          ['policies', 'Policies'],
          ['cache', 'Cache'],
          ['rate-limits', 'Rate Limits'],
          ['advanced', 'Advanced'],
        ] as [Tab, string][]).map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={activeTab === key}
            onClick={() => setTab(key)}
            className={`px-3 py-1.5 text-xs font-semibold rounded-t-lg transition-colors ${activeTab === key ? 'bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300 border-b-2 border-violet-500' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'}`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ═══════════════════════════════════════════════════
          TAB: Overview
         ═══════════════════════════════════════════════════ */}
      {activeTab === 'overview' && <OverviewTab />}

      {/* ═══════════════════════════════════════════════════
          TAB: Rate Limits
         ═══════════════════════════════════════════════════ */}
      {activeTab === 'rate-limits' && <RateLimitsTab />}

      {/* ═══════════════════════════════════════════════════
          TAB: Cache — economics + profiles
         ═══════════════════════════════════════════════════ */}
      {activeTab === 'cache' && <CacheTab />}

      {/* ═══════════════════════════════════════════════════
          TAB: Routes — groups + comparison + provider routes
         ═══════════════════════════════════════════════════ */}
      {activeTab === 'routes' && <RoutesTab />}

      {/* ═══════════════════════════════════════════════════
          TAB: Policies — routing policies + routing log
         ═══════════════════════════════════════════════════ */}
      {activeTab === 'policies' && <PoliciesTab />}

      {/* ═══════════════════════════════════════════════════
          TAB: Advanced — benchmark, passthrough, budget tiers, model quotas, flywheel
         ═══════════════════════════════════════════════════ */}
      {activeTab === 'advanced' && <AdvancedTab />}

    </div>
    </GatewayContext.Provider>
  )
}
