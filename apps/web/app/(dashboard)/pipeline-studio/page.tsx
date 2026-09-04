'use client'

import Link from 'next/link'
import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { GitBranch, RefreshCw, Activity, Shield, DollarSign, Cpu } from 'lucide-react'
import { getPipelineStudioPosture } from '@/lib/api'
import type { PipelineStudioPosture } from '@/types/api'

const stageMeta: Record<string, { label: string; color: string; icon: string }> = {
  ingest: { label: 'Ingest', color: 'bg-blue-500', icon: '📥' },
  routing: { label: 'Routing', color: 'bg-indigo-500', icon: '🔀' },
  enforcement: { label: 'Enforcement', color: 'bg-red-500', icon: '🛡️' },
  execution: { label: 'Execution', color: 'bg-emerald-500', icon: '⚡' },
  reporting: { label: 'Reporting', color: 'bg-amber-500', icon: '📊' },
}

export default function PipelineStudioPage() {
  const { data: session } = useSession()
  const [posture, setPosture] = useState<PipelineStudioPosture | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!session?.apiKey) return
    setLoading(true)
    try {
      const data = await getPipelineStudioPosture(session.apiKey)
      setPosture(data)
    } catch {
      toast.error('Failed to load pipeline posture')
    } finally {
      setLoading(false)
    }
  }, [session?.apiKey])

  useEffect(() => { refresh() }, [refresh])

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold dark:text-white flex items-center gap-2">
            <GitBranch className="h-6 w-6 text-indigo-500" />
            Pipeline Studio
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Visualize and author ingest → routing → enforcement → execution → reporting flows.
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {posture && (
        <>
          <div className="rounded-xl border border-indigo-200 dark:border-indigo-800 bg-white dark:bg-slate-800/40 p-5 space-y-4">
            <h2 className="text-base font-semibold dark:text-white">Pipeline Flow</h2>
            <div className="flex items-center gap-2 overflow-x-auto pb-2">
              {posture.pipeline_model.stages.map((stage, i) => {
                const meta = stageMeta[stage] || { label: stage, color: 'bg-slate-500', icon: '⬤' }
                return (
                  <div key={stage} className="flex items-center gap-2">
                    {i > 0 && (
                      <svg className="h-4 w-8 flex-shrink-0 text-slate-300 dark:text-slate-600" viewBox="0 0 32 16">
                        <path d="M0 8 L24 8 M20 4 L28 8 L20 12" fill="none" stroke="currentColor" strokeWidth="2" />
                      </svg>
                    )}
                    <div className="flex-shrink-0 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 px-4 py-3 text-center min-w-[120px]">
                      <span className="text-xl">{meta.icon}</span>
                      <p className="mt-1 text-xs font-semibold dark:text-white">{meta.label}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl border border-indigo-200 dark:border-indigo-800 bg-white dark:bg-slate-800/40 p-5 space-y-3">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-indigo-500" />
                <h3 className="text-sm font-semibold dark:text-white">Routing Nodes</h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-slate-500">Active routes</span><span className="font-medium dark:text-white">{posture.pipeline_model.routing_nodes.active_routes}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Providers</span><span className="font-medium dark:text-white">{posture.pipeline_model.routing_nodes.distinct_providers}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Routing groups</span><span className="font-medium dark:text-white">{posture.pipeline_model.routing_nodes.routing_groups}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Routing policies</span><span className="font-medium dark:text-white">{posture.pipeline_model.routing_nodes.routing_policies}</span></div>
              </div>
            </div>

            <div className="rounded-xl border border-blue-200 dark:border-blue-800 bg-white dark:bg-slate-800/40 p-5 space-y-3">
              <div className="flex items-center gap-2">
                <Cpu className="h-4 w-4 text-blue-500" />
                <h3 className="text-sm font-semibold dark:text-white">Traffic Overlay</h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-slate-500">Requests (7d)</span><span className="font-medium dark:text-white">{posture.traffic_overlay.requests_7d}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Requests (30d)</span><span className="font-medium dark:text-white">{posture.traffic_overlay.requests_30d}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Cache hits (7d)</span><span className="font-medium dark:text-white">{posture.traffic_overlay.cache_hits_7d}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Audit events (30d)</span><span className="font-medium dark:text-white">{posture.traffic_overlay.audit_events_30d}</span></div>
              </div>
            </div>

            <div className="rounded-xl border border-red-200 dark:border-red-800 bg-white dark:bg-slate-800/40 p-5 space-y-3">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-red-500" />
                <h3 className="text-sm font-semibold dark:text-white">Enforcement Overlay</h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-slate-500">Guardrail rules</span><span className="font-medium dark:text-white">{posture.enforcement_overlay.guardrail_rules}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Events (30d)</span><span className="font-medium dark:text-white">{posture.enforcement_overlay.guardrail_events_30d}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Blocked (30d)</span><span className="font-medium dark:text-white">{posture.enforcement_overlay.blocked_events_30d}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Tool policies</span><span className="font-medium dark:text-white">{posture.enforcement_overlay.tool_policies}</span></div>
              </div>
            </div>

            <div className="rounded-xl border border-amber-200 dark:border-amber-800 bg-white dark:bg-slate-800/40 p-5 space-y-3">
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-amber-500" />
                <h3 className="text-sm font-semibold dark:text-white">FinOps & Build</h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-slate-500">Budgets</span><span className="font-medium dark:text-white">{posture.finops_overlay.budgets}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Cost tracking</span><span className="font-medium dark:text-white">{posture.finops_overlay.cost_tracking}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Agents</span><span className="font-medium dark:text-white">{posture.build_overlay.agents}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Workflows</span><span className="font-medium dark:text-white">{posture.build_overlay.workflows}</span></div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-5 space-y-3">
            <h3 className="text-sm font-semibold dark:text-white">Runtime Architecture</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-500">Data Plane</p>
                <p className="mt-1 text-sm font-semibold dark:text-white">{posture.pipeline_model.execution_runtime.data_plane}</p>
                <p className="text-xs text-slate-400">Rust gateway — hot-path execution</p>
              </div>
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-500">Control Plane</p>
                <p className="mt-1 text-sm font-semibold dark:text-white">{posture.pipeline_model.execution_runtime.control_plane}</p>
                <p className="text-xs text-slate-400">Python API — config, analytics, management</p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link href="/gateway" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Model Gateway</Link>
            <Link href="/analytics" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Analytics</Link>
            <Link href="/guardrails" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Guardrails</Link>
            <Link href="/governance" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Governance</Link>
            <Link href="/budgets" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Budgets</Link>
            <Link href="/workflows" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Workflows</Link>
            <Link href="/agents" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">Agents</Link>
          </div>
        </>
      )}
    </div>
  )
}
