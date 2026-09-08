'use client'

import { useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import {
  Play,
  BarChart3,
  Clock,
  Coins,
  Hash,
  Loader2,
  Plus,
  RotateCcw,
  Settings2,
  SplitSquareHorizontal,
  X,
  ChevronDown,
  Sparkles,
  Zap,
  AlertCircle,
} from 'lucide-react'
import type { PlaygroundRequestResponse, PlaygroundSessionResponse } from '@/types/api'
import { num } from '@/lib/utils'

const POPULAR_MODELS = [
  'gpt-4o',
  'gpt-4o-mini',
  'gpt-4-turbo',
  'gpt-3.5-turbo',
  'claude-sonnet-4-20250514',
  'claude-haiku-4-5-20251001',
  'claude-opus-4-20250514',
  'gemini-1.5-pro',
  'gemini-1.5-flash',
  'mistral-large-latest',
  'mistral-small-latest',
  'llama-3.1-70b-instruct',
  'llama-3.1-8b-instruct',
]

function money(v: number | null | undefined) {
  if (!v) return '$0.00'
  const n = num(v)
  if (n >= 1) return `$${n.toFixed(2)}`
  if (n >= 0.001) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

function statusColor(s: string) {
  const map: Record<string, string> = {
    completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    pending: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  }
  return map[s] || 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
}

type Mode = 'single' | 'compare'

interface ResultCard {
  model: string
  response: PlaygroundRequestResponse | null
  loading: boolean
  error: string | null
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8201'

export default function PlaygroundClient({
  initialSessions,
  initialHistory,
  initialHistoryTotal,
}: {
  initialSessions: PlaygroundSessionResponse[]
  initialHistory: PlaygroundRequestResponse[]
  initialHistoryTotal: number
}) {
  const { data: session } = useSession()
  const apiKey = (session as Record<string, unknown> | null)?.apiKey as string | undefined

  const [mode, setMode] = useState<Mode>('single')
  const [model, setModel] = useState('gpt-4o')
  const [compareModels, setCompareModels] = useState<string[]>(['gpt-4o', 'claude-sonnet-4-20250514'])
  const [userPrompt, setUserPrompt] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [showSystemPrompt, setShowSystemPrompt] = useState(false)
  const [showParams, setShowParams] = useState(false)
  const [temperature, setTemperature] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(1024)

  const [results, setResults] = useState<ResultCard[]>([])
  const [history, setHistory] = useState<PlaygroundRequestResponse[]>(initialHistory)
  const [historyTotal, setHistoryTotal] = useState(initialHistoryTotal)
  const [sending, setSending] = useState(false)

  const addCompareModel = useCallback(() => {
    if (compareModels.length < 5) {
      const available = POPULAR_MODELS.filter((m) => !compareModels.includes(m))
      setCompareModels([...compareModels, available[0] || 'gpt-4o'])
    }
  }, [compareModels])

  const removeCompareModel = useCallback(
    (idx: number) => {
      if (compareModels.length > 2) {
        setCompareModels(compareModels.filter((_, i) => i !== idx))
      }
    },
    [compareModels]
  )

  const updateCompareModel = useCallback(
    (idx: number, value: string) => {
      const next = [...compareModels]
      next[idx] = value
      setCompareModels(next)
    },
    [compareModels]
  )

  async function handleSend() {
    if (!apiKey || !userPrompt.trim()) return
    setSending(true)

    const params: Record<string, unknown> = {}
    if (temperature !== 0.7) params.temperature = temperature
    if (maxTokens !== 1024) params.max_tokens = maxTokens

    try {
      if (mode === 'single') {
        setResults([{ model, response: null, loading: true, error: null }])
        const resp = await fetch(`${API_BASE}/playground/send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
          body: JSON.stringify({
            model,
            user_prompt: userPrompt,
            system_prompt: systemPrompt || undefined,
            parameters: Object.keys(params).length > 0 ? params : undefined,
          }),
        })
        if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
        const data: PlaygroundRequestResponse = await resp.json()
        setResults([{ model, response: data, loading: false, error: null }])
        setHistory((prev) => [data, ...prev])
        setHistoryTotal((prev) => prev + 1)
      } else {
        setResults(
          compareModels.map((m) => ({ model: m, response: null, loading: true, error: null }))
        )
        const resp = await fetch(`${API_BASE}/playground/compare`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
          body: JSON.stringify({
            models: compareModels,
            user_prompt: userPrompt,
            system_prompt: systemPrompt || undefined,
            parameters: Object.keys(params).length > 0 ? params : undefined,
          }),
        })
        if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
        const data: { results: PlaygroundRequestResponse[] } = await resp.json()
        setResults(
          data.results.map((r) => ({ model: r.model, response: r, loading: false, error: null }))
        )
        setHistory((prev) => [...data.results, ...prev])
        setHistoryTotal((prev) => prev + data.results.length)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Request failed'
      setResults((prev) =>
        prev.map((r) => (r.loading ? { ...r, loading: false, error: msg } : r))
      )
    } finally {
      setSending(false)
    }
  }

  function handleReset() {
    setResults([])
    setUserPrompt('')
    setSystemPrompt('')
    setShowSystemPrompt(false)
    setShowParams(false)
    setTemperature(0.7)
    setMaxTokens(1024)
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 md:p-10">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            API Playground
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Send requests through the RunLedger gateway, compare models side-by-side, and track
            costs.
          </p>
        </div>
        {results.length > 0 && (
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 shadow-sm transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            New Request
          </button>
        )}
      </div>

      {/* Mode Toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setMode('single')}
          className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
            mode === 'single'
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
              : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
          }`}
        >
          <Zap className="h-4 w-4" />
          Single Model
        </button>
        <button
          onClick={() => setMode('compare')}
          className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
            mode === 'compare'
              ? 'bg-violet-600 text-white shadow-lg shadow-violet-600/20'
              : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
          }`}
        >
          <SplitSquareHorizontal className="h-4 w-4" />
          Compare Models
        </button>
      </div>

      {/* Input Panel */}
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
        {/* Model Selection */}
        <div className="mb-4">
          {mode === 'single' ? (
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">
                Model
              </label>
              <div className="relative">
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full appearance-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 pr-10 text-sm font-medium text-slate-800 transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:focus:border-blue-500"
                >
                  {POPULAR_MODELS.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              </div>
            </div>
          ) : (
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label className="text-xs font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">
                  Models to Compare ({compareModels.length}/5)
                </label>
                {compareModels.length < 5 && (
                  <button
                    onClick={addCompareModel}
                    className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-blue-600 transition hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-950/40"
                  >
                    <Plus className="h-3 w-3" />
                    Add Model
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                {compareModels.map((m, idx) => (
                  <div key={idx} className="relative flex items-center gap-1">
                    <select
                      value={m}
                      onChange={(e) => updateCompareModel(idx, e.target.value)}
                      className="appearance-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 pr-8 text-sm font-medium text-slate-800 transition focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-500/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
                    >
                      {POPULAR_MODELS.map((pm) => (
                        <option key={pm} value={pm}>
                          {pm}
                        </option>
                      ))}
                    </select>
                    {compareModels.length > 2 && (
                      <button
                        onClick={() => removeCompareModel(idx)}
                        className="rounded-lg p-1 text-slate-400 transition hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-950/40 dark:hover:text-red-400"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* System prompt toggle + Parameters toggle */}
        <div className="mb-3 flex gap-2">
          <button
            onClick={() => setShowSystemPrompt(!showSystemPrompt)}
            className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition ${
              showSystemPrompt
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
            }`}
          >
            <Sparkles className="h-3.5 w-3.5" />
            System Prompt
          </button>
          <button
            onClick={() => setShowParams(!showParams)}
            className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition ${
              showParams
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
            }`}
          >
            <Settings2 className="h-3.5 w-3.5" />
            Parameters
          </button>
        </div>

        {/* System Prompt */}
        {showSystemPrompt && (
          <div className="mb-4">
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="You are a helpful assistant..."
              rows={3}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 placeholder:text-slate-400 transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:placeholder:text-slate-500"
            />
          </div>
        )}

        {/* Parameters */}
        {showParams && (
          <div className="mb-4 flex gap-4">
            <div className="flex-1">
              <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">
                Temperature ({temperature})
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full accent-blue-600"
              />
            </div>
            <div className="w-40">
              <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">
                Max Tokens
              </label>
              <input
                type="number"
                min="1"
                max="128000"
                value={maxTokens}
                onChange={(e) => setMaxTokens(parseInt(e.target.value) || 1024)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
              />
            </div>
          </div>
        )}

        {/* User Prompt */}
        <div className="relative">
          <textarea
            value={userPrompt}
            onChange={(e) => setUserPrompt(e.target.value)}
            placeholder="Enter your prompt..."
            rows={4}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault()
                handleSend()
              }
            }}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 pb-14 text-sm text-slate-800 placeholder:text-slate-400 transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:placeholder:text-slate-500"
          />
          <div className="absolute bottom-3 right-3 flex items-center gap-2">
            <span className="text-[10px] text-slate-400 dark:text-slate-500">
              {navigator.platform?.includes('Mac') ? '⌘' : 'Ctrl'}+Enter
            </span>
            <button
              onClick={handleSend}
              disabled={sending || !userPrompt.trim() || !apiKey}
              className={`flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold text-white shadow-lg transition disabled:opacity-50 disabled:cursor-not-allowed ${
                mode === 'compare'
                  ? 'bg-violet-600 shadow-violet-600/20 hover:bg-violet-500'
                  : 'bg-blue-600 shadow-blue-600/20 hover:bg-blue-500'
              }`}
            >
              {sending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : mode === 'compare' ? (
                <SplitSquareHorizontal className="h-4 w-4" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {sending ? 'Sending...' : mode === 'compare' ? 'Compare' : 'Send'}
            </button>
          </div>
        </div>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className={`grid gap-4 ${results.length > 1 ? 'md:grid-cols-2 lg:grid-cols-3' : ''}`}>
          {results.map((r, idx) => (
            <div
              key={idx}
              className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/80"
            >
              <div className="mb-3 flex items-center justify-between">
                <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-mono font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                  {r.model}
                </span>
                {r.response && (
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusColor(
                      r.response.status
                    )}`}
                  >
                    {r.response.status}
                  </span>
                )}
              </div>

              {r.loading && (
                <div className="flex items-center gap-2 py-8 text-sm text-slate-400">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing...
                </div>
              )}

              {r.error && (
                <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-300">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  {r.error}
                </div>
              )}

              {r.response && (
                <>
                  <div className="mb-3 rounded-xl bg-slate-50 p-4 dark:bg-slate-800/60">
                    <p className="whitespace-pre-wrap text-sm text-slate-800 dark:text-slate-200">
                      {r.response.response_text || 'No response text'}
                    </p>
                  </div>

                  <div className="grid grid-cols-4 gap-2">
                    <div className="rounded-lg bg-slate-50 p-2 text-center dark:bg-slate-800/40">
                      <Coins className="mx-auto h-3.5 w-3.5 text-emerald-500" />
                      <p className="mt-1 text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                        {money(r.response.cost_usd ? Number(r.response.cost_usd) : null)}
                      </p>
                      <p className="text-[9px] text-slate-400">Cost</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-2 text-center dark:bg-slate-800/40">
                      <Hash className="mx-auto h-3.5 w-3.5 text-blue-500" />
                      <p className="mt-1 text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                        {r.response.input_tokens ?? 0}
                      </p>
                      <p className="text-[9px] text-slate-400">In Tokens</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-2 text-center dark:bg-slate-800/40">
                      <Hash className="mx-auto h-3.5 w-3.5 text-violet-500" />
                      <p className="mt-1 text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                        {r.response.output_tokens ?? 0}
                      </p>
                      <p className="text-[9px] text-slate-400">Out Tokens</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-2 text-center dark:bg-slate-800/40">
                      <Clock className="mx-auto h-3.5 w-3.5 text-amber-500" />
                      <p className="mt-1 text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                        {r.response.latency_ms != null ? `${r.response.latency_ms}ms` : '-'}
                      </p>
                      <p className="text-[9px] text-slate-400">Latency</p>
                    </div>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {/* History */}
      <section>
        <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
          Request History ({historyTotal})
        </h2>
        {history.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-10 text-center dark:border-slate-700 dark:bg-slate-900/40">
            <Play className="mx-auto h-8 w-8 text-slate-300 dark:text-slate-600" />
            <p className="mt-3 text-sm font-medium text-slate-500">No playground requests yet.</p>
            <p className="mt-1 text-xs text-slate-400">
              Send your first request using the form above.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">
                    Model
                  </th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">
                    Prompt
                  </th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">
                    Response
                  </th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">
                    Status
                  </th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">
                    Cost
                  </th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">
                    Tokens
                  </th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">
                    Latency
                  </th>
                </tr>
              </thead>
              <tbody>
                {history.map((r) => {
                  const preview =
                    r.user_prompt.length > 60 ? r.user_prompt.slice(0, 60) + '…' : r.user_prompt
                  const responsePreview = r.response_text
                    ? r.response_text.length > 80
                      ? r.response_text.slice(0, 80) + '…'
                      : r.response_text
                    : '-'
                  return (
                    <tr
                      key={r.id}
                      className="border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50"
                    >
                      <td className="px-4 py-3">
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-mono font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                          {r.model}
                        </span>
                      </td>
                      <td className="max-w-xs truncate px-4 py-3 text-sm text-slate-800 dark:text-slate-200">
                        {preview}
                      </td>
                      <td className="max-w-xs truncate px-4 py-3 text-sm text-slate-500">
                        {responsePreview}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusColor(
                            r.status
                          )}`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">
                        {money(r.cost_usd ? Number(r.cost_usd) : null)}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">
                        {r.input_tokens != null ? `${r.input_tokens}/${r.output_tokens}` : '-'}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">
                        {r.latency_ms != null ? `${r.latency_ms}ms` : '-'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
