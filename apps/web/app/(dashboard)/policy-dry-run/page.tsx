'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Shield, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { policyDryRun } from '@/lib/api'
import type { PolicyCheckResponse } from '@/types/api'

const inputCls =
  'w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

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
  if (v === null || v === undefined) return '—'
  if (typeof v === 'boolean') return v ? 'Yes' : 'No'
  if (Array.isArray(v)) return v.length ? v.join(', ') : '—'
  return String(v)
}

export default function PolicyDryRunPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''

  const [form, setForm] = useState<Record<FormKeys, string>>({
    end_user_id: '',
    feature_tag: '',
    tool_name: '',
    model_alias: '',
  })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<PolicyCheckResponse | null>(null)

  function updateField(key: FormKeys, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  async function handleRun(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) {
      toast.error('No API key found in session')
      return
    }
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

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 dark:bg-indigo-900/40">
          <Shield className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Policy Dry Run</h1>
          <p className="text-sm text-slate-500">Test policy checks without recording violations</p>
        </div>
      </div>

      <form onSubmit={handleRun} className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Check Parameters</p>
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
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center gap-3">
              {result.allowed ? (
                <CheckCircle2 className="h-10 w-10 text-emerald-500" />
              ) : (
                <XCircle className="h-10 w-10 text-red-500" />
              )}
              <div>
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
            </div>

            {result.reasons.length > 0 && (
              <div className="mt-4">
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Reasons</p>
                <div className="flex flex-wrap gap-2">
                  {result.reasons.map((r, i) => (
                    <span
                      key={i}
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
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Detail Breakdown</p>
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
        </div>
      )}
    </div>
  )
}
