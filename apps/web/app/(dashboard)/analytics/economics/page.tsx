'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { ArrowRight, BarChart3, DollarSign, Network, Receipt, Sparkles, TrendingDown, Wallet } from 'lucide-react'
import { getAnnotations, getEconomicsFinopsPosture, getEconomicsGatewayPosture, getRegressions, getTopWorkflows } from '@/lib/api'
import type { Annotation, EconomicsFinopsPosture, EconomicsGatewayPosture, RegressionList, WorkflowTopList } from '@/types/api'
import ChangeImpactPanel from '@/components/economics/ChangeImpactPanel'
import RegressionTable from '@/components/economics/RegressionTable'
import AnnotationForm from '@/components/economics/AnnotationForm'

function Section({
  title,
  children,
  description,
}: {
  title: string
  children: React.ReactNode
  description?: string
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-4">
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
        {description ? <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p> : null}
      </div>
      {children}
    </div>
  )
}

function Skeleton() {
  return <div className="h-40 w-full animate-pulse rounded-lg bg-slate-100 dark:bg-slate-700" />
}

function money(value: string) {
  return `$${parseFloat(value).toFixed(4)}`
}

export default function EconomicsPage() {
  const { data: session } = useSession()
  const apiKey = session?.apiKey ?? ''

  const [workflows, setWorkflows] = useState<WorkflowTopList | null>(null)
  const [regressions, setRegressions] = useState<RegressionList | null>(null)
  const [annotations, setAnnotations] = useState<Annotation[]>([])
  const [loadingWorkflows, setLoadingWorkflows] = useState(true)
  const [loadingRegressions, setLoadingRegressions] = useState(true)
  const [loadingAnnotations, setLoadingAnnotations] = useState(true)
  const [finopsPosture, setFinopsPosture] = useState<EconomicsFinopsPosture | null>(null)
  const [gatewayPosture, setGatewayPosture] = useState<EconomicsGatewayPosture | null>(null)

  useEffect(() => {
    if (!apiKey) return

    getTopWorkflows(apiKey, { metric: 'cost', limit: 10 })
      .then(setWorkflows)
      .finally(() => setLoadingWorkflows(false))

    getRegressions(apiKey)
      .then(setRegressions)
      .finally(() => setLoadingRegressions(false))

    getAnnotations(apiKey)
      .then((data) => setAnnotations(data.items))
      .finally(() => setLoadingAnnotations(false))

    getEconomicsFinopsPosture(apiKey)
      .then(setFinopsPosture)
      .catch(() => {})

    getEconomicsGatewayPosture(apiKey)
      .then(setGatewayPosture)
      .catch(() => {})
  }, [apiKey])

  function handleAnnotationCreated(annotation: Annotation) {
    setAnnotations((prev) => [annotation, ...prev])
  }

  const highestWorkflow = workflows?.items[0] ?? null
  const highestRegression = regressions?.items[0] ?? null

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Economics Overview</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-[-0.05em] text-slate-950 dark:text-white">Observe cost, savings, and billing together</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
            Start here for cost regressions and change impact, then move into Model Usage, Cost &amp; Savings, and Billing for the deeper economics workflows.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/model-usage" className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-blue-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
            Model Usage <BarChart3 className="h-4 w-4" />
          </Link>
          <Link href="/cost-savings" className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-blue-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
            Cost &amp; Savings <Sparkles className="h-4 w-4" />
          </Link>
          <Link href="/billing?tab=summary&months=6" className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-blue-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
            Billing Summary <Receipt className="h-4 w-4" />
          </Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Top workflow</p>
          <p className="mt-2 text-lg font-semibold text-slate-950 dark:text-slate-50">{highestWorkflow?.feature_tag ?? 'No workflow data'}</p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {highestWorkflow ? `${money(highestWorkflow.total_cost_usd)} total cost across ${highestWorkflow.run_count} runs.` : 'Send more traffic to see highest-cost workflows.'}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Top regression</p>
          <p className="mt-2 text-lg font-semibold text-slate-950 dark:text-slate-50">{highestRegression?.feature_tag ?? 'No regressions detected'}</p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {highestRegression?.change_pct ? `${parseFloat(highestRegression.change_pct).toFixed(2)}% cost delta in the latest comparison window.` : 'Regression signals appear here when cost or latency shifts materially.'}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Next step</p>
          <p className="mt-2 text-lg font-semibold text-slate-950 dark:text-slate-50">Go deeper by question</p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Use Model Usage for route/model behavior, Cost &amp; Savings for realized optimization, and Billing for finance-ready reconciliation.
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {[
          {
            title: 'Model Usage',
            body: 'Which models are driving requests, spend, latency, and quality?',
            href: '/model-usage',
            icon: BarChart3,
          },
          {
            title: 'Cost & Savings',
            body: 'Where is spend concentrated, what savings are realized, and what should we optimize next?',
            href: '/cost-savings',
            icon: DollarSign,
          },
          {
            title: 'Billing',
            body: 'Which periods are billable, what exports are needed, and how should finance reconcile the ledger?',
            href: '/billing?tab=summary&months=6',
            icon: Receipt,
          },
        ].map(({ title, body, href, icon: Icon }) => (
          <Link
            key={title}
            href={href}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/60 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-400 dark:hover:bg-slate-800"
          >
            <div className="flex items-center justify-between gap-3">
              <p className="text-lg font-semibold text-slate-950 dark:text-slate-50">{title}</p>
              <Icon className="h-5 w-5 text-blue-600" />
            </div>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{body}</p>
            <div className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-blue-700 dark:text-blue-300">
              Open <ArrowRight className="h-4 w-4" />
            </div>
          </Link>
        ))}
      </div>

      {finopsPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 shadow-sm dark:border-emerald-800 dark:bg-emerald-950/30">
          <div className="flex items-center gap-2 mb-3">
            <Wallet className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            <h2 className="text-base font-semibold text-emerald-900 dark:text-emerald-100">FinOps Budget Context</h2>
          </div>
          <p className="text-sm text-emerald-800/80 dark:text-emerald-300/70 mb-4">
            {finopsPosture.budget_context.active_budgets} active budget{finopsPosture.budget_context.active_budgets !== 1 ? 's' : ''} ·{' '}
            {finopsPosture.budget_context.breach_count} breach{finopsPosture.budget_context.breach_count !== 1 ? 'es' : ''} ·{' '}
            {finopsPosture.budget_context.active_overrides} active override{finopsPosture.budget_context.active_overrides !== 1 ? 's' : ''} ·{' '}
            {finopsPosture.notification_context.active_notifications} active notification{finopsPosture.notification_context.active_notifications !== 1 ? 's' : ''} ·{' '}
            {finopsPosture.ledger_context.ledger_snapshots} ledger snapshot{finopsPosture.ledger_context.ledger_snapshots !== 1 ? 's' : ''}
          </p>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 mb-4">
            {[
              { label: 'Budgets', value: `${finopsPosture.budget_context.active_budgets}/${finopsPosture.budget_context.budgets}` },
              { label: 'Overrides', value: `${finopsPosture.budget_context.active_overrides}/${finopsPosture.budget_context.overrides}` },
              { label: 'Notifications', value: `${finopsPosture.notification_context.active_notifications}/${finopsPosture.notification_context.notifications}` },
              { label: 'Ledger (30d)', value: String(finopsPosture.ledger_context.ledger_snapshots_30d) },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-600 dark:text-emerald-400">{label}</p>
                <p className="mt-1 text-lg font-semibold text-emerald-900 dark:text-emerald-100">{value}</p>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {[
              { label: 'Budgets', href: '/budgets' },
              { label: 'Budget Detail', href: '/budgets' },
              { label: 'Budget Overrides', href: '/budgets?tab=overrides' },
              { label: 'Notifications', href: '/budgets?tab=notifications' },
              { label: 'Billing Periods', href: '/billing' },
              { label: 'Chargeback', href: '/chargeback' },
              { label: 'Ledger', href: '/ledger' },
            ].map(({ label, href }) => (
              <Link key={label} href={href} className="rounded-lg border border-emerald-200 bg-white/80 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-100 dark:border-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 dark:hover:bg-emerald-800/50">
                {label}
              </Link>
            ))}
          </div>
        </div>
      )}

      {gatewayPosture && (
        <div className="rounded-2xl border border-violet-200 bg-violet-50/60 p-5 shadow-sm dark:border-violet-800 dark:bg-violet-950/30">
          <div className="flex items-center gap-2 mb-3">
            <Network className="h-5 w-5 text-violet-600 dark:text-violet-400" />
            <h2 className="text-base font-semibold text-violet-900 dark:text-violet-100">Gateway & Provider Context</h2>
          </div>
          <p className="text-sm text-violet-800/80 dark:text-violet-300/70 mb-4">
            {gatewayPosture.provider_context.distinct_providers} provider{gatewayPosture.provider_context.distinct_providers !== 1 ? 's' : ''} ·{' '}
            {gatewayPosture.gateway_context.active_routes} active route{gatewayPosture.gateway_context.active_routes !== 1 ? 's' : ''} ·{' '}
            {gatewayPosture.gateway_context.distinct_models} model{gatewayPosture.gateway_context.distinct_models !== 1 ? 's' : ''} ·{' '}
            {gatewayPosture.investigation_context.runs_30d} runs (30d)
          </p>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 mb-4">
            {[
              { label: 'Providers', value: String(gatewayPosture.provider_context.distinct_providers) },
              { label: 'Routes', value: `${gatewayPosture.gateway_context.active_routes}` },
              { label: 'Runs (30d)', value: String(gatewayPosture.investigation_context.runs_30d) },
              { label: 'Alerts (30d)', value: String(gatewayPosture.investigation_context.monitoring_alerts_30d) },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-violet-600 dark:text-violet-400">{label}</p>
                <p className="mt-1 text-lg font-semibold text-violet-900 dark:text-violet-100">{value}</p>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {[
              { label: 'Provider Profiles', href: '/provider-profiles' },
              { label: 'Model Gateway', href: '/gateway' },
              { label: 'Runs', href: '/runs' },
              { label: 'Request Flow', href: '/request-flow' },
              { label: 'Request Explorer', href: '/request-explorer' },
              { label: 'Monitoring', href: '/monitoring' },
            ].map(({ label, href }) => (
              <Link key={label} href={href} className="rounded-lg border border-violet-200 bg-white/80 px-3 py-1.5 text-xs font-semibold text-violet-700 hover:bg-violet-100 dark:border-violet-700 dark:bg-violet-900/40 dark:text-violet-300 dark:hover:bg-violet-800/50">
                {label}
              </Link>
            ))}
          </div>
        </div>
      )}

      <Section
        title="Top Workflows by Cost"
        description="Use this table to see which feature tags deserve deeper inspection in Cost & Savings or Request Flow."
      >
        {loadingWorkflows ? (
          <Skeleton />
        ) : workflows && workflows.items.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
                <th className="pb-1 font-medium">Feature tag</th>
                <th className="pb-1 text-right font-medium">Runs</th>
                <th className="pb-1 text-right font-medium">Avg cost</th>
                <th className="pb-1 text-right font-medium">P95 cost</th>
                <th className="pb-1 text-right font-medium">Total cost</th>
                <th className="pb-1 text-right font-medium">Calls</th>
              </tr>
            </thead>
            <tbody>
              {workflows.items.map((w, i) => (
                <tr key={i} className="border-b border-slate-100 last:border-0 dark:border-slate-700">
                  <td className="py-2 font-mono text-xs dark:text-slate-300">{w.feature_tag ?? '-'}</td>
                  <td className="py-2 text-right tabular-nums dark:text-slate-300">{w.run_count}</td>
                  <td className="py-2 text-right tabular-nums dark:text-slate-300">${parseFloat(w.avg_cost_usd).toFixed(6)}</td>
                  <td className="py-2 text-right tabular-nums dark:text-slate-300">${parseFloat(w.p95_cost_usd).toFixed(6)}</td>
                  <td className="py-2 text-right tabular-nums font-medium dark:text-slate-200">${parseFloat(w.total_cost_usd).toFixed(4)}</td>
                  <td className="py-2 text-right tabular-nums dark:text-slate-300">{w.call_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">No workflow data yet.</p>
        )}
      </Section>

      <Section
        title="Version Compare"
        description="Compare two versions directly when you want to understand whether a rollout changed cost, latency, or token behavior."
      >
        {apiKey ? <ChangeImpactPanel apiKey={apiKey} /> : <Skeleton />}
      </Section>

      <Section
        title="Cost Regressions"
        description="Last 7 days versus prior 7 days. Use this to identify which workflows have materially worsened before you open the deeper economics pages."
      >
        {loadingRegressions ? <Skeleton /> : <RegressionTable items={regressions?.items ?? []} />}
      </Section>

      <Section
        title="Annotations"
        description="Capture release notes, route changes, and pricing shifts so economics changes can be explained later."
      >
        {apiKey && (
          <div className="mb-5">
            <AnnotationForm apiKey={apiKey} onCreated={handleAnnotationCreated} />
          </div>
        )}
        {loadingAnnotations ? (
          <Skeleton />
        ) : annotations.length > 0 ? (
          <ul className="space-y-2">
            {annotations.map((a) => (
              <li
                key={a.id}
                className="flex items-start gap-3 rounded-lg border border-slate-100 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800"
              >
                <div className="min-w-[100px] text-xs text-slate-500 dark:text-slate-400">
                  <span>{a.annotation_date}</span>
                  {a.version ? (
                    <span className="ml-2 rounded bg-indigo-100 px-1.5 py-0.5 font-mono text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                      {a.version}
                    </span>
                  ) : null}
                </div>
                <p className="text-sm text-slate-800 dark:text-slate-200">{a.note}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">No annotations yet.</p>
        )}
      </Section>

      <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-5 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-300">
        <div className="flex gap-3">
          <TrendingDown className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
          <div>
            <p className="font-semibold text-slate-950 dark:text-white">Economics routing note</p>
            <p className="mt-1">
              This page is the overview bridge for the economics workflow. Deep model analysis belongs in Model Usage, realized optimization belongs in Cost &amp; Savings, and finance-period reconciliation belongs in Billing.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
