'use client'

/**
 * Experiment detail: one view for eval and replay experiments (review B-07).
 * Results come from real gateway runs (B-08); "Recommend route" turns the result
 * into a Flywheel recommendation that is applied with audit and rollback (B-05).
 */

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { FlaskConical, Loader2, Pencil, Play, Sparkles } from 'lucide-react'
import { ExperimentEditDialog } from './_components/ExperimentEditDialog'
import { toast } from 'sonner'
import { getEvalExperiment, recommendRouteFromExperiment, runEvalExperiment } from '@/lib/api'
import type { EvalExperiment, ExperimentModelRow } from '@/types/api'
import { PageHeader } from '@/components/ui/page-header'
import { AsyncCard } from '@/components/ui/async-card'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { routes } from '@/lib/routes'

const POLL_MS = 3000

function pct(v: number | null | undefined): string {
  return v === null || v === undefined ? '—' : `${v > 0 ? '+' : ''}${v.toFixed(1)}%`
}

function usd(v: string | null | undefined): string {
  if (v === null || v === undefined) return '—'
  const n = Number(v)
  return Number.isFinite(n) ? `$${n.toFixed(6)}` : '—'
}

const modelColumns: DataTableColumn<ExperimentModelRow>[] = [
  { key: 'label', header: 'Model (route alias)', sortable: true },
  { key: 'items_run', header: 'Items run', sortable: true },
  { key: 'errors', header: 'Errors', sortable: true },
  {
    key: 'avg_score',
    header: 'Avg score',
    sortable: true,
    render: (r) => (r.avg_score === null ? '—' : r.avg_score.toFixed(3)),
    value: (r) => r.avg_score,
  },
  {
    key: 'expected_match_rate',
    header: 'Expected match',
    render: (r) =>
      r.expected_match_rate === null ? '—' : `${(r.expected_match_rate * 100).toFixed(0)}%`,
    value: (r) => r.expected_match_rate,
  },
  {
    key: 'avg_latency_ms',
    header: 'Avg latency',
    sortable: true,
    render: (r) => (r.avg_latency_ms === null ? '—' : `${r.avg_latency_ms} ms`),
    value: (r) => r.avg_latency_ms,
  },
  {
    key: 'avg_cost_usd',
    header: 'Avg cost',
    sortable: true,
    render: (r) => usd(r.avg_cost_usd),
    value: (r) => (r.avg_cost_usd === null ? null : Number(r.avg_cost_usd)),
  },
  { key: 'total_cost_usd', header: 'Total cost', render: (r) => usd(r.total_cost_usd) },
]

export default function ExperimentDetailPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''
  const params = useParams()
  const experimentId = params.experiment_id as string
  const [exp, setExp] = useState<EvalExperiment | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<'run' | 'recommend' | null>(null)
  const { confirm, dialog } = useConfirm()
  const [editing, setEditing] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey || !experimentId) return
    try {
      setExp(await getEvalExperiment(apiKey, experimentId))
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load experiment')
    } finally {
      setLoading(false)
    }
  }, [apiKey, experimentId])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (exp?.status !== 'running') return
    const t = setInterval(() => void load(), POLL_MS)
    return () => clearInterval(t)
  }, [exp?.status, load])

  const run = async () => {
    if (!exp) return
    const calls = (exp.models?.length ?? 0) * 1
    const ok = await confirm({
      title: 'Run this experiment through the gateway?',
      description: `Every dataset item is sent to ${calls} model(s) with your API key. Calls are real: they are governed, metered and count against budgets.`,
      confirmLabel: 'Run',
    })
    if (!ok) return
    setBusy('run')
    try {
      setExp(await runEvalExperiment(apiKey, exp.id))
      toast.success('Experiment started')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to start experiment')
    } finally {
      setBusy(null)
    }
  }

  const recommend = async () => {
    if (!exp) return
    setBusy('recommend')
    try {
      const rec = await recommendRouteFromExperiment(apiKey, exp.id)
      toast.success(
        `Recommendation created: ${rec.alias} → ${rec.proposed_model}. Review and apply it under Optimization.`
      )
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'No recommendation')
    } finally {
      setBusy(null)
    }
  }

  const results = exp?.results ?? null
  const summary = results?.summary

  return (
    <div className="space-y-6">
      {dialog}
      {editing && exp ? (
        <ExperimentEditDialog apiKey={apiKey} experiment={exp} onClose={() => setEditing(false)}
          onSaved={(e) => { setExp(e); setEditing(false) }} />
      ) : null}
      <PageHeader
        icon={FlaskConical}
        title={exp?.name ?? 'Experiment'}
        description={
          exp
            ? `${exp.mode === 'replay' ? 'Replay of recorded runs' : 'Dataset evaluation'}${exp.prompt_name ? ` · prompt ${exp.prompt_name}${exp.prompt_version ? ` v${exp.prompt_version}` : ''}` : ''} · ${exp.status}`
            : undefined
        }
        breadcrumbs={[{ label: 'Experiments', href: '/experiments' }, { label: exp?.name ?? '…' }]}
        actions={
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setEditing(true)}
              disabled={!exp || exp.status === 'running'}
              aria-label="Edit experiment"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              <Pencil className="h-4 w-4" />
              Edit
            </button>
            <button
              type="button"
              onClick={run}
              disabled={!exp || exp.status === 'running' || busy !== null}
              aria-label="Run experiment through the gateway"
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {busy === 'run' || exp?.status === 'running' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {exp?.status === 'running' ? 'Running…' : 'Run'}
            </button>
            <button
              type="button"
              onClick={recommend}
              disabled={exp?.status !== 'completed' || busy !== null}
              aria-label="Create a Flywheel route recommendation from this experiment"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              <Sparkles className="h-4 w-4" />
              Recommend route
            </button>
          </div>
        }
      />

      <AsyncCard
        title="Summary"
        loading={loading}
        error={error ?? (results?.error ? `Run failed: ${results.error}` : null)}
        onRetry={() => void load()}
        empty={!summary}
        emptyTitle={exp?.status === 'running' ? 'Running…' : 'Not run yet'}
        emptyDescription="Run the experiment to send the dataset through the gateway and score the outputs."
      >
        {summary ? (
          <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-6">
            {[
              ['Items', summary.items],
              ['Gateway calls', summary.calls],
              ['Errors', summary.errors],
              ['Skipped', summary.skipped],
              ['Avg score', summary.avg_score === null ? '—' : summary.avg_score.toFixed(3)],
              ['Total cost', usd(summary.total_cost_usd)],
            ].map(([label, value]) => (
              <div key={String(label)}>
                <dt className="text-slate-500">{label}</dt>
                <dd className="text-lg font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
        ) : null}
      </AsyncCard>

      {results?.models?.length ? (
        <AsyncCard title="Models" description="First model is the baseline for deltas and route recommendations.">
          <DataTable
            label="Experiment models"
            rows={results.models}
            columns={modelColumns}
            rowKey={(r) => r.label}
            urlPrefix="models"
            csvFileName={`experiment-${experimentId}-models.csv`}
            searchable={false}
          />
          {results.deltas.length ? (
            <ul className="mt-4 space-y-1 text-sm text-slate-600 dark:text-slate-300">
              {results.deltas.map((d) => (
                <li key={d.candidate}>
                  <span className="font-medium">{d.candidate}</span> vs {d.baseline}: score{' '}
                  {d.score_delta === null ? '—' : `${d.score_delta > 0 ? '+' : ''}${d.score_delta.toFixed(3)}`}, cost{' '}
                  {pct(d.cost_delta_pct)}, latency {pct(d.latency_delta_pct)}
                </li>
              ))}
            </ul>
          ) : null}
        </AsyncCard>
      ) : null}

      {results?.items?.length ? (
        <AsyncCard title="Items" description="Per-item outputs; open a run to see the full trace.">
          <div className="space-y-4">
            {results.items.map((item) => (
              <div key={item.index} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-sm font-medium">#{item.index + 1} {item.input}</p>
                {item.expected_output ? (
                  <p className="text-xs text-slate-500">Expected: {item.expected_output}</p>
                ) : null}
                <div className="mt-2 grid gap-2 md:grid-cols-2">
                  {item.outputs.map((o) => (
                    <div key={o.label} className="rounded bg-slate-50 p-2 text-xs dark:bg-slate-900">
                      <div className="mb-1 flex items-center justify-between font-medium">
                        <span>{o.label}</span>
                        <span>
                          {o.score !== undefined ? `score ${o.score.toFixed(2)} · ` : ''}
                          {o.latency_ms} ms · {usd(o.cost_usd)}
                        </span>
                      </div>
                      {o.ok ? (
                        <p className="whitespace-pre-wrap">{o.text}</p>
                      ) : (
                        <p className="text-status-error">{o.error}</p>
                      )}
                      {o.run_id ? (
                        <Link href={routes.runsRunId(o.run_id)} className="text-indigo-600 hover:underline">
                          View run
                        </Link>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </AsyncCard>
      ) : null}
    </div>
  )
}
