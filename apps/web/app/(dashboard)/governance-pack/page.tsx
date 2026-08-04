'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  FileCheck,
  Download,
  Loader2,
  Activity,
  DollarSign,
  Cpu,
  Users,
  Shield,
  CheckCircle2,
  Bell,
} from 'lucide-react'
import { getGovernanceAuditPack, exportGovernanceAuditPack } from '@/lib/api'
import type { GovernanceAuditPack } from '@/types/api'

const STATUS_BADGE: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  approved: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  denied: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  cancelled: 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400',
}

const ACTION_BADGE: Record<string, string> = {
  block: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  allow: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  audit: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
}

const inputCls =
  'rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'

export default function GovernancePackPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''

  const [fromDate, setFromDate] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() - 30)
    return d.toISOString().slice(0, 10)
  })
  const [toDate, setToDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [pack, setPack] = useState<GovernanceAuditPack | null>(null)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)

  async function handleGenerate() {
    if (!apiKey) return
    setLoading(true)
    setPack(null)
    try {
      const result = await getGovernanceAuditPack(apiKey, { from: fromDate, to: toDate })
      setPack(result)
    } catch {
      toast.error('Failed to generate audit pack')
    } finally {
      setLoading(false)
    }
  }

  async function handleExport(format: 'json' | 'csv') {
    if (!apiKey) return
    setExporting(true)
    try {
      const raw = await exportGovernanceAuditPack(apiKey, { from: fromDate, to: toDate, format })
      const mimeType = format === 'csv' ? 'text/csv' : 'application/json'
      const blob = new Blob([raw], { type: mimeType })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `governance-audit-pack-${fromDate}-to-${toDate}.${format}`
      a.click()
      URL.revokeObjectURL(url)
      toast.success(`Exported as ${format.toUpperCase()}`)
    } catch {
      toast.error(`Export failed`)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100 dark:bg-violet-900/40">
          <FileCheck className="h-5 w-5 text-violet-600 dark:text-violet-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">AI Governance Audit Pack</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Exportable governance evidence bundle for compliance and audit
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">From</label>
            <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className={inputCls} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">To</label>
            <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className={inputCls} />
          </div>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileCheck className="h-4 w-4" />}
            Generate Report
          </button>
          <div className="flex gap-2">
            <button
              onClick={() => handleExport('json')}
              disabled={exporting}
              className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <Download className="h-4 w-4" /> JSON
            </button>
            <button
              onClick={() => handleExport('csv')}
              disabled={exporting}
              className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <Download className="h-4 w-4" /> CSV
            </button>
          </div>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12 text-slate-400">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Generating audit pack…
        </div>
      )}

      {pack && (
        <div className="space-y-6">
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
            {[
              { label: 'Total Requests', value: pack.summary.total_requests.toLocaleString(), icon: Activity },
              { label: 'Total Cost', value: `$${Number(pack.summary.total_cost_usd).toFixed(2)}`, icon: DollarSign },
              { label: 'Models Used', value: String(pack.summary.models_used), icon: Cpu },
              { label: 'Active Users', value: String(pack.summary.users_active), icon: Users },
              { label: 'Policies Enforced', value: String(pack.summary.policies_enforced), icon: Shield },
              { label: 'Approvals', value: String(pack.summary.approvals_processed), icon: CheckCircle2 },
              { label: 'Alerts Fired', value: String(pack.summary.alerts_fired), icon: Bell },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <Icon className="mb-1 h-4 w-4 text-slate-400" />
                <p className="text-lg font-bold text-slate-900 dark:text-white">{value}</p>
                <p className="text-xs text-slate-500">{label}</p>
              </div>
            ))}
          </div>

          {/* Model Usage */}
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Model Usage</p>
            {pack.model_usage.length === 0 ? (
              <p className="text-sm text-slate-400">No model usage data.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      <th className="pb-2 font-medium text-slate-500">Model</th>
                      <th className="pb-2 font-medium text-slate-500">Provider</th>
                      <th className="pb-2 text-right font-medium text-slate-500">Requests</th>
                      <th className="pb-2 text-right font-medium text-slate-500">Cost (USD)</th>
                      <th className="pb-2 font-medium text-slate-500">First Used</th>
                      <th className="pb-2 font-medium text-slate-500">Last Used</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pack.model_usage.map((m, i) => (
                      <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-3 font-medium">{m.model}</td>
                        <td className="py-3 text-slate-500">{m.provider ?? '—'}</td>
                        <td className="py-3 text-right">{m.request_count.toLocaleString()}</td>
                        <td className="py-3 text-right font-mono">${Number(m.cost_usd).toFixed(2)}</td>
                        <td className="py-3 text-xs text-slate-500">{new Date(m.first_used).toLocaleDateString()}</td>
                        <td className="py-3 text-xs text-slate-500">{new Date(m.last_used).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Policy Enforcements */}
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Policy Enforcements</p>
            {pack.policy_enforcements.length === 0 ? (
              <p className="text-sm text-slate-400">No policy enforcement data.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      <th className="pb-2 font-medium text-slate-500">Policy Type</th>
                      <th className="pb-2 font-medium text-slate-500">Action</th>
                      <th className="pb-2 text-right font-medium text-slate-500">Count</th>
                      <th className="pb-2 font-medium text-slate-500">Last Triggered</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pack.policy_enforcements.map((p, i) => (
                      <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-3">{p.policy_type}</td>
                        <td className="py-3">
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ACTION_BADGE[p.action] ?? 'bg-slate-100 text-slate-600'}`}>
                            {p.action}
                          </span>
                        </td>
                        <td className="py-3 text-right">{p.count}</td>
                        <td className="py-3 text-xs text-slate-500">{new Date(p.last_triggered).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Approvals */}
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Approvals</p>
            {pack.approvals.length === 0 ? (
              <p className="text-sm text-slate-400">No approval records.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      <th className="pb-2 font-medium text-slate-500">Request Type</th>
                      <th className="pb-2 font-medium text-slate-500">Status</th>
                      <th className="pb-2 font-medium text-slate-500">Requested By</th>
                      <th className="pb-2 font-medium text-slate-500">Decided By</th>
                      <th className="pb-2 font-medium text-slate-500">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pack.approvals.map((a, i) => (
                      <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-3">{a.request_type}</td>
                        <td className="py-3">
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[a.status] ?? STATUS_BADGE.cancelled}`}>
                            {a.status}
                          </span>
                        </td>
                        <td className="py-3 font-mono text-xs text-slate-500">{a.requested_by ?? '—'}</td>
                        <td className="py-3 font-mono text-xs text-slate-500">{a.decided_by ?? '—'}</td>
                        <td className="py-3 text-xs text-slate-500">{new Date(a.created_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Data Capture Policies */}
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Data Capture Policies</p>
            {pack.data_capture_policies.length === 0 ? (
              <p className="text-sm text-slate-400">No data capture policies.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      <th className="pb-2 font-medium text-slate-500">Scope</th>
                      <th className="pb-2 font-medium text-slate-500">Privacy Mode</th>
                      <th className="pb-2 text-right font-medium text-slate-500">Retention (days)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pack.data_capture_policies.map((p, i) => (
                      <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-3">{p.scope}</td>
                        <td className="py-3">
                          <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                            {p.privacy_mode}
                          </span>
                        </td>
                        <td className="py-3 text-right">{p.retention_days ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Budget Alerts */}
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Budget Alerts</p>
            {pack.budget_alerts.length === 0 ? (
              <p className="text-sm text-slate-400">No budget alerts fired.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      <th className="pb-2 font-medium text-slate-500">Budget</th>
                      <th className="pb-2 text-right font-medium text-slate-500">Threshold</th>
                      <th className="pb-2 font-medium text-slate-500">Triggered At</th>
                      <th className="pb-2 text-right font-medium text-slate-500">Current Spend</th>
                      <th className="pb-2 text-right font-medium text-slate-500">Limit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pack.budget_alerts.map((b, i) => {
                      const overBudget = Number(b.current_spend_usd) > Number(b.limit_usd)
                      return (
                        <tr key={i} className={`border-b border-slate-100 dark:border-slate-800 ${overBudget ? 'bg-red-50/50 dark:bg-red-950/20' : ''}`}>
                          <td className="py-3">{b.budget_name}</td>
                          <td className="py-3 text-right">{b.threshold_pct}%</td>
                          <td className="py-3 text-xs text-slate-500">{new Date(b.triggered_at).toLocaleString()}</td>
                          <td className={`py-3 text-right font-mono ${overBudget ? 'text-red-600 dark:text-red-400' : ''}`}>
                            ${Number(b.current_spend_usd).toFixed(2)}
                          </td>
                          <td className="py-3 text-right font-mono">${Number(b.limit_usd).toFixed(2)}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Compliance Summary */}
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-6 shadow-sm dark:border-emerald-800 dark:bg-emerald-950/30">
            <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-emerald-700 dark:text-emerald-400">
              Compliance Summary
            </p>
            <p className="mb-3 text-sm text-emerald-800 dark:text-emerald-300">
              This report covers <strong>{pack.period_from}</strong> to <strong>{pack.period_to}</strong>.
              Generated at {new Date(pack.generated_at).toLocaleString()}.
            </p>
            <ul className="space-y-1.5">
              {[
                'Model usage tracked',
                'Policy enforcement logged',
                'Approvals audited',
                'Data capture policies documented',
                'Budget alerts monitored',
              ].map((item) => (
                <li key={item} className="flex items-center gap-2 text-sm text-emerald-700 dark:text-emerald-300">
                  <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-emerald-500" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
