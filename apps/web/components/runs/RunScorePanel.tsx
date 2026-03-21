'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { Star, CheckCircle } from 'lucide-react'
import { toast } from 'sonner'
import { submitScore } from '@/lib/api'

interface Props {
  runId: string
}

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

export default function RunScorePanel({ runId }: Props) {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''

  const [scoreName, setScoreName] = useState('quality')
  const [scoreValue, setScoreValue] = useState<string>('1.0')
  const [scoreLabel, setScoreLabel] = useState('')
  const [scoreConfidence, setScoreConfidence] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    const val = parseFloat(scoreValue)
    if (isNaN(val)) { toast.error('Score value must be a number'); return }
    setSubmitting(true)
    try {
      await submitScore(apiKey, {
        name: scoreName.trim(),
        value: val,
        run_id: runId,
        label: scoreLabel.trim() || null,
        source: 'human',
        confidence: scoreConfidence ? parseFloat(scoreConfidence) : null,
      })
      setSubmitted(true)
      toast.success('Score submitted')
    } catch {
      toast.error('Failed to submit score')
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-800/50 dark:bg-emerald-950/30">
        <CheckCircle className="h-4 w-4 text-emerald-500" />
        <span className="text-sm text-emerald-700 dark:text-emerald-300">Score recorded.</span>
        <button
          onClick={() => { setSubmitted(false); setScoreValue('1.0'); setScoreLabel(''); setScoreConfidence('') }}
          className="ml-auto text-xs text-emerald-600 hover:underline dark:text-emerald-400"
        >
          Add another
        </button>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200/80 bg-white p-4 dark:border-slate-700/60 dark:bg-slate-900">
      <div className="mb-3 flex items-center gap-2 border-b border-slate-200/80 pb-2 dark:border-slate-700/60">
        <Star className="h-4 w-4 text-amber-400" />
        <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Evaluate this Run</h2>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
        <div>
          <label className="mb-1 block text-xs text-gray-500 dark:text-gray-400">Score name</label>
          <select value={scoreName} onChange={(e) => setScoreName(e.target.value)} className={inputCls}>
            <option value="quality">quality</option>
            <option value="accuracy">accuracy</option>
            <option value="helpfulness">helpfulness</option>
            <option value="safety">safety</option>
            <option value="coherence">coherence</option>
            <option value="custom">custom…</option>
          </select>
        </div>
        {scoreName === 'custom' && (
          <div>
            <label className="mb-1 block text-xs text-gray-500 dark:text-gray-400">Custom name</label>
            <input
              type="text"
              placeholder="my_score"
              className={inputCls}
              onChange={(e) => setScoreName(e.target.value === 'custom' ? 'custom' : e.target.value)}
            />
          </div>
        )}
        <div>
          <label className="mb-1 block text-xs text-gray-500 dark:text-gray-400">Value (0–1)</label>
          <input
            type="number"
            step="0.01"
            min="0"
            max="1"
            value={scoreValue}
            onChange={(e) => setScoreValue(e.target.value)}
            className={`w-24 ${inputCls}`}
            required
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-500 dark:text-gray-400">Label (optional)</label>
          <input
            type="text"
            placeholder="e.g. thumbs_up"
            value={scoreLabel}
            onChange={(e) => setScoreLabel(e.target.value)}
            className={inputCls}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-500 dark:text-gray-400">Confidence</label>
          <input
            type="number"
            step="0.1"
            min="0"
            max="1"
            placeholder="1.0"
            value={scoreConfidence}
            onChange={(e) => setScoreConfidence(e.target.value)}
            className={`w-24 ${inputCls}`}
          />
        </div>
        <button
          type="submit"
          disabled={submitting || !apiKey}
          className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {submitting ? 'Submitting…' : 'Submit Score'}
        </button>
      </form>
    </div>
  )
}
