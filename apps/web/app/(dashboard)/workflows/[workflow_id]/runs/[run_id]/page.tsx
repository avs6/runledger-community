import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getWorkflowRun, getWorkflow, getBudgetControlBuildPosture } from '@/lib/api'
import type { WorkflowRunResponse, WorkflowStepResponse } from '@/types/api'

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
    skipped: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    cancelled: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  }
  return map[status] || map.pending
}

function barColor(status: string) {
  const map: Record<string, string> = {
    completed: 'bg-emerald-400 dark:bg-emerald-500',
    running: 'bg-blue-400 dark:bg-blue-500',
    pending: 'bg-slate-300 dark:bg-slate-600',
    failed: 'bg-red-400 dark:bg-red-500',
    skipped: 'bg-amber-300 dark:bg-amber-500',
  }
  return map[status] || map.pending
}

function stepTypeIcon(type: string) {
  const map: Record<string, string> = {
    agent: '\u{1F916}',
    model: '\u{1F4AC}',
    tool: '\u{1F527}',
    human: '\u{1F464}',
    condition: '\u{2194}',
    parallel: '\u{2261}',
  }
  return map[type] || '\u{25CF}'
}

function TimelineBar({ step, maxDuration }: { step: WorkflowStepResponse; maxDuration: number }) {
  const w = maxDuration > 0 && step.duration_ms ? Math.max(4, (step.duration_ms / maxDuration) * 100) : 4

  return (
    <div className="group rounded-xl border border-slate-200 bg-white/90 p-4 shadow-sm transition hover:border-blue-200 dark:border-slate-700 dark:bg-slate-900/80 dark:hover:border-blue-500">
      <div className="flex items-center gap-3">
        <span className="text-lg" title={step.step_type}>{stepTypeIcon(step.step_type)}</span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">{step.name}</span>
            <span className={`inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${statusColor(step.status)}`}>
              {step.status}
            </span>
            {step.model && (
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {step.model}
              </span>
            )}
            {step.tool && (
              <span className="rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-medium text-violet-600 dark:bg-violet-900/40 dark:text-violet-300">
                {step.tool}
              </span>
            )}
          </div>
          <div className="mt-2 h-3 w-full rounded-full bg-slate-100 dark:bg-slate-800">
            <div
              className={`h-3 rounded-full transition-all ${barColor(step.status)}`}
              style={{ width: `${w}%` }}
            />
          </div>
          <div className="mt-1.5 flex items-center gap-4 text-[10px] text-slate-500">
            <span>{duration(step.duration_ms)}</span>
            <span>{money(step.cost)}</span>
            <span>{compact(step.tokens)} tokens</span>
            {step.error && (
              <span className="text-red-500 truncate max-w-[200px]" title={step.error}>
                {step.error}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default async function WorkflowRunDetailPage({
  params,
}: {
  params: { workflow_id: string; run_id: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  let run: WorkflowRunResponse | null = null
  let workflowName = ''

  try {
    ;[run, { name: workflowName }] = await Promise.all([
      getWorkflowRun(session.apiKey, params.workflow_id, params.run_id),
      getWorkflow(session.apiKey, params.workflow_id),
    ])
  } catch {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-sm text-slate-500">Run not found or API unavailable.</p>
      </div>
    )
  }

  if (!run) return null

  const budgetControlBuildPosture = await getBudgetControlBuildPosture(session.apiKey).catch(() => null)

  const maxDuration = Math.max(...run.steps.map((s) => s.duration_ms ?? 0), 1)

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Link href="/workflows" className="text-blue-600 hover:underline dark:text-blue-400">
          Workflows
        </Link>
        <span className="text-slate-400">/</span>
        <Link href={`/workflows/${params.workflow_id}`} className="text-blue-600 hover:underline dark:text-blue-400">
          {workflowName}
        </Link>
        <span className="text-slate-400">/</span>
        <span className="font-mono text-slate-600 dark:text-slate-400">{run.id.slice(0, 8)}</span>
        <span className={`ml-2 inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusColor(run.status)}`}>
          {run.status}
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: 'Status', value: run.status },
          { label: 'Cost', value: money(run.total_cost) },
          { label: 'Tokens', value: compact(run.total_tokens) },
          { label: 'Duration', value: duration(run.total_duration_ms) },
        ].map((item) => (
          <div key={item.label} className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm ring-1 ring-white/70 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">{item.label}</p>
            <p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-950 dark:text-slate-50">{item.value}</p>
          </div>
        ))}
      </div>

      {budgetControlBuildPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="flex items-center gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Budget Control — Build Posture</p>
          </div>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetControlBuildPosture.budget_policy.active_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Breached</p>
              <p className={`mt-1 text-lg font-semibold ${budgetControlBuildPosture.budget_policy.breached_budgets > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{budgetControlBuildPosture.budget_policy.breached_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Avg Utilization</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">{budgetControlBuildPosture.budget_policy.avg_utilization_pct.toFixed(1)}%</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Scope Types</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{Object.keys(budgetControlBuildPosture.scope_context).length}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
            <Link href="/budgets" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
            <Link href="/budgets?tab=overrides" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Overrides</Link>
            <Link href="/billing" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Billing</Link>
          </div>
        </div>
      )}

      {run.trigger && (
        <div className="text-xs text-slate-500">
          Trigger: <span className="font-medium text-slate-700 dark:text-slate-300">{run.trigger}</span>
        </div>
      )}

      {run.error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300">
          {run.error}
        </div>
      )}

      <div>
        <h2 className="mb-3 text-sm font-semibold text-slate-950 dark:text-slate-50">
          Step Timeline ({run.steps.length} steps)
        </h2>
        <div className="space-y-2">
          {run.steps.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700">
              No steps recorded for this run.
            </div>
          ) : (
            run.steps.map((step) => (
              <TimelineBar key={step.id} step={step} maxDuration={maxDuration} />
            ))
          )}
        </div>
      </div>
    </div>
  )
}
