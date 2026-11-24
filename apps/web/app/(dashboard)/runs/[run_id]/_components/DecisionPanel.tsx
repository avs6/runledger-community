import Link from 'next/link'
import { Route, ShieldCheck, Sparkles, Wallet, FileText } from 'lucide-react'
import type { GatewayRunDecision } from '@/lib/api'

/**
 * "Why this route" — the gateway's decision trace for a run: the route that served and
 * why, the candidates preflight prepared (fallbacks), routes skipped by caps, and the
 * cache / budget / guardrail / prompt outcome. The same summary is returned to the
 * caller as the X-RunLedger-Decision response header.
 */

function Row({ icon, label, value, detail }: { icon: React.ReactNode; label: string; value: string; detail?: string | null }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-slate-200/80 bg-slate-50/60 px-2.5 py-2 dark:border-slate-700/60 dark:bg-slate-800/40">
      <span className="mt-0.5 text-slate-500 dark:text-slate-400">{icon}</span>
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">{label}</p>
        <p className="truncate text-xs font-semibold text-slate-900 dark:text-slate-100">{value}</p>
        {detail && <p className="mt-0.5 break-words font-mono text-[10px] text-slate-500 dark:text-slate-400">{detail}</p>}
      </div>
    </div>
  )
}

export default function DecisionPanel({ data }: { data: GatewayRunDecision | null }) {
  // Runs that did not go through the gateway have no decision; show nothing.
  if (!data || (!data.decision && !data.gateway_request_id)) return null
  const d = data.decision ?? {}
  const served = d.route?.served
  const routeValue = served ? `${served.alias} → ${served.provider}:${served.target_model}` : (d.route?.alias ?? 'Unknown')
  const budget = d.budget?.status ?? 'ok'
  const budgetDetail = [
    d.budget?.budget_id ? `budget ${d.budget.budget_id.slice(0, 8)}…` : null,
    d.budget?.rerouted_from ? `rerouted from ${d.budget.rerouted_from}` : null,
  ].filter(Boolean).join(' · ') || null
  const guardrail = d.guardrail?.post_call === 'block' ? 'blocked after call' : (d.guardrail?.result ?? 'off')

  return (
    <section aria-labelledby="decision-panel-title" className="rounded-xl border border-slate-200/80 bg-white p-3 dark:border-slate-700/60 dark:bg-slate-900">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/80 pb-2 dark:border-slate-700/60">
        <h2 id="decision-panel-title" className="text-sm font-semibold text-slate-800 dark:text-slate-200">Why this route</h2>
        <div className="flex flex-wrap gap-2 text-[11px] text-slate-500 dark:text-slate-400">
          {data.workflow && <span>Workflow <span className="font-semibold text-slate-800 dark:text-slate-200">{data.workflow}</span></span>}
          {data.gateway_overhead_ms != null && <span>Gateway overhead <span className="font-semibold text-slate-800 dark:text-slate-200">{data.gateway_overhead_ms} ms</span></span>}
          <Link href="/request-explorer" className="font-semibold text-blue-600 hover:underline dark:text-blue-400">Request explorer</Link>
        </div>
      </div>

      {data.decision_header && (
        <p className="mt-2 break-all rounded-md bg-slate-100 px-2 py-1 font-mono text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-300" title="X-RunLedger-Decision response header">
          X-RunLedger-Decision: {data.decision_header}
        </p>
      )}

      <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <Row icon={<Route className="h-3.5 w-3.5" />} label="Route" value={routeValue} detail={served?.reason ?? d.route?.reason ?? null} />
        <Row icon={<Sparkles className="h-3.5 w-3.5" />} label="Cache" value={d.cache?.result ?? 'off'} detail={d.cache ? `exact ${d.cache.exact ?? 'off'} · semantic ${d.cache.semantic ?? 'off'}` : null} />
        <Row icon={<Wallet className="h-3.5 w-3.5" />} label="Budget" value={budget} detail={budgetDetail} />
        <Row icon={<ShieldCheck className="h-3.5 w-3.5" />} label="Guardrails" value={guardrail} detail={d.guardrail?.reason ?? (d.guardrail?.checked != null ? `${d.guardrail.checked} pre-call rule(s)` : null)} />
      </div>

      {d.prompt?.prompt_name && (
        <div className="mt-2">
          <Row
            icon={<FileText className="h-3.5 w-3.5" />}
            label="Prompt"
            value={`${d.prompt.prompt_name} v${d.prompt.prompt_version ?? '?'} (${d.prompt.prompt_environment ?? 'default'})`}
            detail={d.prompt.missing_variables?.length ? `missing variables: ${d.prompt.missing_variables.join(', ')}` : d.prompt.prompt_ref ?? null}
          />
        </div>
      )}

      {(d.candidates?.length ?? 0) > 0 && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-xs">
            <caption className="sr-only">Routes prepared for this request, in the order the gateway tries them</caption>
            <thead>
              <tr className="border-b border-slate-100 text-left text-[10px] uppercase tracking-wider text-slate-500 dark:border-slate-800">
                <th scope="col" className="py-1 pr-2">#</th>
                <th scope="col" className="py-1 pr-2">Alias</th>
                <th scope="col" className="py-1 pr-2">Provider / model</th>
                <th scope="col" className="py-1 pr-2">Trigger</th>
                <th scope="col" className="py-1">Served</th>
              </tr>
            </thead>
            <tbody>
              {d.candidates!.map((c, i) => (
                <tr key={`${c.route_id}-${i}`} className="border-b border-slate-50 dark:border-slate-800/60">
                  <td className="py-1 pr-2 text-slate-500">{i + 1}</td>
                  <td className="py-1 pr-2 font-medium">{c.alias}</td>
                  <td className="py-1 pr-2 font-mono">{c.provider}:{c.target_model}</td>
                  <td className="py-1 pr-2">{c.trigger}</td>
                  <td className="py-1">{served?.route_id === c.route_id ? '✓' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(d.skipped_routes?.length ?? 0) > 0 && (
        <ul className="mt-2 space-y-0.5 text-[11px] text-amber-700 dark:text-amber-400" aria-label="Routes skipped">
          {d.skipped_routes!.map((s) => (
            <li key={s.route_id}>Skipped {s.alias} ({s.route_id.slice(0, 8)}…): {s.why}</li>
          ))}
        </ul>
      )}

      {data.guardrail_events.length > 0 && (
        <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">
          {data.guardrail_events.length} guardrail event(s) linked:{' '}
          {data.guardrail_events.slice(0, 5).map((e) => `${e.guardrail_name} (${e.mode}: ${e.decision})`).join(', ')}
        </p>
      )}
    </section>
  )
}
