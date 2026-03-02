'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { submitScore, listScores, getScoreSummary } from '@/lib/api'
import type { ScoreEvent, ScoreSummaryItem } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Star } from 'lucide-react'
import { toast } from 'sonner'

function SkeletonRows({ cols, rows = 3 }: { cols: number; rows?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i}>
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} className="pb-2 pr-3">
              <div className="h-4 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

function ChangeBadge({ changePct }: { changePct: string | null }) {
  if (changePct === null) return <span className="text-gray-400 text-xs">—</span>
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

export default function EvaluationsPage() {
  const { data: session } = useSession()
  const [scores, setScores] = useState<ScoreEvent[]>([])
  const [summary, setSummary] = useState<ScoreSummaryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [summaryLoading, setSummaryLoading] = useState(true)

  // Form state
  const [runId, setRunId] = useState('')
  const [scoreName, setScoreName] = useState('')
  const [scoreValue, setScoreValue] = useState('')
  const [label, setLabel] = useState('')
  const [source, setSource] = useState('human')
  const [confidence, setConfidence] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function loadScores(key: string) {
    listScores(key, { limit: 50 })
      .then((res) => {
        setScores(res.items)
        setLoading(false)
      })
      .catch((err) => {
        console.error(err)
        setLoading(false)
      })
  }

  function loadSummary(key: string) {
    getScoreSummary(key)
      .then((res) => {
        setSummary(res.items)
        setSummaryLoading(false)
      })
      .catch((err) => {
        console.error(err)
        setSummaryLoading(false)
      })
  }

  useEffect(() => {
    const key = (session as { apiKey?: string } | null)?.apiKey
    if (!key) return
    loadScores(key)
    loadSummary(key)
  }, [session])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const key = (session as { apiKey?: string } | null)?.apiKey
    if (!key) return

    const val = parseFloat(scoreValue)
    if (isNaN(val) || val < 0 || val > 100) {
      toast.error('Value must be between 0 and 100')
      return
    }

    setSubmitting(true)
    try {
      await submitScore(key, {
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
      loadScores(key)
      loadSummary(key)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to submit score')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Evaluations</h1>

      {/* Two-column layout: form + summary */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left — Submit Score form */}
        <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700">
          <CardHeader>
            <CardTitle className="text-base text-gray-900 dark:text-white">Submit Score</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Run ID <span className="text-gray-400">(optional)</span>
                </label>
                <input
                  type="text"
                  value={runId}
                  onChange={(e) => setRunId(e.target.value)}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Score Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={scoreName}
                  onChange={(e) => setScoreName(e.target.value)}
                  placeholder="relevance, accuracy, helpfulness…"
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Value (0–100) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  required
                  min={0}
                  max={100}
                  step="0.01"
                  value={scoreValue}
                  onChange={(e) => setScoreValue(e.target.value)}
                  placeholder="0.9"
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Label
                  </label>
                  <select
                    value={label}
                    onChange={(e) => setLabel(e.target.value)}
                    className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">—</option>
                    <option value="good">good</option>
                    <option value="neutral">neutral</option>
                    <option value="bad">bad</option>
                    <option value="pass">pass</option>
                    <option value="fail">fail</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Source
                  </label>
                  <select
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="human">human</option>
                    <option value="llm">llm</option>
                    <option value="rule">rule</option>
                    <option value="telemetry">telemetry</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Confidence (0–1) <span className="text-gray-400">(optional)</span>
                </label>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step="0.01"
                  value={confidence}
                  onChange={(e) => setConfidence(e.target.value)}
                  placeholder="0.95"
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {submitting ? 'Submitting…' : 'Submit Score'}
              </button>
            </form>
          </CardContent>
        </Card>

        {/* Right — Summary cards */}
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
            Score Summary (Last 7 Days)
          </h2>
          {summaryLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-20 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800"
                />
              ))}
            </div>
          ) : summary.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-gray-200 dark:border-gray-700 py-12 text-center">
              <Star className="h-8 w-8 text-gray-300 dark:text-gray-600 mb-2" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No scores yet. Submit your first quality score.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {summary.map((item) => (
                <Card
                  key={item.name}
                  className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700"
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {item.name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          {item.sample_count} sample{item.sample_count !== 1 ? 's' : ''}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xl font-semibold text-gray-900 dark:text-white">
                          {parseFloat(item.avg_value).toFixed(2)}
                        </p>
                        <ChangeBadge changePct={item.change_pct} />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom — Recent Scores table */}
      <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700">
        <CardHeader>
          <CardTitle className="text-base text-gray-900 dark:text-white">Recent Scores</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700 text-left">
                  {['Name', 'Value', 'Label', 'Source', 'Run ID', 'Confidence', 'Created'].map(
                    (h) => (
                      <th
                        key={h}
                        className="pb-2 pr-4 font-medium text-gray-500 dark:text-gray-400"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {loading ? (
                  <SkeletonRows cols={7} rows={3} />
                ) : scores.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center">
                      <div className="flex flex-col items-center gap-2 text-gray-400 dark:text-gray-600">
                        <Star className="h-8 w-8" />
                        <p className="text-sm">
                          No scores yet. Submit your first quality score above.
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  scores.map((score) => (
                    <tr key={score.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                      <td className="py-2 pr-4 font-medium text-gray-900 dark:text-white">
                        {score.name}
                      </td>
                      <td className="py-2 pr-4 text-gray-700 dark:text-gray-300">
                        {parseFloat(score.value).toFixed(4)}
                      </td>
                      <td className="py-2 pr-4 text-gray-500 dark:text-gray-400">
                        {score.label ?? '—'}
                      </td>
                      <td className="py-2 pr-4">
                        <span className="inline-flex items-center rounded bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-xs text-gray-600 dark:text-gray-400">
                          {score.source}
                        </span>
                      </td>
                      <td className="py-2 pr-4 font-mono text-xs text-gray-500 dark:text-gray-400">
                        {score.run_id ? (
                          <a
                            href={`/runs/${score.run_id}`}
                            className="hover:text-indigo-600 dark:hover:text-indigo-400"
                          >
                            {score.run_id.slice(0, 8)}…
                          </a>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="py-2 pr-4 text-gray-500 dark:text-gray-400">
                        {score.confidence ? parseFloat(score.confidence).toFixed(2) : '—'}
                      </td>
                      <td className="py-2 pr-4 text-gray-500 dark:text-gray-400">
                        {new Date(score.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
