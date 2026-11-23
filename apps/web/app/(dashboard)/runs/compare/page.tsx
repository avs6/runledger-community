import Link from 'next/link'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { compareRuns } from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { EmptyState } from '@/components/ui/empty-state'
import { SectionError } from '@/components/ui/async-card'
import RunStatusBadge from '@/components/runs/RunStatusBadge'
import CopyId from '@/components/observe/CopyId'
import { routes } from '@/lib/routes'
import { formatCost } from '@/lib/utils'
import type { RunCompareResponse, RunCompareSide } from '@/types/api'

/** Side-by-side compare of two runs (b minus a). Pick runs with ?a=&b=. */
export default async function CompareRunsPage({ searchParams }: { searchParams: { a?: string; b?: string } }) {
  const session = await getServerSession(authOptions)
  if (!session) return null
  const a = searchParams.a?.trim() ?? ''
  const b = searchParams.b?.trim() ?? ''

  let data: RunCompareResponse | null = null
  let error: string | null = null
  if (a && b) {
    try {
      data = await compareRuns(session.apiKey, a, b)
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not compare runs'
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Compare runs"
        description="Two runs side by side: cost, tokens, latency, models and tools, with the difference."
        breadcrumbs={[{ label: 'Runs', href: '/runs' }, { label: 'Compare' }]}
      />
      <form className="flex flex-wrap items-end gap-2" method="get">
        <label className="flex flex-col text-xs font-medium text-slate-600 dark:text-slate-300">
          Run A
          <input name="a" defaultValue={a} required aria-label="Run A id" placeholder="run id" className="mt-1 h-9 w-80 rounded-md border border-input bg-background px-2 font-mono text-xs" />
        </label>
        <label className="flex flex-col text-xs font-medium text-slate-600 dark:text-slate-300">
          Run B
          <input name="b" defaultValue={b} required aria-label="Run B id" placeholder="run id" className="mt-1 h-9 w-80 rounded-md border border-input bg-background px-2 font-mono text-xs" />
        </label>
        <button type="submit" className="h-9 rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground">Compare</button>
      </form>

      {error && <SectionError message={error.includes('404') ? 'One of the runs was not found in this workspace.' : error} />}
      {!data && !error && (
        <EmptyState title="Pick two runs" description="Paste two run ids, or use “Compare with…” on a run’s detail page." />
      )}
      {data && <CompareTable data={data} />}
    </div>
  )
}

function num(v: string | number | null | undefined): number | null {
  if (v === null || v === undefined) return null
  const n = typeof v === 'number' ? v : Number.parseFloat(v)
  return Number.isFinite(n) ? n : null
}

function Delta({ value, money, lowerIsBetter = true }: { value: string | null | undefined; money?: boolean; lowerIsBetter?: boolean }) {
  const n = num(value)
  if (n === null || n === 0) return <span className="text-slate-400">–</span>
  const better = lowerIsBetter ? n < 0 : n > 0
  const text = money ? formatCost(String(Math.abs(n))) : Math.abs(n).toLocaleString()
  return (
    <span className={better ? 'text-status-success' : 'text-status-error'}>
      {n > 0 ? '+' : '−'}{text}
    </span>
  )
}

function CompareTable({ data }: { data: RunCompareResponse }) {
  const rows: Array<{ label: string; get: (s: RunCompareSide) => React.ReactNode; delta?: React.ReactNode }> = [
    { label: 'Status', get: s => <RunStatusBadge status={s.run.status} /> },
    { label: 'Workflow', get: s => s.run.feature_tag ?? '—' },
    { label: 'Primary model', get: s => <span className="font-mono">{s.run.primary_model ?? '—'}</span> },
    { label: 'Models used', get: s => s.models.join(', ') || '—' },
    { label: 'Cost', get: s => formatCost(s.run.total_cost_usd), delta: <Delta value={data.delta.cost_usd} money /> },
    { label: 'Input tokens', get: s => (s.run.total_input_tokens ?? 0).toLocaleString(), delta: <Delta value={data.delta.input_tokens} /> },
    { label: 'Output tokens', get: s => (s.run.total_output_tokens ?? 0).toLocaleString(), delta: <Delta value={data.delta.output_tokens} /> },
    { label: 'Duration', get: s => (s.run.duration_ms != null ? `${s.run.duration_ms.toLocaleString()} ms` : '—'), delta: <Delta value={data.delta.duration_ms} /> },
    { label: 'Provider calls', get: s => s.provider_call_count, delta: <Delta value={data.delta.provider_calls} /> },
    { label: 'Errors', get: s => s.error_count },
    { label: 'Tool calls', get: s => s.tool_call_count, delta: <Delta value={data.delta.tool_calls} /> },
    { label: 'Tools', get: s => s.tools.join(', ') || '—' },
    { label: 'Spans', get: s => s.span_count },
    { label: 'Cached input tokens', get: s => s.cached_input_tokens.toLocaleString() },
    { label: 'Recorded savings', get: s => formatCost(s.savings_usd) },
  ]
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <table className="w-full text-sm">
        <caption className="sr-only">Run comparison</caption>
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-700">
            <th scope="col" className="px-3 py-2">Metric</th>
            {[data.a, data.b].map((side, i) => (
              <th key={side.run.id} scope="col" className="px-3 py-2">
                <span className="mr-1">{i === 0 ? 'A' : 'B'}</span>
                <Link href={routes.runsRunId(side.run.id)} className="font-mono normal-case text-blue-600 hover:underline dark:text-blue-400">
                  {side.run.id.slice(0, 8)}
                </Link>
                <CopyId value={side.run.id} label={`Copy run ${i === 0 ? 'A' : 'B'} id`} />
              </th>
            ))}
            <th scope="col" className="px-3 py-2">B − A</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(row => (
            <tr key={row.label} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
              <th scope="row" className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-300">{row.label}</th>
              <td className="px-3 py-2">{row.get(data.a)}</td>
              <td className="px-3 py-2">{row.get(data.b)}</td>
              <td className="px-3 py-2">{row.delta ?? null}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
