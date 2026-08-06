import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getWorkflows } from '@/lib/api'
import type { WorkflowDefinitionResponse } from '@/types/api'

function statusBadge(status: string) {
  const colors: Record<string, string> = {
    active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    archived: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
  }
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${colors[status] || colors.active}`}>
      {status}
    </span>
  )
}

function WorkflowCard({ wf }: { wf: WorkflowDefinitionResponse }) {
  const stepCount = wf.steps_schema?.length ?? 0

  return (
    <Link
      href={`/workflows/${wf.id}`}
      className="group rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm ring-1 ring-white/70 transition hover:border-blue-300 hover:shadow-md dark:border-slate-700 dark:bg-slate-900/80 dark:ring-transparent dark:hover:border-blue-500"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-slate-950 dark:text-slate-50">
            {wf.name}
          </h3>
          {wf.description && (
            <p className="mt-1 line-clamp-2 text-xs text-slate-500">{wf.description}</p>
          )}
        </div>
        {statusBadge(wf.status)}
      </div>
      <div className="mt-4 flex items-center gap-4 border-t border-slate-100 pt-3 text-[11px] text-slate-500 dark:border-slate-800">
        <span>{stepCount} step{stepCount !== 1 ? 's' : ''} defined</span>
        <span className="ml-auto text-[10px] text-slate-400">
          {new Date(wf.created_at).toLocaleDateString()}
        </span>
      </div>
    </Link>
  )
}

export default async function WorkflowsPage() {
  const session = await getServerSession(authOptions)
  if (!session) return null

  let workflows: WorkflowDefinitionResponse[] = []
  let total = 0

  try {
    const data = await getWorkflows(session.apiKey, { limit: 100 })
    workflows = data.workflows
    total = data.total
  } catch {
    // API may not be reachable
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-[-0.04em] text-slate-950 dark:text-slate-50">
            Workflows
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {total} workflow{total !== 1 ? 's' : ''} defined
          </p>
        </div>
      </div>

      {workflows.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 p-12 text-center dark:border-slate-700 dark:bg-slate-900/50">
          <p className="text-sm text-slate-500">
            No workflows defined yet. Use the API to create workflow definitions and track runs.
          </p>
          <pre className="mx-auto mt-4 max-w-lg rounded-xl bg-slate-100 p-4 text-left text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300">
{`POST /workflows
{
  "name": "customer-support",
  "description": "Route, classify, respond",
  "steps_schema": [
    {"name": "classify", "type": "model"},
    {"name": "respond", "type": "agent"}
  ]
}`}
          </pre>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {workflows.map((wf) => (
            <WorkflowCard key={wf.id} wf={wf} />
          ))}
        </div>
      )}
    </div>
  )
}
