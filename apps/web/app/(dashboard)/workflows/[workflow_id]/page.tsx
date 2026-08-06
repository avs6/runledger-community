import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getWorkflow, getWorkflowRuns, getWorkflowCost } from '@/lib/api'
import type { WorkflowDefinitionResponse, WorkflowRunResponse, WorkflowCostAttribution } from '@/types/api'

function money(v: number | null | undefined) {
  if (!v) return '$0.00'
  if (v >= 1) return `$${v.toFixed(2)}`
  if (v >= 0.001) return `$${v.toFixed(4)}`
  return `$${v.toFixed(6)}`
}

function compact(value: number) {
  return new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

function duration(ms: number | null | undefined) {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function statusColor(status: string) {
  const map: Record<string, string> = {
    completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    running: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    pending: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    cancelled: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  }
  return map[status] || map.pending
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

export default async function WorkflowDetailPage({ params }: { params: { workflow_id: string } }) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  let wf: WorkflowDefinitionResponse | null = null
  let runs: WorkflowRunResponse[] = []
  let cost: WorkflowCostAttribution | null = null
  let totalRuns = 0

  try {
    ;[wf, cost] = await Promise.all([
      getWorkflow(session.apiKey, params.workflow_id),
      getWorkflowCost(session.apiKey, params.workflow_id),
    ])
    const runsData = await getWorkflowRuns(session.apiKey, params.workflow_id, { limit: 30 })
    runs = runsData.runs
    totalRuns = runsData.total
  } catch {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-sm text-slate-500">Workflow not found or API unavailable.</p>
      </div>
    )
  }

  if (!wf) return null

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Link href="/workflows" className="text-sm text-blue-600 hover:underline dark:text-blue-400">
          Workflows
        </Link>
        <span className="text-slate-400">/</span>
        <h1 className="text-xl font-bold tracking-[-0.04em] text-slate-950 dark:text-slate-50">
          {wf.name}
        </h1>
        <span className={`ml-2 inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${wf.status === 'active' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>
          {wf.status}
        </span>
      </div>

      {wf.description && (
        <p className="text-sm text-slate-600 dark:text-slate-400">{wf.description}</p>
      )}

      {cost && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Total Runs" value={String(cost.total_runs)} />
          <StatCard label="Total Cost" value={money(cost.total_cost)} />
          <StatCard label="Avg Cost / Run" value={money(cost.avg_cost_per_run)} />
          <StatCard label="Steps Defined" value={String(wf.steps_schema.length)} />
        </div>
      )}

      {cost && cost.cost_by_step.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
          <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
            <h2 className="text-sm font-semibold text-slate-950 dark:text-slate-50">Cost by Step</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-100 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500 dark:border-slate-800">
                  <th className="px-4 py-3">Step</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Total Cost</th>
                  <th className="px-4 py-3">Avg Cost</th>
                  <th className="px-4 py-3">Invocations</th>
                </tr>
              </thead>
              <tbody>
                {cost.cost_by_step.map((s, i) => (
                  <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="px-4 py-3 text-xs font-medium text-slate-700 dark:text-slate-300">{s.step_name}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{s.step_type}</td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{money(s.total_cost)}</td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{money(s.avg_cost)}</td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{s.invocation_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
        <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <h2 className="text-sm font-semibold text-slate-950 dark:text-slate-50">
            Runs ({totalRuns})
          </h2>
        </div>
        {runs.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">No runs recorded for this workflow.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-100 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500 dark:border-slate-800">
                  <th className="px-4 py-3">Run ID</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Cost</th>
                  <th className="px-4 py-3">Tokens</th>
                  <th className="px-4 py-3">Duration</th>
                  <th className="px-4 py-3">Steps</th>
                  <th className="px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id} className="border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50">
                    <td className="px-4 py-3">
                      <Link href={`/workflows/${wf.id}/runs/${run.id}`} className="text-xs font-mono text-blue-600 hover:underline dark:text-blue-400">
                        {run.id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusColor(run.status)}`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{money(run.total_cost)}</td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{compact(run.total_tokens)}</td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{duration(run.total_duration_ms)}</td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{run.steps.length}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{new Date(run.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
