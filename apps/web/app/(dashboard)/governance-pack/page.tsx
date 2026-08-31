'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
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
  Layers,
  Link2,
} from 'lucide-react'
import { getGovernanceAuditPack, exportGovernanceAuditPack, getEvidenceAuditCrossPosture, getGovernanceInternalPosture, getGovernancePackRuntimePosture } from '@/lib/api'
import type { GovernanceAuditPack, EvidenceAuditCrossPosture, GovernanceInternalPosture, GovernancePackRuntimePosture } from '@/types/api'

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
  const [crossPosture, setCrossPosture] = useState<EvidenceAuditCrossPosture | null>(null)
  const [govInternal, setGovInternal] = useState<GovernanceInternalPosture | null>(null)
  const [runtimePosture, setRuntimePosture] = useState<GovernancePackRuntimePosture | null>(null)

  useEffect(() => {
    if (!apiKey) return
    getEvidenceAuditCrossPosture(apiKey).then(setCrossPosture).catch(() => {})
    getGovernanceInternalPosture(apiKey).then(setGovInternal).catch(() => {})
    getGovernancePackRuntimePosture(apiKey).then(setRuntimePosture).catch(() => {})
  }, [apiKey])

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

      {/* Cross-Feature Evidence Posture */}
      {crossPosture && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-5 dark:border-amber-800 dark:bg-amber-950/30">
          <div className="mb-3 flex items-center gap-2">
            <Layers className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            <h2 className="text-sm font-semibold text-amber-900 dark:text-amber-200">Cross-Feature Evidence Posture</h2>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{crossPosture.finops_context.active_budgets}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Budgets</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{crossPosture.finops_context.chargeback_rules}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Chargeback Rules</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{crossPosture.gateway_context.total_providers}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Gateway Providers</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{crossPosture.observe_context.total_runs_30d}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Agent Runs 30d</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Link href="/budgets" className="text-amber-700 hover:text-amber-900 dark:text-amber-400 dark:hover:text-amber-300">Budgets →</Link>
            <Link href="/chargeback" className="text-amber-700 hover:text-amber-900 dark:text-amber-400 dark:hover:text-amber-300">Chargeback →</Link>
            <Link href="/ledger" className="text-amber-700 hover:text-amber-900 dark:text-amber-400 dark:hover:text-amber-300">Ledger →</Link>
            <Link href="/organization" className="text-amber-700 hover:text-amber-900 dark:text-amber-400 dark:hover:text-amber-300">Organization →</Link>
            <Link href="/analytics" className="text-amber-700 hover:text-amber-900 dark:text-amber-400 dark:hover:text-amber-300">Runs →</Link>
            <Link href="/monitoring" className="text-amber-700 hover:text-amber-900 dark:text-amber-400 dark:hover:text-amber-300">Monitoring →</Link>
            <Link href="/gateway" className="text-amber-700 hover:text-amber-900 dark:text-amber-400 dark:hover:text-amber-300">Gateway →</Link>
          </div>
        </div>
      )}

      {govInternal && (
        <div className="rounded-2xl border border-rose-200 dark:border-rose-800 bg-rose-50/60 dark:bg-rose-950/30 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-rose-600 dark:text-rose-400" />
            <h2 className="text-lg font-semibold text-rose-900 dark:text-rose-100">Governance Cohesion</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Registered Tools</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.tool_registry_context.total_tools}</p>
              <p className="text-xs text-slate-500">{govInternal.tool_registry_context.enforced_tools} enforced</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Active Policies</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.tool_policies_context.active_policies}</p>
              <p className="text-xs text-slate-500">{govInternal.tool_policies_context.total_policies} total</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Security Events (30d)</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.security_context.security_events_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Active Tags</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.tags_context.active_tags}</p>
              <p className="text-xs text-slate-500">{govInternal.tags_context.total_tags} total</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/tool-registry" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tool Registry</Link>
            <Link href="/tool-policies" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tool Policies</Link>
            <Link href="/approvals" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Approvals</Link>
            <Link href="/data-capture" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Data Capture</Link>
            <Link href="/security" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Security</Link>
            <Link href="/alert-rules" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Alert Rules</Link>
            <Link href="/audit" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Audit Log</Link>
            <Link href="/tags" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tags</Link>
          </div>
        </div>
      )}

      {runtimePosture && (
        <div className="rounded-2xl border border-cyan-200 bg-cyan-50/60 p-5 dark:border-cyan-800 dark:bg-cyan-950/30">
          <div className="mb-3 flex items-center gap-2">
            <Layers className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
            <h2 className="text-sm font-semibold text-cyan-900 dark:text-cyan-200">Runtime Scope & Evidence</h2>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{runtimePosture.governance_sources.audit_events_30d}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Audit Events 30d</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{runtimePosture.governance_sources.active_tags}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Tags</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{runtimePosture.monitoring_evidence.alert_firings_30d}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Alert Firings 30d</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{runtimePosture.finops_evidence.ledger_snapshots_30d}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Ledger Snapshots 30d</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Link href="/guardrails" className="text-cyan-700 hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300">Guardrails →</Link>
            <Link href="/audit" className="text-cyan-700 hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300">Audit Log →</Link>
            <Link href="/tags" className="text-cyan-700 hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300">Tags →</Link>
            <Link href="/monitoring" className="text-cyan-700 hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300">Monitoring →</Link>
            <Link href="/budgets" className="text-cyan-700 hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300">Budgets →</Link>
            <Link href="/ledger" className="text-cyan-700 hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300">Ledger →</Link>
            <Link href="/organization" className="text-cyan-700 hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300">Organization →</Link>
          </div>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Link href="/approvals" className="rounded-2xl border border-slate-200 bg-white/90 p-4 text-sm text-slate-700 shadow-sm hover:border-violet-300 hover:bg-violet-50/40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
          <p className="font-semibold text-slate-900 dark:text-white">Approvals</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Review pending decisions and auto-approval policies.</p>
        </Link>
        <Link href="/audit" className="rounded-2xl border border-slate-200 bg-white/90 p-4 text-sm text-slate-700 shadow-sm hover:border-violet-300 hover:bg-violet-50/40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
          <p className="font-semibold text-slate-900 dark:text-white">Audit log</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Drill into the raw governance trail behind this evidence pack.</p>
        </Link>
        <Link href="/alert-rules" className="rounded-2xl border border-slate-200 bg-white/90 p-4 text-sm text-slate-700 shadow-sm hover:border-violet-300 hover:bg-violet-50/40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
          <p className="font-semibold text-slate-900 dark:text-white">Alert rules</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Tune governance notifications and threshold-based monitoring.</p>
        </Link>
        <Link href="/data-capture" className="rounded-2xl border border-slate-200 bg-white/90 p-4 text-sm text-slate-700 shadow-sm hover:border-violet-300 hover:bg-violet-50/40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
          <p className="font-semibold text-slate-900 dark:text-white">Data capture</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Adjust privacy mode and scoped capture posture behind this report.</p>
        </Link>
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
