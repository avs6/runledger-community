import { getServerSession } from 'next-auth'
import { Suspense } from 'react'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getAccessGroupDashboard, getInvestigationFinopsBudgetPosture, getInvestigationGatewayRuntimePosture, getInvestigationGovernancePosture, getInvestigationOrgIdentityPosture, getOverviewScopePosture, getRuns, listSessions } from '@/lib/api'
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

function PostureCards({
  governance,
  finops,
  orgIdentity,
  gatewayRuntime,
  scopePosture,
}: {
  governance: Awaited<ReturnType<typeof getInvestigationGovernancePosture>> | null
  finops: Awaited<ReturnType<typeof getInvestigationFinopsBudgetPosture>> | null
  orgIdentity: Awaited<ReturnType<typeof getInvestigationOrgIdentityPosture>> | null
  gatewayRuntime: Awaited<ReturnType<typeof getInvestigationGatewayRuntimePosture>> | null
  scopePosture: Awaited<ReturnType<typeof getOverviewScopePosture>> | null
}) {
  return (
    <div className="space-y-3">
      {governance && (
        <div className="grid gap-2 md:grid-cols-3">
          {[
            { label: 'Governance Runs', value: governance.filtered_runs.toLocaleString(), sub: `${governance.security.runs_with_events} with security evidence` },
            { label: 'Tool Policies', value: governance.tool_governance.active_tool_policies.toLocaleString(), sub: `${governance.tool_governance.filtered_tool_calls} filtered tool calls` },
            { label: 'Security Events', value: governance.security.events.toLocaleString(), sub: `${governance.alert_rules.recent_firings} recent alert firings` },
          ].map((item) => (
            <div key={item.label} className="rounded-xl border border-slate-200 bg-white/90 px-3 py-2.5 dark:border-slate-700 dark:bg-slate-900/80">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">{item.label}</p>
                <p className="text-lg font-semibold tracking-tight text-slate-950 dark:text-slate-50">{item.value}</p>
              </div>
              <p className="mt-0.5 text-[10px] text-slate-500">{item.sub}</p>
            </div>
          ))}
          <div className="md:col-span-3 flex flex-wrap gap-3 rounded-xl border border-cyan-200 bg-cyan-50/70 px-3 py-2 text-xs font-semibold text-cyan-800 dark:border-cyan-900/40 dark:bg-cyan-950/20 dark:text-cyan-100">
            <Link href="/tool-registry" className="hover:underline">Tool Registry</Link>
            <Link href="/tool-policies" className="hover:underline">Tool Policies</Link>
            <Link href="/security" className="hover:underline">Security</Link>
            <Link href="/alert-rules" className="hover:underline">Alert Rules</Link>
            <Link href="/audit" className="hover:underline">Audit Log</Link>
            <Link href="/governance-pack" className="hover:underline">Governance Pack</Link>
          </div>
        </div>
      )}
      {finops && (
        <div className="grid gap-2 md:grid-cols-4">
          {[
            { label: 'Active Budgets', value: `${finops.budget_context.active_budgets} / ${finops.budget_context.budgets}`, sub: `${finops.budget_context.breach_count} in breach` },
            { label: 'Budget Limit', value: money(finops.budget_context.total_limit_usd), sub: `${finops.budget_context.active_overrides} overrides` },
            { label: 'Spend (30d)', value: money(finops.spend_context.total_spend_30d), sub: `${finops.spend_context.total_runs_30d.toLocaleString()} runs` },
            { label: 'Billing', value: `${finops.billing_context.open_billing_periods} open`, sub: `${finops.billing_context.chargeback_rules} chargeback rules` },
          ].map((item) => (
            <div key={item.label} className="rounded-xl border border-slate-200 bg-white/90 px-3 py-2.5 dark:border-slate-700 dark:bg-slate-900/80">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">{item.label}</p>
                <p className="text-lg font-semibold tracking-tight text-slate-950 dark:text-slate-50">{item.value}</p>
              </div>
              <p className="mt-0.5 text-[10px] text-slate-500">{item.sub}</p>
            </div>
          ))}
          <div className="md:col-span-4 flex flex-wrap gap-3 rounded-xl border border-emerald-200 bg-emerald-50/70 px-3 py-2 text-xs font-semibold text-emerald-800 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-100">
            <Link href="/budgets" className="hover:underline">Budgets</Link>
            <Link href="/billing" className="hover:underline">Billing</Link>
            <Link href="/chargeback" className="hover:underline">Chargeback</Link>
          </div>
        </div>
      )}
      {orgIdentity && (
        <div className="grid gap-2 md:grid-cols-5">
          {[
            { label: 'Users', value: orgIdentity.user_context.workspace_users.toLocaleString(), sub: `${orgIdentity.user_context.distinct_end_users_30d} end users (30d)` },
            { label: 'API Keys', value: `${orgIdentity.api_key_context.active_keys} / ${orgIdentity.api_key_context.total_keys}`, sub: `${orgIdentity.api_key_context.keys_with_traffic_30d} with traffic` },
            { label: 'Groups', value: scopePosture ? `${scopePosture.access_group_context.active_access_groups}/${scopePosture.access_group_context.access_groups}` : '—', sub: scopePosture ? `${scopePosture.access_group_context.total_members} members` : '' },
            { label: 'MCP Servers', value: orgIdentity.mcp_context.servers.toLocaleString(), sub: `${orgIdentity.mcp_context.tool_calls_30d.toLocaleString()} calls` },
            { label: 'Telemetry', value: orgIdentity.telemetry_context.batches_30d.toLocaleString(), sub: `${orgIdentity.user_context.runs_30d.toLocaleString()} runs` },
          ].map((item) => (
            <div key={item.label} className="rounded-xl border border-slate-200 bg-white/90 px-3 py-2.5 dark:border-slate-700 dark:bg-slate-900/80">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">{item.label}</p>
                <p className="text-lg font-semibold tracking-tight text-slate-950 dark:text-slate-50">{item.value}</p>
              </div>
              <p className="mt-0.5 text-[10px] text-slate-500">{item.sub}</p>
            </div>
          ))}
        </div>
      )}
      {gatewayRuntime && (
        <div className="grid gap-2 md:grid-cols-4">
          {[
            { label: 'Providers', value: `${gatewayRuntime.provider_context.distinct_providers}`, sub: `${gatewayRuntime.provider_context.active_routes} routes` },
            { label: 'Gateway (30d)', value: gatewayRuntime.route_context.gateway_requests_30d.toLocaleString(), sub: `${gatewayRuntime.route_context.cache_hits_30d.toLocaleString()} cache hits` },
            { label: 'Guardrails', value: `${gatewayRuntime.guardrail_context.active_rules} rules`, sub: `${gatewayRuntime.guardrail_context.blocks_30d} blocks` },
            { label: 'Cache Savings', value: `$${num(gatewayRuntime.cache_context.savings_usd).toFixed(2)}`, sub: `${gatewayRuntime.cache_context.total_hits.toLocaleString()} hits` },
          ].map((item) => (
            <div key={item.label} className="rounded-xl border border-slate-200 bg-white/90 px-3 py-2.5 dark:border-slate-700 dark:bg-slate-900/80">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">{item.label}</p>
                <p className="text-lg font-semibold tracking-tight text-slate-950 dark:text-slate-50">{item.value}</p>
              </div>
              <p className="mt-0.5 text-[10px] text-slate-500">{item.sub}</p>
            </div>
          ))}
          <div className="md:col-span-4 flex flex-wrap gap-3 rounded-xl border border-violet-200 bg-violet-50/70 px-3 py-2 text-xs font-semibold text-violet-800 dark:border-violet-900/40 dark:bg-violet-950/20 dark:text-violet-100">
            <Link href="/provider-profiles" className="hover:underline">Providers</Link>
            <Link href="/gateway" className="hover:underline">Gateway</Link>
            <Link href="/guardrails" className="hover:underline">Guardrails</Link>
          </div>
        </div>
      )}
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

  const [governance, finops, orgIdentity, gatewayRuntime, scopePosture] = await Promise.all([
    getInvestigationGovernancePosture(session.apiKey, {
      from: searchParams.from ?? sevenDaysAgo,
      to: searchParams.to,
      access_group_id: accessGroupId,
      tag: searchParams.tag,
      tool_name: searchParams.tool_name,
      security_event_only: searchParams.security_event_only === 'true',
    }).catch(() => null),
    getInvestigationFinopsBudgetPosture(session.apiKey, {
      access_group_id: accessGroupId,
    }).catch(() => null),
    getInvestigationOrgIdentityPosture(session.apiKey).catch(() => null),
    getInvestigationGatewayRuntimePosture(session.apiKey, { access_group_id: accessGroupId }).catch(() => null),
    getOverviewScopePosture(session.apiKey).catch(() => null),
  ])

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
            <PostureCards
              governance={governance}
              finops={finops}
              orgIdentity={orgIdentity}
              gatewayRuntime={gatewayRuntime}
              scopePosture={scopePosture}
            />
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
