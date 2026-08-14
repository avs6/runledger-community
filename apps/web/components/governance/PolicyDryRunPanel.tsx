'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import {
  Shield,
  CheckCircle2,
  XCircle,
  Loader2,
  FileText,
  ArrowUpCircle,
  ExternalLink,
} from 'lucide-react'
import { policyDryRun, getPolicyDryRunReport, promotePolicy } from '@/lib/api'
import type { PolicyCheckResponse, PolicyDryRunReport } from '@/types/api'

const inputCls =
  'w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

const cardCls =
  'rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900'

const sectionLabel =
  'text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500'

const fields = [
  { key: 'end_user_id', label: 'End User ID', placeholder: 'e.g. user_abc123' },
  { key: 'feature_tag', label: 'Feature Tag', placeholder: 'e.g. chat, summarize' },
  { key: 'tool_name', label: 'Tool Name', placeholder: 'e.g. web_search' },
  { key: 'model_alias', label: 'Model Alias', placeholder: 'e.g. gpt-4o' },
] as const

type FormKeys = (typeof fields)[number]['key']

const detailLabels: { key: string; label: string; good: (v: unknown) => boolean }[] = [
  { key: 'budget_remaining_usd', label: 'Budget Remaining (USD)', good: (v) => Number(v) > 0 },
  { key: 'budget_limit_usd', label: 'Budget Limit (USD)', good: () => true },
  { key: 'budget_period', label: 'Budget Period', good: () => true },
  { key: 'tool_registered', label: 'Tool Registered', good: (v) => v === true },
  { key: 'tool_policy_setting', label: 'Tool Policy', good: (v) => v === 'allow' || v === 'audit' },
  { key: 'gateway_routes_found', label: 'Gateway Routes Found', good: (v) => Number(v) > 0 },
  { key: 'gateway_route_aliases', label: 'Gateway Route Aliases', good: (v) => Array.isArray(v) && v.length > 0 },
  { key: 'score_latest_value', label: 'Score Latest Value', good: () => true },
  { key: 'score_gate_threshold', label: 'Score Gate Threshold', good: () => true },
]

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return '-'
  if (typeof v === 'boolean') return v ? 'Yes' : 'No'
  if (Array.isArray(v)) return v.length ? v.join(', ') : '-'
  return String(v)
}

const actionBadge: Record<string, string> = {
  block: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  allow: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  reroute: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
}

type Tab = 'single' | 'report'

export default function PolicyDryRunPanel({ apiKey }: { apiKey: string }) {
  const [tab, setTab] = useState<Tab>('single')
  const [form, setForm] = useState<Record<FormKeys, string>>({
    end_user_id: '',
    feature_tag: '',
    tool_name: '',
    model_alias: '',
  })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<PolicyCheckResponse | null>(null)
  const [promoting, setPromoting] = useState(false)
  const [report, setReport] = useState<PolicyDryRunReport | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportPromoting, setReportPromoting] = useState(false)

  function updateField(key: FormKeys, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  async function handleRun(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setLoading(true)
    setResult(null)
    try {
      const body: Record<string, unknown> = { dry_run: true as const }
      for (const f of fields) {
        if (form[f.key].trim()) body[f.key] = form[f.key].trim()
      }
      const res = await policyDryRun(apiKey, body as Parameters<typeof policyDryRun>[1])
      setResult(res)
    } catch {
      toast.error('Policy check failed')
    } finally {
      setLoading(false)
    }
  }

  async function handlePromote(policyType: string) {
    setPromoting(true)
    try {
      const res = await promotePolicy(apiKey, { policy_type: policyType, enforce: true })
      toast.success(res.message || 'Policy promoted to enforcement')
    } catch {
      toast.error('Failed to promote policy')
    } finally {
      setPromoting(false)
    }
  }

  async function loadReport() {
    setReportLoading(true)
    try {
      const data = await getPolicyDryRunReport(apiKey, { limit: 100 })
      setReport(data)
    } catch {
      toast.error('Failed to load dry-run report')
    } finally {
      setReportLoading(false)
    }
  }

  async function handleReportPromote(policyType: string) {
    setReportPromoting(true)
    try {
      const res = await promotePolicy(apiKey, { policy_type: policyType, enforce: true })
      toast.success(res.message || 'Policy promoted to enforcement')
    } catch {
      toast.error('Failed to promote policy')
    } finally {
      setReportPromoting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 dark:bg-indigo-900/40">
            <Shield className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Policy Dry Run</h2>
            <p className="text-sm text-slate-500">
              Test policy checks without turning them into active enforcement yet.
            </p>
          </div>
        </div>
      </div>

      <div className="flex gap-1 rounded-lg bg-slate-100 p-1 dark:bg-slate-800">
        {([
          { id: 'single' as Tab, label: 'Single Check', icon: Shield },
          { id: 'report' as Tab, label: 'Dry-Run Report', icon: FileText },
        ]).map((t) => (
          <button
            key={t.id}
            onClick={() => {
              setTab(t.id)
              if (t.id === 'report' && !report) void loadReport()
            }}
            className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition ${
              tab === t.id
                ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'single' && (
        <>
          <form onSubmit={handleRun} className={cardCls}>
            <p className={`mb-4 ${sectionLabel}`}>Check Parameters</p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {fields.map((f) => (
                <label key={f.key} className="block">
                  <span className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">{f.label}</span>
                  <input
                    type="text"
                    className={inputCls}
                    placeholder={f.placeholder}
                    value={form[f.key]}
                    onChange={(e) => updateField(f.key, e.target.value)}
                  />
                </label>
              ))}
            </div>
            <button
              type="submit"
              disabled={loading}
              className="mt-5 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Shield className="h-4 w-4" />}
              Run Check
            </button>
          </form>

          {result && (
            <div className="space-y-4">
              <div className={cardCls}>
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    {result.allowed ? (
                      <CheckCircle2 className="h-10 w-10 text-emerald-500" />
                    ) : (
                      <XCircle className="h-10 w-10 text-red-500" />
                    )}
                    <span
                      className={`inline-block rounded-full px-3 py-1 text-sm font-semibold ${
                        result.allowed
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                          : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                      }`}
                    >
                      {result.allowed ? 'Allowed' : 'Blocked'}
                    </span>
                  </div>

                  <button
                    onClick={() => {
                      const policyType = form.feature_tag.trim() || form.tool_name.trim() || 'default'
                      void handlePromote(policyType)
                    }}
                    disabled={promoting}
                    className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-amber-700 disabled:opacity-50"
                  >
                    {promoting ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUpCircle className="h-4 w-4" />}
                    Promote to Enforcement
                  </button>
                </div>

                {result.reasons.length > 0 && (
                  <div className="mt-4">
                    <p className={`mb-2 ${sectionLabel}`}>Reasons</p>
                    <div className="flex flex-wrap gap-2">
                      {result.reasons.map((r, i) => (
                        <span
                          key={`${r}-${i}`}
                          className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                        >
                          {r}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {result.detail && (
                <div className={cardCls}>
                  <p className={`mb-4 ${sectionLabel}`}>Detail Breakdown</p>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {detailLabels.map(({ key, label, good }) => {
                      const raw = (result.detail as unknown as Record<string, unknown>)?.[key]
                      const display = formatValue(raw)
                      const isNull = raw === null || raw === undefined
                      const colorCls = isNull
                        ? 'text-slate-400'
                        : good(raw)
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-red-600 dark:text-red-400'
                      return (
                        <div key={key} className="flex items-baseline justify-between rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
                          <span className="text-xs text-slate-500">{label}</span>
                          <span className={`text-sm font-medium ${colorCls}`}>{display}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              <div className={cardCls}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className={sectionLabel}>Audit Trail</p>
                    <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                      View all dry-run policy decisions in the audit log.
                    </p>
                  </div>
                  <a
                    href="/audit?action=policy.dry_run"
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    <ExternalLink className="h-4 w-4" />
                    View Audit Log
                  </a>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {tab === 'report' && (
        <div className={`${cardCls} space-y-4`}>
          <div className="flex items-center justify-between">
            <div>
              <p className={sectionLabel}>Dry-Run Report</p>
              <p className="mt-1 text-sm text-slate-500">Recent shadow-evaluation decisions across the policy engine.</p>
            </div>
            <button
              onClick={() => void loadReport()}
              disabled={reportLoading}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              {reportLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
              Refresh report
            </button>
          </div>

          {!report ? (
            <p className="text-sm text-slate-500">Load the report to inspect dry-run outcomes.</p>
          ) : (
            <>
              <div className="grid gap-4 md:grid-cols-4">
                <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                  <p className={sectionLabel}>Checked</p>
                  <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{report.total_checked}</p>
                </div>
                <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                  <p className={sectionLabel}>Would Block</p>
                  <p className="mt-2 text-2xl font-semibold text-red-600">{report.would_block}</p>
                </div>
                <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                  <p className={sectionLabel}>Would Allow</p>
                  <p className="mt-2 text-2xl font-semibold text-emerald-600">{report.would_allow}</p>
                </div>
                <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                  <p className={sectionLabel}>Would Reroute</p>
                  <p className="mt-2 text-2xl font-semibold text-amber-600">{report.would_reroute}</p>
                </div>
              </div>

              <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 dark:bg-slate-800/60">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Request</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Action</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Model</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Reason</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Promote</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {report.items.map((item) => (
                      <tr key={item.request_id}>
                        <td className="px-4 py-3 font-mono text-xs text-slate-500">{item.request_id}</td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${actionBadge[item.action] ?? 'bg-slate-100 text-slate-600'}`}>
                            {item.action}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{item.model ?? '-'}</td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{item.reasons.join(', ') || '-'}</td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => void handleReportPromote(item.action)}
                            disabled={reportPromoting}
                            className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700 disabled:opacity-50"
                          >
                            Promote
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
