'use client'

import { useMemo, useState } from 'react'
import { FlaskConical, RefreshCw } from 'lucide-react'
import { previewGatewayRoute, type GatewayRoutePreview } from '@/lib/api/gateway'
import { apiErrorMessage } from '@/lib/api'
import { SectionError } from '@/components/ui/async-card'
import { parseCsvTags } from './shared'
import { useGateway } from './useGatewayState'

function usd(value: string | null): string {
  if (value == null) return 'unpriced'
  const n = parseFloat(value)
  return n < 0.01 ? `$${n.toFixed(6)}` : `$${n.toFixed(4)}`
}

/**
 * Test request (ENH): dry-run an alias through the same route selection the gateway uses,
 * and show the chosen route, its estimated cost and its recent latency. No provider call.
 */
export function RouteTestPanel() {
  const { apiKey, gatewayRoutes } = useGateway()
  const aliases = useMemo(
    () => Array.from(new Set(gatewayRoutes.map((r) => r.alias))).sort(),
    [gatewayRoutes],
  )
  const [model, setModel] = useState('')
  const [prompt, setPrompt] = useState('Summarise this support ticket in two sentences.')
  const [tags, setTags] = useState('')
  const [region, setRegion] = useState('')
  const [outputTokens, setOutputTokens] = useState('256')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<GatewayRoutePreview | null>(null)

  async function run(e: React.FormEvent) {
    e.preventDefault()
    const alias = model || aliases[0]
    if (!apiKey || !alias) return
    setRunning(true)
    setError('')
    try {
      setResult(
        await previewGatewayRoute(apiKey, {
          model: alias,
          prompt,
          tags: parseCsvTags(tags),
          region: region.trim() || null,
          expected_output_tokens: parseInt(outputTokens, 10) || 0,
        }),
      )
    } catch (err) {
      setError(apiErrorMessage(err, 'Test request failed'))
    } finally {
      setRunning(false)
    }
  }

  const input = 'rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-900'
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900" aria-labelledby="route-test-title">
      <div className="mb-2 flex items-center gap-2">
        <FlaskConical className="h-4 w-4 text-violet-500" aria-hidden />
        <h2 id="route-test-title" className="text-sm font-semibold text-slate-900 dark:text-white">Test request</h2>
        <span className="text-[10px] text-slate-500">Dry run · same selection as the gateway · no provider call</span>
      </div>
      <form onSubmit={run} className="grid grid-cols-1 gap-2 md:grid-cols-6">
        <label className="flex flex-col gap-0.5 text-[10px] text-slate-500">Alias
          <select aria-label="Alias to test" value={model || aliases[0] || ''} onChange={(e) => setModel(e.target.value)} className={input}>
            {aliases.length === 0 && <option value="">No routes yet</option>}
            {aliases.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-0.5 text-[10px] text-slate-500 md:col-span-2">Prompt
          <input aria-label="Test prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} className={input} />
        </label>
        <label className="flex flex-col gap-0.5 text-[10px] text-slate-500">Tags
          <input aria-label="Request tags, comma separated" value={tags} onChange={(e) => setTags(e.target.value)} placeholder="tier:gold" className={input} />
        </label>
        <label className="flex flex-col gap-0.5 text-[10px] text-slate-500">Region
          <input aria-label="Preferred region" value={region} onChange={(e) => setRegion(e.target.value)} placeholder="any" className={input} />
        </label>
        <div className="flex items-end gap-2">
          <label className="flex flex-1 flex-col gap-0.5 text-[10px] text-slate-500">Output tokens
            <input aria-label="Expected output tokens" type="number" min={0} value={outputTokens} onChange={(e) => setOutputTokens(e.target.value)} className={input} />
          </label>
          <button type="submit" disabled={running || aliases.length === 0} className="flex items-center gap-1 rounded-lg bg-violet-600 px-3 py-1 text-xs font-semibold text-white hover:bg-violet-700 disabled:opacity-50">
            {running && <RefreshCw className="h-3 w-3 animate-spin" aria-hidden />}Run
          </button>
        </div>
      </form>
      {error && <div className="mt-2"><SectionError message={error} /></div>}
      {result && (
        <div className="mt-3 space-y-2" aria-live="polite">
          <div className="flex flex-wrap gap-3 text-xs">
            <span><span className="text-slate-500">Decision:</span> <code className="font-mono">{result.decision_reason}</code></span>
            {result.policy_type && <span><span className="text-slate-500">Policy:</span> {result.policy_type}</span>}
            <span><span className="text-slate-500">Est. cost:</span> <b>{usd(result.est_cost_usd)}</b> ({result.est_input_tokens} in / {result.est_output_tokens} out)</span>
            <span><span className="text-slate-500">p50 latency:</span> <b>{result.p50_latency_ms ? `${parseFloat(result.p50_latency_ms).toFixed(0)} ms` : 'no traffic yet'}</b></span>
            {result.fallback_aliases.length > 0 && <span><span className="text-slate-500">Fallbacks:</span> {result.fallback_aliases.join(' → ')}</span>}
          </div>
          {result.warnings.map((w) => (
            <p key={w} className="text-xs text-status-warning">{w}</p>
          ))}
          {result.candidates.length > 0 && (
            <table className="w-full text-left text-xs" aria-label="Candidate routes">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-700">
                  <th scope="col" className="py-1 font-medium">Route</th>
                  <th scope="col" className="py-1 font-medium">Priority</th>
                  <th scope="col" className="py-1 font-medium">Region</th>
                  <th scope="col" className="py-1 font-medium">Est. cost</th>
                  <th scope="col" className="py-1 font-medium">p50 / p95 (7d)</th>
                </tr>
              </thead>
              <tbody>
                {result.candidates.map((c) => (
                  <tr key={c.route_id} className={`border-b border-slate-100 dark:border-slate-800 ${c.selected ? 'bg-violet-50 font-semibold dark:bg-violet-950/30' : ''}`}>
                    <td className="py-1">{c.selected && <span className="mr-1 text-violet-600">●</span>}{c.provider}/{c.target_model}</td>
                    <td className="py-1">{c.priority}</td>
                    <td className="py-1">{c.region ?? '—'}</td>
                    <td className="py-1">{usd(c.est_cost_usd)}</td>
                    <td className="py-1">{c.p50_latency_ms ? `${parseFloat(c.p50_latency_ms).toFixed(0)} / ${parseFloat(c.p95_latency_ms ?? '0').toFixed(0)} ms (${c.sample_size})` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </section>
  )
}
