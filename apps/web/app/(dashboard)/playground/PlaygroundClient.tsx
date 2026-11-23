'use client'

import { useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import {
  Play, Clock, Coins, Hash, Loader2, Plus, RotateCcw,
  Settings2, SplitSquareHorizontal, X, ChevronDown,
  Sparkles, Zap, AlertCircle, Terminal,
} from 'lucide-react'
import type { PlaygroundModel, PlaygroundRequestResponse, PlaygroundSessionResponse } from '@/types/api'
import { comparePlaygroundModels, getPlaygroundHistory, sendPlaygroundRequest } from '@/lib/api'
import { SessionsBar } from './_components/SessionsBar'
import { EmptyState } from '@/components/ui/empty-state'
import { routes } from '@/lib/routes'
import { num } from '@/lib/utils'

function money(v: number | null | undefined) {
  if (!v) return '$0.00'
  const n = num(v)
  if (n >= 1) return `$${n.toFixed(2)}`
  if (n >= 0.001) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

function statusCls(s: string) {
  if (s === 'completed') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300'
  if (s === 'pending') return 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
  return 'bg-rose-100 text-rose-700 dark:bg-rose-900/50 dark:text-rose-300'
}

/** Side-by-side deltas of a compared model against the first (baseline) column. */
function CompareDelta({ base, other }: { base: PlaygroundRequestResponse; other: PlaygroundRequestResponse }) {
  const delta = (a: number | null | undefined, b: number | null | undefined) => {
    const x = Number(a ?? 0)
    const y = Number(b ?? 0)
    if (!y) return null
    return ((x - y) / y) * 100
  }
  const fmt = (v: number | null) => (v === null ? '—' : `${v > 0 ? '+' : ''}${v.toFixed(0)}%`)
  const cost = delta(other.cost_usd, base.cost_usd)
  const lat = delta(other.latency_ms, base.latency_ms)
  const toks = delta(other.output_tokens, base.output_tokens)
  return (
    <p className="mb-2 text-[10px] text-slate-500" aria-label={`Compared with ${base.model}`}>
      vs {base.model}: cost <span className={cost !== null && cost < 0 ? 'text-emerald-600' : ''}>{fmt(cost)}</span>, latency{' '}
      <span className={lat !== null && lat < 0 ? 'text-emerald-600' : ''}>{fmt(lat)}</span>, output tokens {fmt(toks)}
    </p>
  )
}

type Mode = 'single' | 'compare'
interface ResultCard { model: string; response: PlaygroundRequestResponse | null; loading: boolean; error: string | null }

const inputCls = 'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500'
const PAGE_SIZE = 20

export default function PlaygroundClient({
  initialSessions,
  initialHistory,
  initialHistoryTotal,
  models,
}: {
  models: PlaygroundModel[]
  initialSessions: PlaygroundSessionResponse[]
  initialHistory: PlaygroundRequestResponse[]
  initialHistoryTotal: number
}) {
  const { data: session } = useSession()
  const apiKey = (session as Record<string, unknown> | null)?.apiKey as string | undefined

  const [mode, setMode] = useState<Mode>('single')
  // Model choices are this workspace's gateway route aliases (review ui-fixes #6).
  const aliasNames = models.map((m) => m.alias)
  const [model, setModel] = useState(aliasNames[0] ?? '')
  const [compareModels, setCompareModels] = useState<string[]>(aliasNames.slice(0, 2))
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
  const [histPage, setHistPage] = useState(0)
  const [sessions, setSessions] = useState<PlaygroundSessionResponse[]>(initialSessions)
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)

  async function selectSession(s: PlaygroundSessionResponse | null) {
    setActiveSessionId(s?.id ?? null)
    if (s?.system_prompt) {
      setSystemPrompt(s.system_prompt)
      setShowSystemPrompt(true)
    }
    if (!apiKey) return
    try {
      const h = await getPlaygroundHistory(apiKey, { session_id: s?.id, limit: 50 })
      setHistory(h.requests)
      setHistoryTotal(h.total)
      setHistPage(0)
    } catch {
      // keep the current history if the filtered load fails
    }
  }

  const addCompareModel = useCallback(() => {
    if (compareModels.length < 5) {
      const available = aliasNames.filter((m) => !compareModels.includes(m))
      if (available[0]) setCompareModels([...compareModels, available[0]])
    }
  }, [compareModels, aliasNames])

  const removeCompareModel = useCallback((idx: number) => {
    if (compareModels.length > 2) setCompareModels(compareModels.filter((_, i) => i !== idx))
  }, [compareModels])

  const updateCompareModel = useCallback((idx: number, value: string) => {
    const next = [...compareModels]; next[idx] = value; setCompareModels(next)
  }, [compareModels])

  async function handleSend() {
    if (!apiKey || !userPrompt.trim()) return
    setSending(true)
    const params: Record<string, unknown> = {}
    if (temperature !== 0.7) params.temperature = temperature
    if (maxTokens !== 1024) params.max_tokens = maxTokens
    try {
      const parameters = Object.keys(params).length > 0 ? params : undefined
      if (mode === 'single') {
        setResults([{ model, response: null, loading: true, error: null }])
        const data = await sendPlaygroundRequest(apiKey, {
          model,
          user_prompt: userPrompt,
          system_prompt: systemPrompt || undefined,
          session_id: activeSessionId ?? undefined,
          parameters,
        })
        setResults([{ model, response: data, loading: false, error: null }])
        setHistory((prev) => [data, ...prev])
        setHistoryTotal((prev) => prev + 1)
      } else {
        setResults(compareModels.map((m) => ({ model: m, response: null, loading: true, error: null })))
        const data = await comparePlaygroundModels(apiKey, {
          models: compareModels,
          session_id: activeSessionId ?? undefined,
          user_prompt: userPrompt,
          system_prompt: systemPrompt || undefined,
          parameters,
        })
        setResults(data.results.map((r) => ({ model: r.model, response: r, loading: false, error: null })))
        setHistory((prev) => [...data.results, ...prev])
        setHistoryTotal((prev) => prev + data.results.length)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Request failed'
      setResults((prev) => prev.map((r) => (r.loading ? { ...r, loading: false, error: msg } : r)))
    } finally { setSending(false) }
  }

  function handleReset() {
    setResults([]); setUserPrompt(''); setSystemPrompt('')
    setShowSystemPrompt(false); setShowParams(false)
    setTemperature(0.7); setMaxTokens(1024)
  }

  const histTotalPages = Math.ceil(history.length / PAGE_SIZE)
  const pagedHistory = history.slice(histPage * PAGE_SIZE, (histPage + 1) * PAGE_SIZE)

  const totalCost = history.reduce((s, r) => s + (r.cost_usd ? Number(r.cost_usd) : 0), 0)
  const totalTokensAll = history.reduce((s, r) => s + (r.input_tokens ?? 0) + (r.output_tokens ?? 0), 0)
  const avgLatency = history.length > 0 ? history.reduce((s, r) => s + (r.latency_ms ?? 0), 0) / history.length : 0

  return (
    <div className="space-y-3">
      {/* ── Header ─────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/25">
            <Terminal className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">API Playground</h1>
            <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">Every request goes through the RunLedger gateway with your API key: routing, budgets, guardrails and metering apply, and each call is recorded as a run.</p>
          </div>
        </div>
        <div className="flex gap-1.5">
          {[
            { label: 'Gateway', href: '/gateway' },
            { label: 'Scorecards', href: '/model-scorecards' },
            { label: 'Eval Studio', href: '/evaluation' },
            { label: 'Model Usage', href: '/model-usage' },
          ].map(({ label, href }) => (
            <Link key={label} href={href} className="rounded-full bg-indigo-100 dark:bg-indigo-900/30 px-2.5 py-1 text-[10px] font-semibold text-indigo-700 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-800/40 transition-colors">{label}</Link>
          ))}
        </div>
      </div>

      {/* ── KPI strip ──────────────────────────────────── */}
      <div className="grid grid-cols-6 gap-2">
        {[
          { label: 'Total Requests', value: historyTotal },
          { label: 'Total Cost', value: money(totalCost), accent: true },
          { label: 'Tokens Used', value: totalTokensAll.toLocaleString() },
          { label: 'Avg Latency', value: `${avgLatency.toFixed(0)}ms` },
          { label: 'Sessions', value: sessions.length },
          { label: 'Models', value: new Set(history.map(h => h.model)).size },
        ].map(({ label, value, accent }) => (
          <div key={label} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-2.5 py-2 text-center">
            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{label}</p>
            <p className={`text-sm font-bold ${accent ? 'text-indigo-600 dark:text-indigo-400' : 'text-slate-900 dark:text-white'}`}>{value}</p>
          </div>
        ))}
      </div>

      {models.length === 0 && (
        <EmptyState
          title="No gateway routes yet"
          description="The Playground sends requests to your gateway route aliases. Add a route, then come back."
          action={<Link href="/gateway" className="text-sm font-medium text-indigo-600 hover:underline">Open Gateway</Link>}
        />
      )}

      {/* ── Mode + Input ───────────────────────────────── */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 p-4 space-y-3">
        {apiKey && (
          <SessionsBar
            apiKey={apiKey}
            sessions={sessions}
            activeId={activeSessionId}
            systemPrompt={systemPrompt}
            onSessionsChange={setSessions}
            onSelect={(s) => void selectSession(s)}
          />
        )}
        <div className="flex items-center gap-2">
          <div className="flex gap-0.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-0.5">
            <button onClick={() => setMode('single')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition ${mode === 'single' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-500 hover:text-slate-800 dark:hover:text-white'}`}>
              <Zap className="h-3.5 w-3.5" />Single
            </button>
            <button onClick={() => setMode('compare')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition ${mode === 'compare' ? 'bg-violet-600 text-white shadow-sm' : 'text-slate-500 hover:text-slate-800 dark:hover:text-white'}`}>
              <SplitSquareHorizontal className="h-3.5 w-3.5" />Compare
            </button>
          </div>
          {mode === 'single' ? (
            <div className="relative flex-1 max-w-xs">
              <select aria-label="Route alias" value={model} onChange={(e) => setModel(e.target.value)} className={inputCls}>
                {models.map((m) => <option key={m.alias} value={m.alias}>{m.alias} ({m.targets.join(', ')})</option>)}
              </select>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-1.5 flex-1">
              {compareModels.map((m, idx) => (
                <div key={idx} className="flex items-center gap-0.5">
                  <select aria-label={`Compare route alias ${idx + 1}`} value={m} onChange={(e) => updateCompareModel(idx, e.target.value)} className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2 py-1 text-[10px] focus:outline-none focus:ring-2 focus:ring-violet-500">
                    {aliasNames.map((pm) => <option key={pm} value={pm}>{pm}</option>)}
                  </select>
                  {compareModels.length > 2 && (
                    <button aria-label={`Remove ${m} from comparison`} onClick={() => removeCompareModel(idx)} className="rounded p-0.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/30"><X className="h-3 w-3" /></button>
                  )}
                </div>
              ))}
              {compareModels.length < 5 && (
                <button onClick={addCompareModel} className="rounded-lg bg-slate-100 dark:bg-slate-800 px-2 py-1 text-[10px] font-medium text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700 flex items-center gap-0.5">
                  <Plus className="h-3 w-3" />Add
                </button>
              )}
              <span className="text-[9px] text-slate-400">{compareModels.length}/5</span>
            </div>
          )}
          <div className="flex gap-1 ml-auto">
            <button onClick={() => setShowSystemPrompt(!showSystemPrompt)}
              className={`flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-medium transition ${showSystemPrompt ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
              <Sparkles className="h-3 w-3" />System
            </button>
            <button onClick={() => setShowParams(!showParams)}
              className={`flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-medium transition ${showParams ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
              <Settings2 className="h-3 w-3" />Params
            </button>
            {results.length > 0 && (
              <button onClick={handleReset} className="flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-medium text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800">
                <RotateCcw className="h-3 w-3" />Reset
              </button>
            )}
          </div>
        </div>

        {showSystemPrompt && (
          <textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="You are a helpful assistant..." rows={2}
            className={`${inputCls} resize-none`} />
        )}

        {showParams && (
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5">Temperature ({temperature})</label>
              <input type="range" min="0" max="2" step="0.1" value={temperature} onChange={(e) => setTemperature(parseFloat(e.target.value))} className="w-full accent-indigo-600" />
            </div>
            <div className="w-32">
              <label className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-0.5">Max Tokens</label>
              <input type="number" min="1" max="128000" value={maxTokens} onChange={(e) => setMaxTokens(parseInt(e.target.value) || 1024)} className={inputCls} />
            </div>
          </div>
        )}

        <div className="relative">
          <textarea value={userPrompt} onChange={(e) => setUserPrompt(e.target.value)}
            placeholder="Enter your prompt..." rows={3}
            onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); handleSend() } }}
            className={`${inputCls} resize-none pb-10`} />
          <div className="absolute bottom-2 right-2 flex items-center gap-2">
            <span className="text-[9px] text-slate-400">{typeof navigator !== 'undefined' && navigator.platform?.includes('Mac') ? '⌘' : 'Ctrl'}+Enter</span>
            <button onClick={handleSend} disabled={sending || !userPrompt.trim() || !apiKey || models.length === 0}
              className={`flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition disabled:opacity-40 ${mode === 'compare' ? 'bg-violet-600 hover:bg-violet-700' : 'bg-indigo-600 hover:bg-indigo-700'}`}>
              {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : mode === 'compare' ? <SplitSquareHorizontal className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
              {sending ? 'Sending…' : mode === 'compare' ? 'Compare' : 'Send'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Results ─────────────────────────────────────── */}
      {results.length > 0 && (
        <div className={`grid gap-3 ${results.length > 1 ? 'md:grid-cols-2 lg:grid-cols-3' : ''}`}>
          {results.map((r, idx) => (
            <div key={idx} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="rounded-lg bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-mono font-semibold text-slate-700 dark:text-slate-300">{r.model}</span>
                {r.response && <span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${statusCls(r.response.status)}`}>{r.response.status}</span>}
              </div>
              {r.loading && <div className="flex items-center gap-2 py-6 text-xs text-slate-400"><Loader2 className="h-3.5 w-3.5 animate-spin" />Processing…</div>}
              {r.error && <div className="flex items-center gap-2 rounded-lg border border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/40 px-3 py-2 text-xs text-rose-700 dark:text-rose-300"><AlertCircle className="h-3.5 w-3.5 shrink-0" />{r.error}</div>}
              {r.response && (
                <>
                  {r.response.error ? (
                    <div className="mb-2 flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300"><AlertCircle className="h-3.5 w-3.5 shrink-0" />{r.response.error}</div>
                  ) : (
                    <div className="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-3 mb-2">
                      <p className="whitespace-pre-wrap text-xs text-slate-800 dark:text-slate-200 leading-relaxed max-h-60 overflow-y-auto">{r.response.response_text || 'No response text'}</p>
                    </div>
                  )}
                  {results.length > 1 && idx > 0 && results[0].response && (
                    <CompareDelta base={results[0].response} other={r.response} />
                  )}
                  <div className="grid grid-cols-4 gap-1.5">
                    {[
                      { icon: <Coins className="h-3 w-3 text-emerald-500" />, value: money(r.response.cost_usd ? Number(r.response.cost_usd) : null), label: 'Cost' },
                      { icon: <Hash className="h-3 w-3 text-blue-500" />, value: r.response.input_tokens ?? 0, label: 'In' },
                      { icon: <Hash className="h-3 w-3 text-violet-500" />, value: r.response.output_tokens ?? 0, label: 'Out' },
                      { icon: <Clock className="h-3 w-3 text-amber-500" />, value: r.response.latency_ms != null ? `${r.response.latency_ms}ms` : '-', label: 'Latency' },
                    ].map(({ icon, value, label }) => (
                      <div key={label} className="rounded-lg bg-slate-50 dark:bg-slate-800/40 px-2 py-1.5 text-center">
                        <div className="flex justify-center">{icon}</div>
                        <p className="text-[10px] font-bold text-slate-700 dark:text-slate-300 tabular-nums">{value}</p>
                        <p className="text-[8px] text-slate-400">{label}</p>
                      </div>
                    ))}
                  </div>
                  {r.response.run_id && (
                    <Link href={routes.runsRunId(r.response.run_id)} className="mt-2 inline-block text-[10px] font-medium text-indigo-600 hover:underline">
                      View recorded run
                    </Link>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── History ─────────────────────────────────────── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Request History ({historyTotal})</h2>
        </div>
        {history.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/60 dark:bg-slate-900/60 px-6 py-10 text-center">
            <Play className="h-7 w-7 text-slate-400" />
            <h3 className="mt-3 text-xs font-bold text-slate-700 dark:text-slate-200">No playground requests yet</h3>
            <p className="mt-1 text-[10px] text-slate-500">Send your first request using the form above.</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-100 dark:border-slate-800 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    <th className="px-3 py-1.5 text-left">Model</th>
                    <th className="px-3 py-1.5 text-left">Prompt</th>
                    <th className="px-3 py-1.5 text-left">Response</th>
                    <th className="px-3 py-1.5 text-left">Status</th>
                    <th className="px-3 py-1.5 text-right">Cost</th>
                    <th className="px-3 py-1.5 text-right">Tokens</th>
                    <th className="px-3 py-1.5 text-right">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {pagedHistory.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                      <td className="px-3 py-1.5"><span className="rounded bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-700 dark:text-slate-300">{r.model}</span></td>
                      <td className="px-3 py-1.5 max-w-[200px] truncate text-slate-800 dark:text-slate-200">{r.user_prompt.length > 50 ? r.user_prompt.slice(0, 50) + '…' : r.user_prompt}</td>
                      <td className="px-3 py-1.5 max-w-[200px] truncate text-slate-500">{r.response_text ? (r.response_text.length > 60 ? r.response_text.slice(0, 60) + '…' : r.response_text) : '-'}</td>
                      <td className="px-3 py-1.5"><span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${statusCls(r.status)}`}>{r.status}</span></td>
                      <td className="px-3 py-1.5 text-right tabular-nums text-slate-600 dark:text-slate-400">{money(r.cost_usd ? Number(r.cost_usd) : null)}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums text-slate-600 dark:text-slate-400">{r.input_tokens != null ? `${r.input_tokens}/${r.output_tokens}` : '-'}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums text-slate-600 dark:text-slate-400">{r.latency_ms != null ? `${r.latency_ms}ms` : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {histTotalPages > 1 && (
              <div className="flex items-center justify-between">
                <p className="text-[10px] text-slate-400">{histPage * PAGE_SIZE + 1}–{Math.min((histPage + 1) * PAGE_SIZE, history.length)} of {history.length}</p>
                <div className="flex gap-1">
                  <button onClick={() => setHistPage(p => Math.max(0, p - 1))} disabled={histPage === 0} className="rounded-lg bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:text-slate-300 disabled:opacity-40">Prev</button>
                  <button onClick={() => setHistPage(p => Math.min(histTotalPages - 1, p + 1))} disabled={histPage >= histTotalPages - 1} className="rounded-lg bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:text-slate-300 disabled:opacity-40">Next</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
