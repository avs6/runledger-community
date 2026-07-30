import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { ArrowRight, GitBranch, Layers3, Route, ShieldCheck } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getRuns } from '@/lib/api'
import RequestFlowSankey from '@/components/dashboard/RequestFlowSankey'

function pct(value: number, total: number) {
  if (total <= 0) return '0%'
  return `${Math.round((value / total) * 100)}%`
}

export default async function RequestFlowPage() {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const runs = await getRuns(session.apiKey, { limit: 200 })
  const items = runs.items
  const uniqueIntents = new Set(items.map((run) => run.feature_tag || 'General / Untagged')).size
  const uniqueModels = new Set(items.map((run) => run.primary_model || 'Model Unknown')).size
  const succeeded = items.filter((run) => run.status === 'succeeded').length

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-teal-500/10 px-2.5 py-1 text-xs font-semibold text-teal-700 dark:text-teal-300">
            <Route className="h-3.5 w-3.5" />
            Phase 5 MVP
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">
            AI Request Flow
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
            Follow recent AI traffic from request volume into intent, model selection, and final result. This is the foundation for the deeper Skill, Agent, Tool, and Outcome Sankey.
          </p>
        </div>
        <Link
          href="/runs"
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-teal-300 hover:text-teal-700 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300 dark:hover:border-teal-500/40 dark:hover:text-teal-300"
        >
          Inspect runs <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {[
          { label: 'Runs sampled', value: items.length.toLocaleString(), icon: GitBranch },
          { label: 'Intent groups', value: uniqueIntents.toLocaleString(), icon: Layers3 },
          { label: 'Models observed', value: uniqueModels.toLocaleString(), icon: Route },
          { label: 'Success rate', value: pct(succeeded, items.length), icon: ShieldCheck },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950/45">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{label}</p>
              <Icon className="h-4 w-4 text-teal-600 dark:text-teal-300" />
            </div>
            <p className="mt-3 text-2xl font-semibold text-slate-950 dark:text-white">{value}</p>
          </div>
        ))}
      </div>

      <RequestFlowSankey runs={items} />

      <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-5 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-950/35 dark:text-slate-300">
        <p className="font-semibold text-slate-950 dark:text-white">Next analytics layer</p>
        <p className="mt-1">
          The current MVP uses fields RunLedger already records on recent runs. The Phase 5 full contract will add Skill, Agent, Tool, cache, routing reason, and optimization attribution into this same flow.
        </p>
      </div>
    </div>
  )
}
