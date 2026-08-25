import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { ArrowRight, Expand, GitBranch, Layers3, Route as RouteIcon, Search, ShieldCheck } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getAccessGroupDashboard, getInvestigationFinopsBudgetPosture, getInvestigationGatewayRuntimePosture, getInvestigationGovernancePosture, getInvestigationOrgIdentityPosture, getRunFlow } from '@/lib/api'
import RequestFlowSankey, {
  type RequestFlowDensity,
  type RequestFlowMetric,
  type RequestFlowMode,
  type RequestFlowScope,
} from '@/components/dashboard/RequestFlowSankey'
import type { RunFlowResponse } from '@/types/api'

interface PageProps {
  searchParams: {
    mode?: string
    metric?: string
    scope?: string
    density?: string
    top?: string
    collapse?: string
    access_group_id?: string
    tag?: string
    tool_name?: string
    security_event_only?: string
    end_user_id?: string
    api_key_id?: string
  }
}

const flowModes: RequestFlowMode[] = [
  'request-intent-model-result',
  'user-intent-model',
  'prompt-skill-agent-model-tool-result',
  'request-route-provider-outcome',
  'workspace-app-agent-model-cost',
]

const flowMetrics: RequestFlowMetric[] = ['requests', 'cost', 'tokens', 'savings']
const flowScopes: RequestFlowScope[] = ['workspace', 'org', 'platform']
const flowDensities: RequestFlowDensity[] = ['compact', 'comfortable', 'presentation']

function parseMode(value: string | undefined): RequestFlowMode {
  if (value === 'team-app-agent-model-cost') return 'workspace-app-agent-model-cost'
  return flowModes.includes(value as RequestFlowMode) ? (value as RequestFlowMode) : 'request-intent-model-result'
}

function parseMetric(value: string | undefined): RequestFlowMetric {
  return flowMetrics.includes(value as RequestFlowMetric) ? (value as RequestFlowMetric) : 'requests'
}

function parseScope(value: string | undefined): RequestFlowScope {
  return flowScopes.includes(value as RequestFlowScope) ? (value as RequestFlowScope) : 'workspace'
}

function parseDensity(value: string | undefined): RequestFlowDensity {
  return flowDensities.includes(value as RequestFlowDensity) ? (value as RequestFlowDensity) : 'comfortable'
}

function parseTopN(value: string | undefined) {
  const parsed = Number.parseInt(value ?? '', 10)
  return Number.isFinite(parsed) ? parsed : 8
}

function pct(value: number, total: number) {
  if (total <= 0) return '0%'
  return `${Math.round((value / total) * 100)}%`
}

function money(value: number) {
  if (value >= 1) return `$${value.toFixed(2)}`
  if (value >= 0.001) return `$${value.toFixed(4)}`
  return `$${value.toFixed(6)}`
}

export default async function RequestFlowPage({ searchParams }: PageProps) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const mode = parseMode(searchParams.mode)
  const metric = parseMetric(searchParams.metric)
  const density = parseDensity(searchParams.density)
  const topN = parseTopN(searchParams.top)
  const collapseSmall = searchParams.collapse !== '0'
  const accessGroupId = searchParams.access_group_id
  const govTag = searchParams.tag
  const govToolName = searchParams.tool_name
  const govSecurityOnly = searchParams.security_event_only === 'true'
  const endUserId = searchParams.end_user_id
  const apiKeyId = searchParams.api_key_id
  const requestedScope = accessGroupId ? 'workspace' : parseScope(searchParams.scope)
  let scope = requestedScope
  const accessGroupDashboard = accessGroupId
    ? await getAccessGroupDashboard(session.apiKey, accessGroupId).catch(() => null)
    : null
  const accessGroup = accessGroupDashboard?.groups[0] ?? null
  const govParams = { access_group_id: accessGroupId, tag: govTag, tool_name: govToolName, security_event_only: govSecurityOnly || undefined }
  const [governance, finops, orgIdentity, gatewayRuntime] = await Promise.all([
    getInvestigationGovernancePosture(session.apiKey, govParams).catch(() => null),
    getInvestigationFinopsBudgetPosture(session.apiKey, { access_group_id: accessGroupId }).catch(() => null),
    getInvestigationOrgIdentityPosture(session.apiKey).catch(() => null),
    getInvestigationGatewayRuntimePosture(session.apiKey, { access_group_id: accessGroupId }).catch(() => null),
  ])
  let flow: RunFlowResponse
  try {
    flow = await getRunFlow(session.apiKey, { scope, mode, metric, limit: 500, access_group_id: accessGroupId, tag: govTag, tool_name: govToolName, security_event_only: govSecurityOnly || undefined, api_key_id: apiKeyId, end_user_id: endUserId })
  } catch {
    scope = 'workspace'
    flow = await getRunFlow(session.apiKey, { scope, mode, metric, limit: 500, access_group_id: accessGroupId, tag: govTag, tool_name: govToolName, security_event_only: govSecurityOnly || undefined, api_key_id: apiKeyId, end_user_id: endUserId })
  }
  const items = flow.items
  const uniqueIntents = new Set(items.map((run) => run.feature_tag || 'General / Untagged')).size
  const uniqueModels = new Set(items.map((run) => run.primary_model || 'Model Unknown')).size
  const succeeded = items.filter((run) => run.success).length

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">
            AI Request Flow
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
            Follow AI traffic from incoming request to intent, skill, agent, model, tool, route, provider, outcome, and cost. Click any flow line to inspect the matching requests.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/analytics?scope=${scope}&view=overview${accessGroupId ? `&access_group_id=${encodeURIComponent(accessGroupId)}` : ''}`}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-300 dark:bg-white dark:text-slate-700 dark:hover:border-blue-300 dark:hover:text-blue-700"
          >
            Analytics Overview <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href={accessGroupId ? `/request-explorer?access_group_id=${encodeURIComponent(accessGroupId)}` : '/request-explorer'}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-300 dark:bg-white dark:text-slate-700 dark:hover:border-blue-300 dark:hover:text-blue-700"
          >
            Request Explorer <Search className="h-4 w-4" />
          </Link>
          <Link
            href={`/request-flow/focus?mode=${mode}&metric=${metric}&scope=${scope}&density=presentation&top=${topN}${collapseSmall ? '' : '&collapse=0'}${accessGroupId ? `&access_group_id=${encodeURIComponent(accessGroupId)}` : ''}`}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-300 dark:bg-white dark:text-slate-700 dark:hover:border-blue-300 dark:hover:text-blue-700"
          >
            Focus Mode <Expand className="h-4 w-4" />
          </Link>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50/60 px-6 py-20 text-center dark:border-slate-700 dark:bg-slate-950/30">
          <RouteIcon className="h-10 w-10 text-slate-400 dark:text-slate-500" />
          <h2 className="mt-4 text-lg font-semibold text-slate-700 dark:text-slate-300">No request flow data yet</h2>
          <p className="mt-1.5 max-w-md text-sm text-slate-500 dark:text-slate-400">
            Send AI requests through the RunLedger gateway to see traffic flow visualized here. The Sankey diagram will show how requests route through intents, models, and outcomes.
          </p>
        </div>
      ) : (
        <>
          {accessGroup && (
            <div className="rounded-2xl border border-blue-200 bg-blue-50/80 px-4 py-3 text-sm text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-100">
              Request Flow is filtered to the <span className="font-semibold">{accessGroup.name}</span> access group.
            </div>
          )}
          <div className="grid gap-4 md:grid-cols-4">
            {[
              { label: 'Runs sampled', value: items.length.toLocaleString(), icon: GitBranch },
              { label: 'Intent groups', value: uniqueIntents.toLocaleString(), icon: Layers3 },
              { label: 'Models observed', value: uniqueModels.toLocaleString(), icon: RouteIcon },
              { label: 'Success rate', value: pct(succeeded, items.length), icon: ShieldCheck },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950/45">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{label}</p>
                  <Icon className="h-4 w-4 text-teal-600 dark:text-teal-300" />
                </div>
                <p className="mt-3 text-2xl font-semibold text-slate-950 dark:text-white">{value}</p>
              </div>
            ))}
          </div>

          {governance && (
            <div className="rounded-2xl border border-cyan-200 bg-cyan-50/70 p-5 shadow-sm dark:border-cyan-900/40 dark:bg-cyan-950/20">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700 dark:text-cyan-200">Governance Context</p>
                  <h2 className="mt-2 text-lg font-semibold text-slate-950 dark:text-white">Runtime policy evidence around this investigation scope</h2>
                  <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                    {governance.filtered_runs.toLocaleString()} scoped runs, {governance.security.events.toLocaleString()} security events, and {governance.audit_log.governance_events.toLocaleString()} governance audit events are available for drill-through.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 text-xs font-semibold text-cyan-800 dark:text-cyan-100">
                  <Link href="/tool-registry" className="hover:underline">Tool Registry</Link>
                  <Link href="/tool-policies" className="hover:underline">Tool Policies</Link>
                  <Link href="/security" className="hover:underline">Security</Link>
                  <Link href="/alert-rules" className="hover:underline">Alert Rules</Link>
                  <Link href="/audit" className="hover:underline">Audit Log</Link>
                  <Link href="/governance-pack" className="hover:underline">Governance Pack</Link>
                  <Link href="/tags" className="hover:underline">Tags</Link>
                </div>
              </div>
            </div>
          )}

          {finops && (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-5 shadow-sm dark:border-emerald-900/40 dark:bg-emerald-950/20">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-200">Budget Context</p>
                  <h2 className="mt-2 text-lg font-semibold text-slate-950 dark:text-white">FinOps budget posture across this investigation scope</h2>
                  <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                    {finops.budget_context.active_budgets} active budgets ({finops.budget_context.breach_count} in breach), {money(finops.spend_context.total_spend_30d)} spent across {finops.spend_context.total_runs_30d.toLocaleString()} runs, {finops.billing_context.open_billing_periods} open billing periods.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 text-xs font-semibold text-emerald-800 dark:text-emerald-100">
                  <Link href="/budgets" className="hover:underline">Budgets</Link>
                  <Link href="/billing" className="hover:underline">Billing Periods</Link>
                  <Link href="/chargeback" className="hover:underline">Chargeback</Link>
                  <Link href="/model-budgets" className="hover:underline">Model Budgets</Link>
                </div>
              </div>
            </div>
          )}

          {orgIdentity && (
            <div className="rounded-2xl border border-blue-200 bg-blue-50/70 p-5 shadow-sm dark:border-blue-900/40 dark:bg-blue-950/20">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700 dark:text-blue-200">Org Identity Context</p>
                  <h2 className="mt-2 text-lg font-semibold text-slate-950 dark:text-white">Organization identity posture across this investigation scope</h2>
                  <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                    {orgIdentity.user_context.workspace_users} workspace users, {orgIdentity.user_context.distinct_end_users_30d} distinct end users, {orgIdentity.api_key_context.total_keys} API keys ({orgIdentity.api_key_context.active_keys} active), {orgIdentity.mcp_context.servers} MCP servers.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 text-xs font-semibold text-blue-800 dark:text-blue-100">
                  <Link href="/organization" className="hover:underline">Organization</Link>
                  <Link href="/users" className="hover:underline">Users</Link>
                  <Link href="/api-keys" className="hover:underline">API Keys</Link>
                  <Link href="/telemetry" className="hover:underline">Telemetry</Link>
                  <Link href="/mcp-registry" className="hover:underline">MCP Registry</Link>
                </div>
              </div>
            </div>
          )}

          {gatewayRuntime && (
            <div className="rounded-2xl border border-violet-200 bg-violet-50/70 p-5 shadow-sm dark:border-violet-900/40 dark:bg-violet-950/20">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-700 dark:text-violet-200">Gateway Runtime Context</p>
                  <h2 className="mt-2 text-lg font-semibold text-slate-950 dark:text-white">Provider routing, guardrails, cache, and rate limits across this scope</h2>
                  <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                    {gatewayRuntime.provider_context.distinct_providers} providers, {gatewayRuntime.provider_context.active_routes} active routes, {gatewayRuntime.route_context.gateway_requests_30d.toLocaleString()} gateway requests (30d). {gatewayRuntime.guardrail_context.active_rules} guardrail rules ({gatewayRuntime.guardrail_context.blocks_30d} blocks). {gatewayRuntime.cache_context.total_hits.toLocaleString()} cache hits, ${gatewayRuntime.cache_context.savings_usd.toFixed(2)} saved.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 text-xs font-semibold text-violet-800 dark:text-violet-100">
                  <Link href="/provider-profiles" className="hover:underline">Provider Profiles</Link>
                  <Link href="/gateway" className="hover:underline">Gateway Routes</Link>
                  <Link href="/guardrails" className="hover:underline">Guardrails</Link>
                  <Link href="/cache-config" className="hover:underline">Response Cache</Link>
                  <Link href="/rate-limits" className="hover:underline">Rate Limits</Link>
                </div>
              </div>
            </div>
          )}

          <RequestFlowSankey
            flow={flow}
            scope={scope}
            mode={mode}
            metric={metric}
            density={density}
            topN={topN}
            collapseSmall={collapseSmall}
            accessGroupId={accessGroupId}
          />

          <div className="grid gap-4 lg:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950/45">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Request Analysis Flow</p>
              <h2 className="mt-2 text-lg font-semibold text-slate-950 dark:text-white">Start broad, then drill into evidence</h2>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                Use Analytics Overview for scope health, Request Flow for routing causality, and Request Explorer when you need the exact run, prompt path, and gateway evidence.
              </p>
            </div>
            <Link
              href={accessGroupId ? `/request-explorer?access_group_id=${encodeURIComponent(accessGroupId)}` : '/request-explorer'}
              className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/70 dark:border-slate-800 dark:bg-slate-950/45 dark:hover:border-blue-400 dark:hover:bg-slate-900"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Drill-in</p>
              <h2 className="mt-2 text-lg font-semibold text-slate-950 dark:text-white">Open Request Explorer</h2>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                Filter the exact requests behind a suspicious edge, inspect run detail, and correlate route, model, cache, and outcome behavior.
              </p>
            </Link>
            <Link
              href={`/request-flow/focus?mode=${mode}&metric=${metric}&scope=${scope}&density=presentation&top=${topN}${collapseSmall ? '' : '&collapse=0'}${accessGroupId ? `&access_group_id=${encodeURIComponent(accessGroupId)}` : ''}`}
              className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/70 dark:border-slate-800 dark:bg-slate-950/45 dark:hover:border-blue-400 dark:hover:bg-slate-900"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Presentation Mode</p>
              <h2 className="mt-2 text-lg font-semibold text-slate-950 dark:text-white">Launch Focus Mode</h2>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                Expand the same flow into a larger canvas for demos, incident review, and dense route-to-outcome debugging without changing the underlying dataset.
              </p>
            </Link>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-5 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-950/35 dark:text-slate-300">
            <p className="font-semibold text-slate-950 dark:text-white">Scope note</p>
            <p className="mt-1">
              This page uses the backend flow aggregate API. Workspace scope is available to workspace access; org scope requires org admin; platform scope requires platform admin.
            </p>
          </div>
        </>
      )}
    </div>
  )
}
