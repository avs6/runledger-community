'use client'

import { useEffect, useState, useCallback } from 'react'
import { toast } from 'sonner'
import { RefreshCw, TrendingDown } from 'lucide-react'
import { getFlywheelSettings, updateFlywheelSettings, listFlywheelRecommendations, applyFlywheelRecommendation, dismissFlywheelRecommendation, runFlywheel } from '@/lib/api'
import type { FlywheelSettings, FlywheelRecommendation } from '@/types/api'
import { inputCls, pctStr } from './shared'

const KIND_STYLE: Record<string, string> = {
  switch: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  explore: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  guardrail: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
}

export function FlywheelPanel({ apiKey, canManage }: { apiKey: string; canManage: boolean }) {
  const [settings, setSettings] = useState<FlywheelSettings | null>(null)
  const [recs, setRecs] = useState<FlywheelRecommendation[]>([])
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [s, r] = await Promise.all([
        getFlywheelSettings(apiKey).catch(() => null),
        listFlywheelRecommendations(apiKey, { status: 'pending' }).catch(() => ({ items: [], total: 0 })),
      ])
      if (s) setSettings(s)
      setRecs(r.items)
    } finally {
      setLoading(false)
    }
  }, [apiKey])

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

  async function handleApply(id: string) {
    setBusyId(id)
    try {
      await applyFlywheelRecommendation(apiKey, id)
      toast.success('Recommendation applied')
      setRecs((cur) => cur.filter((r) => r.id !== id))
    } catch {
      toast.error('Failed to apply')
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
          disabled={running || !settings?.enabled}
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
      {loading ? (
        <div className="py-6 text-center text-sm text-slate-400">Loading…</div>
      ) : recs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400">
          No pending recommendations. {settings?.enabled ? 'Run the analysis once enough traffic has accumulated.' : 'Enable the flywheel to start learning.'}
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
                {canManage && (
                  <div className="flex shrink-0 gap-2">
                    <button
                      onClick={() => handleApply(r.id)}
                      disabled={busyId === r.id}
                      className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {r.segment_by === 'alias' ? 'Apply' : 'Accept'}
                    </button>
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
      </p>
    </section>
  )
}
