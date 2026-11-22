import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import { FileSpreadsheet, Shield } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getBillingPeriods, getBillingSummary } from '@/lib/api'
import BillingWorkspaceClient from '@/components/billing/BillingWorkspaceClient'
import { num } from '@/lib/utils'

export default async function BillingPage({
  searchParams,
}: {
  searchParams?: Promise<{ tab?: string; months?: string; access_group_id?: string }>
}) {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/login')

  const sp = (await searchParams) ?? {}
  const tab = sp.tab === 'summary'
    ? 'summary'
    : sp.tab === 'shared-costs'
      ? 'shared-costs'
      : 'periods'
  const summaryMonths = [3, 6, 12].includes(Number(sp.months))
    ? Number(sp.months)
    : 6
  const accessGroupId = sp.access_group_id

  const [periods, summary] = await Promise.all([
    getBillingPeriods(session.apiKey, { access_group_id: accessGroupId }).catch(() => ({ items: [] })),
    getBillingSummary(session.apiKey, summaryMonths).catch(() => ({ workspace_id: '', periods: [] }))])


  return (
    <div className="space-y-5">
      {/* ── Hero ── */}
      <section className="rounded-2xl border border-slate-200 bg-white/90 px-6 py-8 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
        <div>
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-950 dark:text-white">Billing</h1>
          </div>
          <p className="mt-1.5 max-w-xl text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
            Operate billing periods, review reconciliation quality, manage shared-cost policies, and export finance-ready evidence in one place.
          </p>
        </div>

        {/* KPI strip */}
        <div className="mt-6 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {[
            { label: 'Periods', value: String(periods.items.length) },
          ].map((kpi) => (
            <div key={kpi.label} className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">{kpi.label}</p>
              <p className="mt-0.5 truncate text-sm font-bold text-slate-900 dark:text-white">{kpi.value}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Context panels ── */}



      {/* Billing client */}
      <BillingWorkspaceClient
        apiKey={session.apiKey}
        initialPeriods={periods.items}
        summary={summary}
        initialTab={tab}
        initialMonths={summaryMonths}
        accessGroupId={accessGroupId}
      />

      {/* ── Quick-nav footer ── */}
      <div className="flex flex-wrap gap-2 pt-2">
        {[
          { label: 'Cost & Savings', href: '/cost-savings' },
          { label: 'Budgets', href: '/budgets' },
          { label: 'Chargeback', href: '/chargeback' },
          { label: 'Access Groups', href: '/access-groups' },
          { label: 'API Keys', href: '/api-keys' },
          { label: 'Gateway', href: '/gateway' },
          { label: 'Alert Rules', href: '/alert-rules' },
          { label: 'Audit Log', href: '/audit' },
          { label: 'Telemetry', href: '/monitoring/telemetry' },
        ].map(({ label, href }) => (
          <Link
            key={label}
            href={href}
            className="rounded-full border border-emerald-200 bg-emerald-50/80 px-3 py-1 text-[11px] font-semibold text-emerald-700 transition hover:bg-emerald-100 dark:border-emerald-800/50 dark:bg-emerald-950/30 dark:text-emerald-300 dark:hover:bg-emerald-900/40"
          >
            {label}
          </Link>
        ))}
      </div>
    </div>
  )
}
