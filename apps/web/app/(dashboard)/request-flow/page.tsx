import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { ArrowRight, Expand, GitBranch, Layers3, Route as RouteIcon, Search, ShieldCheck } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getAccessGroupDashboard, getInvestigationFinopsBudgetPosture, getInvestigationGatewayRuntimePosture, getInvestigationGovernancePosture, getInvestigationOrgIdentityPosture, getOverviewScopePosture, getRunFlow } from '@/lib/api'
import RequestFlowSankey, {
  type RequestFlowDensity,
  type RequestFlowMetric,
  type RequestFlowMode,
  type RequestFlowScope,
} from '@/components/dashboard/RequestFlowSankey'
import ContextAccordion from './ContextAccordion'
import type { RunFlowResponse } from '@/types/api'
import { num } from '@/lib/utils'

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
  if (num(value) >= 1) return `$${num(value).toFixed(2)}`
  if (num(value) >= 0.001) return `$${num(value).toFixed(4)}`
  return `$${num(value).toFixed(6)}`
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
  const [governance, finops, orgIdentity, gatewayRuntime, scopePosture] = await Promise.all([
    getInvestigationGovernancePosture(session.apiKey, govParams).catch(() => null),
    getInvestigationFinopsBudgetPosture(session.apiKey, { access_group_id: accessGroupId }).catch(() => null),
    getInvestigationOrgIdentityPosture(session.apiKey).catch(() => null),
    getInvestigationGatewayRuntimePosture(session.apiKey, { access_group_id: accessGroupId }).catch(() => null),
    getOverviewScopePosture(session.apiKey).catch(() => null),
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

  const contextSections: { color: string; label: string; summary: string; links: { href: string; text: string }[] }[] = []
  if (governance) {
    contextSections.push({
      color: 'cyan',
      label: 'Governance',
      summary: `${governance.filtered_runs.toLocaleString()} scoped runs, ${governance.security.events.toLocaleString()} security events, ${governance.audit_log.governance_events.toLocaleString()} governance audit events.${scopePosture ? ` ${scopePosture.tool_context.pending_approvals} pending approvals, ${scopePosture.tool_context.capture_policies} capture policies.` : ''}`,
      links: [
        { href: '/tool-registry', text: 'Tool Registry' },
        { href: '/tool-policies', text: 'Tool Policies' },
        { href: '/approvals', text: 'Approvals' },
        { href: '/security', text: 'Security' },
        { href: '/alert-rules', text: 'Alert Rules' },
        { href: '/audit', text: 'Audit Log' },
        { href: '/governance-pack', text: 'Governance Pack' },
        { href: '/tags', text: 'Tags' },
      ],
    })
  }
  if (finops) {
    contextSections.push({
      color: 'emerald',
      label: 'Budget',
      summary: `${finops.budget_context.active_budgets} active budgets (${finops.budget_context.breach_count} in breach), ${money(finops.spend_context.total_spend_30d)} spent across ${finops.spend_context.total_runs_30d.toLocaleString()} runs, ${finops.billing_context.open_billing_periods} open billing periods.`,
      links: [
        { href: '/budgets', text: 'Budgets' },
        { href: '/budgets?view=detail', text: 'Budget Detail' },
        { href: '/budget-overrides', text: 'Budget Overrides' },
        { href: '/billing', text: 'Billing Periods' },
        { href: '/billing?view=detail', text: 'Billing Period Detail' },
        { href: '/chargeback', text: 'Chargeback' },
        { href: '/model-budgets', text: 'Model Budgets' },
      ],
    })
  }
  if (orgIdentity) {
    contextSections.push({
      color: 'blue',
      label: 'Org Identity',
      summary: `${orgIdentity.user_context.workspace_users} workspace users, ${orgIdentity.user_context.distinct_end_users_30d} distinct end users, ${orgIdentity.api_key_context.total_keys} API keys (${orgIdentity.api_key_context.active_keys} active), ${orgIdentity.mcp_context.servers} MCP servers.`,
      links: [
        { href: '/organization', text: 'Organization' },
        { href: '/users', text: 'Users' },
        { href: '/api-keys', text: 'API Keys' },
        { href: '/telemetry', text: 'Telemetry' },
        { href: '/mcp-registry', text: 'MCP Registry' },
      ],
    })
  }
  if (gatewayRuntime) {
    contextSections.push({
      color: 'violet',
      label: 'Gateway Runtime',
      summary: `${gatewayRuntime.provider_context.distinct_providers} providers, ${gatewayRuntime.provider_context.active_routes} active routes, ${gatewayRuntime.route_context.gateway_requests_30d.toLocaleString()} gateway requests (30d). ${gatewayRuntime.guardrail_context.active_rules} guardrail rules (${gatewayRuntime.guardrail_context.blocks_30d} blocks). ${gatewayRuntime.cache_context.total_hits.toLocaleString()} cache hits, $${num(gatewayRuntime.cache_context.savings_usd).toFixed(2)} saved.`,
      links: [
        { href: '/provider-profiles', text: 'Provider Profiles' },
        { href: '/gateway', text: 'Gateway Routes' },
        { href: '/guardrails', text: 'Guardrails' },
        { href: '/cache-config', text: 'Response Cache' },
        { href: '/rate-limits', text: 'Rate Limits' },
      ],
    })
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">
            AI Request Flow
          </h1>
          <p className="mt-0.5 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
            Follow AI traffic from request to intent, model, route, provider, outcome, and cost. Click any flow line to inspect.
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Link
            href={`/analytics?scope=${scope}&view=overview${accessGroupId ? `&access_group_id=${encodeURIComponent(accessGroupId)}` : ''}`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-blue-500 dark:hover:bg-blue-950/40 dark:hover:text-blue-300"
          >
            Analytics <ArrowRight className="h-3 w-3" />
          </Link>
          <Link
            href={accessGroupId ? `/request-explorer?access_group_id=${encodeURIComponent(accessGroupId)}` : '/request-explorer'}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-blue-500 dark:hover:bg-blue-950/40 dark:hover:text-blue-300"
          >
            Explorer <Search className="h-3 w-3" />
          </Link>
          <Link
            href={`/request-flow/focus?mode=${mode}&metric=${metric}&scope=${scope}&density=presentation&top=${topN}${collapseSmall ? '' : '&collapse=0'}${accessGroupId ? `&access_group_id=${encodeURIComponent(accessGroupId)}` : ''}`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-blue-500 dark:hover:bg-blue-950/40 dark:hover:text-blue-300"
          >
            Focus <Expand className="h-3 w-3" />
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
            <div className="rounded-xl border border-blue-200 bg-blue-50/80 px-3 py-2 text-xs text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-100">
              Filtered to <span className="font-semibold">{accessGroup.name}</span> access group.
            </div>
          )}

          {/* Compact inline stats */}
          <div className="flex flex-wrap gap-3">
            {[
              { label: 'Runs', value: items.length.toLocaleString(), icon: GitBranch },
              { label: 'Intents', value: uniqueIntents.toLocaleString(), icon: Layers3 },
              { label: 'Models', value: uniqueModels.toLocaleString(), icon: RouteIcon },
              { label: 'Success', value: pct(succeeded, items.length), icon: ShieldCheck },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white/80 px-3 py-2 shadow-sm dark:border-slate-800 dark:bg-slate-950/45">
                <Icon className="h-3.5 w-3.5 text-teal-600 dark:text-teal-300" />
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</span>
                <span className="text-sm font-semibold text-slate-950 dark:text-white">{value}</span>
              </div>
            ))}
          </div>

          {/* HERO: Request Flow Sankey */}
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

          {/* Collapsible context sections */}
          {contextSections.length > 0 && (
            <ContextAccordion sections={contextSections} />
          )}

          {/* Compact bottom cards */}
          <div className="grid gap-3 lg:grid-cols-3">
            <div className="rounded-xl border border-slate-200 bg-white/80 px-4 py-3 shadow-sm dark:border-slate-800 dark:bg-slate-950/45">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 dark:text-slate-500">Analysis Flow</p>
              <p className="mt-1 text-sm font-semibold text-slate-950 dark:text-white">Start broad, drill into evidence</p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                <Link href={`/analytics?scope=${scope}&view=overview${accessGroupId ? `&access_group_id=${encodeURIComponent(accessGroupId)}` : ''}`} className="font-medium text-blue-600 hover:underline dark:text-blue-400">Overview</Link> for scope health, <Link href="/request-flow" className="font-medium text-blue-600 hover:underline dark:text-blue-400">Flow</Link> for routing causality, <Link href={accessGroupId ? `/request-explorer?access_group_id=${encodeURIComponent(accessGroupId)}` : '/request-explorer'} className="font-medium text-blue-600 hover:underline dark:text-blue-400">Explorer</Link> for exact runs.
              </p>
            </div>
            <Link
              href={accessGroupId ? `/request-explorer?access_group_id=${encodeURIComponent(accessGroupId)}` : '/request-explorer'}
              className="rounded-xl border border-slate-200 bg-white/80 px-4 py-3 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/70 dark:border-slate-800 dark:bg-slate-950/45 dark:hover:border-blue-400 dark:hover:bg-slate-900"
            >
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 dark:text-slate-500">Drill-in</p>
              <p className="mt-1 text-sm font-semibold text-slate-950 dark:text-white">Open Request Explorer</p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Filter requests behind suspicious edges, inspect run detail.
              </p>
            </Link>
            <Link
              href={`/request-flow/focus?mode=${mode}&metric=${metric}&scope=${scope}&density=presentation&top=${topN}${collapseSmall ? '' : '&collapse=0'}${accessGroupId ? `&access_group_id=${encodeURIComponent(accessGroupId)}` : ''}`}
              className="rounded-xl border border-slate-200 bg-white/80 px-4 py-3 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/70 dark:border-slate-800 dark:bg-slate-950/45 dark:hover:border-blue-400 dark:hover:bg-slate-900"
            >
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 dark:text-slate-500">Presentation</p>
              <p className="mt-1 text-sm font-semibold text-slate-950 dark:text-white">Launch Focus Mode</p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Larger canvas for demos and incident review.
              </p>
            </Link>
          </div>

          <p className="text-xs text-slate-400 dark:text-slate-500">
            <span className="font-medium">Scope:</span> Workspace access = workspace scope; org admin = org scope; platform admin = platform scope.
          </p>
        </>
      )}
    </div>
  )
}
