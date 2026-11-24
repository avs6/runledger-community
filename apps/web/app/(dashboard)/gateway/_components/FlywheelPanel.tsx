'use client'

import { useEffect, useState, useCallback } from 'react'
import { toast } from 'sonner'
import { RefreshCw, TrendingDown } from 'lucide-react'
import { getFlywheelSettings, updateFlywheelSettings, listFlywheelRecommendations, applyFlywheelRecommendation, dismissFlywheelRecommendation, runFlywheel, apiErrorMessage } from '@/lib/api'
import { rollbackFlywheelRecommendation } from '@/lib/api/gateway'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { SectionError } from '@/components/ui/async-card'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import type { FlywheelSettings, FlywheelRecommendation } from '@/types/api'
import { inputCls, pctStr } from './shared'

const KIND_STYLE: Record<string, string> = {
  switch: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  explore: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  guardrail: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
}

const STATUSES = ['pending', 'applied', 'rolled_back', 'dismissed', 'all'] as const

/**
 * Flywheel (G-03): apply, rollback and settings need an org admin (`canApply`); run and
 * dismiss a workspace admin (`canWrite`). Both come from the gateway role matrix.
 */
export function FlywheelPanel({ apiKey, canApply, canWrite }: { apiKey: string; canApply: boolean; canWrite: boolean }) {
  const canManage = canApply
  const [settings, setSettings] = useState<FlywheelSettings | null>(null)
  const [recs, setRecs] = useState<FlywheelRecommendation[]>([])
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const { confirm, dialog } = useConfirm()
  const params = useSearchParams()
  const pathname = usePathname()
  const router = useRouter()
  const statusParam = params.get('fwstatus')
  const statusFilter = (STATUSES as readonly string[]).includes(statusParam ?? '') ? (statusParam as string) : 'pending'
  const setStatusFilter = (value: string) => {
    const next = new URLSearchParams(params.toString())
    if (value === 'pending') next.delete('fwstatus')
    else next.set('fwstatus', value)
    router.replace(`${pathname}?${next.toString()}`, { scroll: false })
  }

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [s, r] = await Promise.all([
        getFlywheelSettings(apiKey),
        listFlywheelRecommendations(apiKey, { status: statusFilter }),
      ])
      setSettings(s)
      setRecs(r.items)
    } catch (err) {
      setError(apiErrorMessage(err, "Couldn't load the flywheel"))
    } finally {
      setLoading(false)
    }
  }, [apiKey, statusFilter])

  useEffect(() => { void load() }, [load])

  async function patch(body: Partial<FlywheelSettings>) {
    if (!canManage) return
    try {
      const s = await updateFlywheelSettings(apiKey, body)
      setSettings(s)
      toast.success('Flywheel settings saved')
    } catch {
      toast.error('Failed to save settings')
    }
  }

  async function handleRun() {
    setRunning(true)
    try {
      const res = await runFlywheel(apiKey)
      toast.success(`Analysis ${res.status} · ${res.recommendations} recommendation(s)`)
      await load()
    } catch {
      toast.error('Flywheel run failed (is the service configured?)')
    } finally {
      setRunning(false)
    }
  }

  async function handleApply(rec: FlywheelRecommendation) {
    const rewrites = rec.segment_by === 'alias'
    if (!(await confirm({
      title: rewrites ? `Apply to the '${rec.segment_key}' route?` : 'Accept this recommendation?',
      description: rewrites
        ? 'The route changes on the next request. Its current config is saved, so you can roll back.'
        : 'Advisory only: no route changes.',
      confirmLabel: rewrites ? 'Apply' : 'Accept',
    }))) return
    setBusyId(rec.id)
    try {
      await applyFlywheelRecommendation(apiKey, rec.id)
      toast.success('Recommendation applied')
      await load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to apply'))
    } finally {
      setBusyId(null)
    }
  }

  async function handleRollback(rec: FlywheelRecommendation) {
    if (!(await confirm({
      title: `Roll back '${rec.segment_key}'?`,
      description: 'The route gets the config it had before this recommendation was applied.',
      confirmLabel: 'Roll back',
      destructive: true,
    }))) return
    setBusyId(rec.id)
    try {
      await rollbackFlywheelRecommendation(apiKey, rec.id)
      toast.success('Route rolled back')
      await load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to roll back'))
    } finally {
      setBusyId(null)
    }
  }

  async function handleDismiss(id: string) {
    setBusyId(id)
    try {
      await dismissFlywheelRecommendation(apiKey, id)
      setRecs((cur) => cur.filter((r) => r.id !== id))
    } catch {
      toast.error('Failed to dismiss')
    } finally {
      setBusyId(null)
    }
  }

  const metricType = (settings?.quality_metric?.type as string) ?? 'blend'

  return (
    <section className="space-y-4">
      {dialog}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold dark:text-white flex items-center gap-2">
            <TrendingDown className="h-4 w-4 text-indigo-500" />
            Optimization Flywheel
            {settings?.enabled ? (
              <span className="rounded-full bg-indigo-100 dark:bg-indigo-900/30 px-2 py-0.5 text-[10px] font-medium text-indigo-700 dark:text-indigo-300">ON</span>
            ) : (
              <span className="rounded-full bg-slate-100 dark:bg-slate-700 px-2 py-0.5 text-[10px] font-medium text-slate-500 dark:text-slate-400">OFF</span>
            )}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Learns the cheapest optimization config per segment that still holds your quality SLA, then recommends (or auto-applies) it.
          </p>
        </div>
        <button
          onClick={handleRun}
          disabled={running || !settings?.enabled || !canWrite}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors"
          title={settings?.enabled ? 'Run the analysis now' : 'Enable the flywheel first'}
        >
          <RefreshCw className={`h-3.5 w-3.5 ${running ? 'animate-spin' : ''}`} />
          {running ? 'Analyzing…' : 'Run now'}
        </button>
      </div>

      {/* Settings */}
      {settings && (
        <div className="grid gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={settings.enabled}
              disabled={!canManage}
              onChange={(e) => patch({ enabled: e.target.checked })}
              className="h-4 w-4 rounded border-slate-300"
            />
            <span className="dark:text-slate-200">Enabled</span>
          </label>

          <label className="text-sm">
            <span className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Apply mode</span>
            <select
              value={settings.apply_mode}
              disabled={!canManage}
              onChange={(e) => patch({ apply_mode: e.target.value })}
              className={inputCls + ' w-full'}
            >
              <option value="approval">Approval-gated</option>
              <option value="auto">Auto-apply (guardrailed)</option>
              <option value="off">Off (analyze only)</option>
            </select>
          </label>

          <label className="text-sm">
            <span className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Segment by</span>
            <select
              value={settings.segment_by}
              disabled={!canManage}
              onChange={(e) => patch({ segment_by: e.target.value })}
              className={inputCls + ' w-full'}
            >
              <option value="outcome_type">Outcome type</option>
              <option value="task_class">Task class (complexity×risk)</option>
              <option value="alias">Alias</option>
            </select>
          </label>

          <label className="text-sm">
            <span className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Quality metric</span>
            <select
              value={metricType}
              disabled={!canManage}
              onChange={(e) => patch({ quality_metric: { ...settings.quality_metric, type: e.target.value } })}
              className={inputCls + ' w-full'}
            >
              <option value="blend">Blend (outcome + eval)</option>
              <option value="outcome_success">Outcome success-rate</option>
              <option value="eval_score">Eval / judge score</option>
            </select>
          </label>

          <label className="text-sm">
            <span className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Min quality (SLA)</span>
            <input
              type="number" step="0.05" min="0" max="1"
              defaultValue={Number(settings.min_quality)}
              disabled={!canManage}
              onBlur={(e) => patch({ min_quality: e.target.value })}
              className={inputCls + ' w-full'}
            />
          </label>

          <label className="text-sm">
            <span className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Min sample size</span>
            <input
              type="number" min="1"
              defaultValue={settings.min_sample_size}
              disabled={!canManage}
              onBlur={(e) => patch({ min_sample_size: Number(e.target.value) })}
              className={inputCls + ' w-full'}
            />
          </label>
        </div>
      )}

      {/* Recommendations */}
      {error && <SectionError message={error} onRetry={() => void load()} />}
      <div className="flex items-center gap-2">
        <label htmlFor="fw-status" className="text-xs text-slate-500">Show</label>
        <select id="fw-status" aria-label="Filter recommendations by status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className={inputCls}>
          {STATUSES.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
      </div>
      {loading ? (
        <div className="py-6 text-center text-sm text-slate-400">Loading…</div>
      ) : recs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400">
          No {statusFilter === 'all' ? '' : statusFilter.replace('_', ' ')} recommendations. {settings?.enabled ? 'Run the analysis once enough traffic has accumulated.' : 'Enable the flywheel to start learning.'}
        </div>
      ) : (
        <div className="space-y-2">
          {recs.map((r) => (
            <div key={r.id} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${KIND_STYLE[r.kind] ?? 'bg-slate-100 text-slate-600'}`}>{r.kind}</span>
                    <span className="font-mono text-sm dark:text-slate-200 truncate">{r.segment_key}</span>
                    <span className="text-[10px] text-slate-400">· {r.confidence} confidence · n={r.sample_size}</span>
                  </div>
                  <p className="mt-1.5 text-xs text-slate-600 dark:text-slate-300">{r.rationale}</p>
                  <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-slate-500 dark:text-slate-400">
                    <span>cost <span className={Number(r.est_cost_delta_pct) < 0 ? 'text-emerald-600 dark:text-emerald-400 font-semibold' : 'text-red-500 dark:text-red-400 font-semibold'}>{pctStr(r.est_cost_delta_pct)}</span></span>
                    <span>quality {r.current_quality != null ? Number(r.current_quality).toFixed(2) : '—'} → {r.proposed_quality != null ? Number(r.proposed_quality).toFixed(2) : '—'} (SLA {Number(r.min_quality).toFixed(2)})</span>
                    <span className="font-mono truncate">{JSON.stringify(r.proposed_config)}</span>
                  </div>
                </div>
                {r.status === 'applied' && canApply && r.applied_route_id && (
                  <button
                    onClick={() => void handleRollback(r)}
                    disabled={busyId === r.id}
                    className="shrink-0 rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-50 disabled:opacity-50 dark:border-rose-900/50 dark:hover:bg-rose-950/30"
                  >
                    Roll back
                  </button>
                )}
                {r.status !== 'pending' && (
                  <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">{r.status.replace('_', ' ')}</span>
                )}
                {r.status === 'pending' && (canApply || canWrite) && (
                  <div className="flex shrink-0 gap-2">
                    {canApply && <button
                      onClick={() => void handleApply(r)}
                      disabled={busyId === r.id}
                      className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {r.segment_by === 'alias' ? 'Apply' : 'Accept'}
                    </button>}
                    <button
                      onClick={() => handleDismiss(r.id)}
                      disabled={busyId === r.id}
                      className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
                    >
                      Dismiss
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-[11px] text-slate-400 dark:text-slate-500">
        Recommendations are observational — cost from your own gateway traffic, quality from outcomes/evals by model.
        Only <span className="font-mono">alias</span>-segmented proposals patch a route directly; others are advisory.
        Applying, rolling back and changing settings need an organization admin and are recorded in the audit log.
      </p>
    </section>
  )
}
