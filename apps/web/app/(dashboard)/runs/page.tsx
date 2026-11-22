import { getServerSession } from 'next-auth'
import { Suspense } from 'react'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getAccessGroupDashboard, getRuns, listSessions } from '@/lib/api'
import RunFilters from '@/components/runs/RunFilters'
import RunsExportButton from '@/components/runs/RunsExportButton'
import RunsTabs from './RunsTabs'
import RunsPaginated from './RunsPaginated'
import SessionsEmbed from './SessionsEmbed'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { modelColor } from '@/lib/modelColors'
import type { RunListItem } from '@/types/api'
import { num } from '@/lib/utils'

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
    access_group_id?: string
    tag?: string
    tool_name?: string
    security_event_only?: string
    api_key_id?: string
  }
}

function parseCost(value: string | null | undefined) {
  const parsed = Number.parseFloat(value ?? '0')
  return Number.isFinite(parsed) ? parsed : 0
}

function money(value: number) {
  if (num(value) >= 1) return `$${num(value).toFixed(2)}`
  if (num(value) >= 0.001) return `$${num(value).toFixed(4)}`
  return `$${num(value).toFixed(6)}`
}

function compact(value: number) {
  return new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

function HeroChart({ items, total }: { items: RunListItem[]; total: number }) {
  const succeeded = items.filter((run) => run.status === 'succeeded').length
  const failed = items.filter((run) => run.status === 'failed').length
  const cost = items.reduce((sum, run) => sum + parseCost(run.total_cost_usd), 0)
  const tokens = items.reduce((sum, run) => sum + (run.total_input_tokens ?? 0) + (run.total_output_tokens ?? 0), 0)
  const models = Array.from(new Set(items.map((run) => run.primary_model).filter(Boolean) as string[]))
  const successRate = items.length > 0 ? Math.round((succeeded / items.length) * 100) : 0
  const sample = [...items]
    .sort((a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime())
    .slice(-60)

  return (
    <div className="space-y-4">
      {/* Compact stats row */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          { label: 'Runs', value: total.toLocaleString() },
          { label: 'Success', value: `${successRate}%` },
          { label: 'Cost', value: money(cost) },
          { label: 'Tokens', value: compact(tokens) },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white/90 px-3 py-2.5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">{item.label}</p>
            <p className="ml-auto text-lg font-semibold tracking-tight text-slate-950 dark:text-slate-50">{item.value}</p>
          </div>
        ))}
      </div>

      {/* Hero chart */}
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-blue-600 dark:text-blue-400">Model Activity</p>
            <h2 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-slate-950 dark:text-slate-50">
              Live Workspace Model Activity
            </h2>
          </div>
          <Link
            href="/request-flow?mode=request-intent-model-result&metric=requests"
            className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700 transition hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-300 dark:hover:bg-blue-900/60"
          >
            Open flow
          </Link>
        </div>
        <div className="mt-4 flex h-44 items-end gap-[3px] rounded-xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-700 dark:bg-slate-950/50">
          {sample.length === 0 ? (
            <div className="flex h-full w-full items-center justify-center text-sm text-slate-500">No activity in this window.</div>
          ) : (
            sample.map((run) => {
              const tokenCount = (run.total_input_tokens ?? 0) + (run.total_output_tokens ?? 0)
              const height = Math.max(16, Math.min(140, 16 + tokenCount / 50))
              return (
                <Link
                  key={run.id}
                  href={`/runs/${run.id}`}
                  title={`${run.primary_model ?? 'Unknown model'} / ${run.feature_tag ?? 'untagged'} / ${run.status}`}
                  className="min-w-[6px] flex-1 rounded-t-md transition hover:opacity-75"
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
          {models.slice(0, 12).map((model) => (
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
  const accessGroupId = searchParams.access_group_id
  const accessGroupDashboard = accessGroupId
    ? await getAccessGroupDashboard(session.apiKey, accessGroupId).catch(() => null)
    : null
  const accessGroup = accessGroupDashboard?.groups[0] ?? null

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
    access_group_id: accessGroupId,
    tag: searchParams.tag,
    tool_name: searchParams.tool_name,
    security_event_only: searchParams.security_event_only === 'true',
    api_key_id: searchParams.api_key_id,
  })
  const sessionsData = await listSessions(session.apiKey, { page: 1, page_size: 50 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 50 }))


  const nextHref = data.next_cursor
    ? `/runs?${new URLSearchParams({
        ...Object.fromEntries(
          Object.entries(searchParams).filter(([, v]) => v !== undefined) as [string, string][],
        ),
        cursor: data.next_cursor,
      }).toString()}`
    : null

  return (
    <>
      {accessGroup && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50/80 px-4 py-3 text-sm text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-100">
          Runs are filtered to the <span className="font-semibold">{accessGroup.name}</span> access group.
        </div>
      )}
      <RunsTabs
        overview={
          <div className="space-y-4">
            <HeroChart items={data.items} total={data.total} />
          </div>
        }
        runs={
          <RunsPaginated items={data.items} total={data.total} nextCursorHref={nextHref} />
        }
        sessions={
          <SessionsEmbed
            items={sessionsData.items}
            total={sessionsData.total}
            page={sessionsData.page}
            pageCount={Math.max(1, Math.ceil(sessionsData.total / sessionsData.page_size))}
          />
        }
      />
    </>
  )
}

export default function RunsPage({ searchParams }: PageProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-[-0.05em] text-slate-950 dark:text-slate-50">Runs</h1>
          <p className="mt-1 text-sm text-slate-500">Dense request ledger with model, cost, token, and latency telemetry.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href={searchParams.access_group_id ? `/request-explorer?access_group_id=${encodeURIComponent(searchParams.access_group_id)}` : '/request-explorer'}>Request Explorer</Link>
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
