'use client'

import { useCallback, useEffect, useState } from 'react'
import { submitScore, listScores, getScoreSummary } from '@/lib/api'
import type { ScoreEvent, ScoreSummaryItem } from '@/types/api'
import { Star } from 'lucide-react'
import { toast } from 'sonner'

function SkeletonRows({ cols, rows = 3 }: { cols: number; rows?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i}>
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} className="px-4 py-3">
              <div className="h-4 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

function ChangeBadge({ changePct }: { changePct: string | null }) {
  if (changePct === null) return <span className="text-slate-400 text-xs">-</span>
  const val = parseFloat(changePct)
  const positive = val >= 0
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${
        positive
          ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
          : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
      }`}
    >
      {positive ? '↑' : '↓'} {Math.abs(val).toFixed(1)}%
    </span>
  )
}

const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500'

const labelCls = 'block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1'

export default function QualityScoresTab({ apiKey }: { apiKey: string }) {
  const [scores, setScores] = useState<ScoreEvent[]>([])
  const [summary, setSummary] = useState<ScoreSummaryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [summaryLoading, setSummaryLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  const [runId, setRunId] = useState('')
  const [scoreName, setScoreName] = useState('')
  const [scoreValue, setScoreValue] = useState('')
  const [label, setLabel] = useState('')
  const [source, setSource] = useState('human')
  const [confidence, setConfidence] = useState('')

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    setSummaryLoading(true)
    try {
      const [scoreRes, summaryRes] = await Promise.all([
        listScores(apiKey, { limit: 50 }),
        getScoreSummary(apiKey),
      ])
      setScores(scoreRes.items)
      setSummary(summaryRes.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load quality scores')
    } finally {
      setLoading(false)
      setSummaryLoading(false)
    }
  }, [apiKey])

  useEffect(() => { void load() }, [load])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    const val = parseFloat(scoreValue)
    if (Number.isNaN(val) || val < 0 || val > 100) {
      toast.error('Value must be between 0 and 100')
      return
    }

    setSubmitting(true)
    try {
      await submitScore(apiKey, {
        name: scoreName,
        value: val,
        run_id: runId.trim() || null,
        label: label || null,
        source,
        confidence: confidence ? parseFloat(confidence) : null,
      })
      toast.success('Score submitted')
      setRunId('')
      setScoreName('')
      setScoreValue('')
      setLabel('')
      setConfidence('')
      await load()
    } catch (err) {
      console.error(err)
      toast.error(err instanceof Error ? err.message : 'Failed to submit score')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Submit quality score</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Attach human, heuristic, or LLM-judge signals to runs so the evaluation suite can track quality over time.
            </p>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className={labelCls}>Run ID</label>
              <input value={runId} onChange={(e) => setRunId(e.target.value)} placeholder="Optional run UUID" className={inputCls} />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className={labelCls}>Score name *</label>
                <input value={scoreName} onChange={(e) => setScoreName(e.target.value)} required placeholder="relevance, accuracy, helpfulness" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Value (0-100) *</label>
                <input value={scoreValue} onChange={(e) => setScoreValue(e.target.value)} type="number" min={0} max={100} step="0.01" required placeholder="92.5" className={inputCls} />
              </div>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label className={labelCls}>Label</label>
                <select value={label} onChange={(e) => setLabel(e.target.value)} className={inputCls}>
                  <option value="">-</option>
                  <option value="good">good</option>
                  <option value="neutral">neutral</option>
                  <option value="bad">bad</option>
                  <option value="pass">pass</option>
                  <option value="fail">fail</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Source</label>
                <select value={source} onChange={(e) => setSource(e.target.value)} className={inputCls}>
                  <option value="human">human</option>
                  <option value="llm">llm</option>
                  <option value="rule">rule</option>
                  <option value="telemetry">telemetry</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Confidence</label>
                <input value={confidence} onChange={(e) => setConfidence(e.target.value)} type="number" min={0} max={1} step="0.01" placeholder="Optional 0-1" className={inputCls} />
              </div>
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : 'Submit score'}
            </button>
          </form>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Score summary</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Average score values and recent movement across your workspace.
            </p>
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Metric</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Average</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {summaryLoading ? <SkeletonRows cols={3} /> : summary.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-4 py-10 text-center text-sm text-slate-500 dark:text-slate-400">
                      No score summary yet.
                    </td>
                  </tr>
                ) : summary.map((item) => (
                  <tr key={item.name}>
                    <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200">{item.name}</td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{Number(item.avg_value).toFixed(2)}</td>
                    <td className="px-4 py-3"><ChangeBadge changePct={item.change_pct} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Recent scores</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Latest score events from human review, rules, and evaluation jobs.
          </p>
        </div>
        <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Value</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Label</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Source</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Run</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? <SkeletonRows cols={5} rows={5} /> : scores.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-12 text-center">
                    <Star className="mx-auto mb-2 h-8 w-8 text-slate-300 dark:text-slate-600" />
                    <p className="text-sm text-slate-500 dark:text-slate-400">No scores submitted yet.</p>
                  </td>
                </tr>
              ) : scores.map((score) => (
                <tr key={score.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200">{score.name}</td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{Number(score.value).toFixed(2)}</td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{score.label ?? '-'}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-600 dark:text-slate-300">
                      {score.source}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500 dark:text-slate-400">{score.run_id ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
