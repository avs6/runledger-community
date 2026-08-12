import { getServerSession } from 'next-auth'
import { Suspense } from 'react'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getRuns } from '@/lib/api'
import RunsTable from '@/components/runs/RunsTable'
import RunFilters from '@/components/runs/RunFilters'
import RunsExportButton from '@/components/runs/RunsExportButton'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { modelColor } from '@/lib/modelColors'
import type { RunListItem } from '@/types/api'

interface PageProps {
  searchParams: {
    status?: string
    feature_tag?: string
    end_user_id?: string
    search?: string
    from?: string
    to?: string
    cursor?: string
    preset?: string
    model?: string
    min_cost?: string
    max_cost?: string
  }
}

function parseCost(value: string | null | undefined) {
  const parsed = Number.parseFloat(value ?? '0')
  return Number.isFinite(parsed) ? parsed : 0
}

function money(value: number) {
  if (value >= 1) return `$${value.toFixed(2)}`
  if (value >= 0.001) return `$${value.toFixed(4)}`
  return `$${value.toFixed(6)}`
}

function compact(value: number) {
  return new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

function RunsOverview({ items, total }: { items: RunListItem[]; total: number }) {
  const succeeded = items.filter((run) => run.status === 'succeeded').length
  const failed = items.filter((run) => run.status === 'failed').length
  const cost = items.reduce((sum, run) => sum + parseCost(run.total_cost_usd), 0)
  const tokens = items.reduce((sum, run) => sum + (run.total_input_tokens ?? 0) + (run.total_output_tokens ?? 0), 0)
  const models = Array.from(new Set(items.map((run) => run.primary_model).filter(Boolean) as string[]))
  const successRate = items.length > 0 ? Math.round((succeeded / items.length) * 100) : 0
  const sample = [...items]
    .sort((a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime())
    .slice(-44)

  return (
    <div className="grid gap-3 xl:grid-cols-[1fr_1.4fr]">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-2">
        {[
          { label: 'Runs', value: total.toLocaleString(), sub: `${items.length} loaded` },
          { label: 'Success rate', value: `${successRate}%`, sub: `${failed} failed in sample` },
          { label: 'Sample cost', value: money(cost), sub: 'current page' },
          { label: 'Tokens', value: compact(tokens), sub: `${models.length} models` },
        ].map((item) => (
          <div key={item.label} className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm ring-1 ring-white/70 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">{item.label}</p>
            <p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-950 dark:text-slate-50">{item.value}</p>
            <p className="mt-1 text-xs text-slate-500">{item.sub}</p>
          </div>
        ))}
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm ring-1 ring-white/70 dark:border-slate-700 dark:bg-slate-900/80">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Model Activity</p>
            <h2 className="mt-1 text-base font-semibold tracking-[-0.03em] text-slate-950 dark:text-slate-50">
              Live Workspace Model Activity
            </h2>
          </div>
          <Link
            href="/request-flow?mode=request-intent-model-result&metric=requests"
            className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700 transition hover:bg-blue-100"
          >
            Open flow
          </Link>
        </div>
        <div className="mt-5 flex h-24 items-end gap-1 rounded-xl border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-700 dark:bg-slate-950/50">
          {sample.length === 0 ? (
            <div className="flex h-full w-full items-center justify-center text-sm text-slate-500">No activity in this window.</div>
          ) : (
            sample.map((run) => {
              const tokenCount = (run.total_input_tokens ?? 0) + (run.total_output_tokens ?? 0)
              const height = Math.max(14, Math.min(72, 14 + tokenCount / 80))
              return (
                <Link
                  key={run.id}
                  href={`/runs/${run.id}`}
                  title={`${run.primary_model ?? 'Unknown model'} / ${run.feature_tag ?? 'untagged'} / ${run.status}`}
                  className="min-w-[8px] flex-1 rounded-t-md transition hover:opacity-75"
                  style={{
                    height,
                    background: `linear-gradient(180deg, ${modelColor(run.primary_model)}, ${modelColor(run.primary_model)}99)`,
                  }}
                />
              )
            })
          )}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {models.slice(0, 10).map((model) => (
            <span key={model} className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: modelColor(model) }} />
              {model}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

async function RunsContent({ searchParams }: PageProps) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 3_600_000).toISOString()

  const data = await getRuns(session.apiKey, {
    limit: 50,
    status: searchParams.status,
    feature_tag: searchParams.feature_tag,
    end_user_id: searchParams.end_user_id,
    search: searchParams.search,
    from: searchParams.from ?? sevenDaysAgo,
    to: searchParams.to,
    cursor: searchParams.cursor,
    model: searchParams.model,
    min_cost: searchParams.min_cost,
    max_cost: searchParams.max_cost,
  })

  const nextHref = data.next_cursor
    ? `/runs?${new URLSearchParams({
        ...Object.fromEntries(
          Object.entries(searchParams).filter(([, v]) => v !== undefined) as [
            string,
            string,
          ][],
        ),
        cursor: data.next_cursor,
      }).toString()}`
    : null

  return (
    <>
      <RunsOverview items={data.items} total={data.total} />
      <RunsTable items={data.items} />
      {nextHref && (
        <div className="mt-4 flex justify-center">
          <Button variant="outline" size="sm" asChild>
            <Link href={nextHref}>Load more</Link>
          </Button>
        </div>
      )}
    </>
  )
}

export default function RunsPage({ searchParams }: PageProps) {
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-[-0.05em] text-slate-950 dark:text-slate-50">Runs</h1>
          <p className="mt-1 text-sm text-slate-500">Dense request ledger with model, cost, token, and latency telemetry.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href="/request-explorer">Request Explorer</Link>
          </Button>
          <Suspense fallback={null}>
            <RunsExportButton />
          </Suspense>
        </div>
      </div>
      <Suspense fallback={null}>
        <RunFilters />
      </Suspense>
      <Suspense
        fallback={
          <div className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        }
      >
        <RunsContent searchParams={searchParams} />
      </Suspense>
    </div>
  )
}
