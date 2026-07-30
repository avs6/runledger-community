'use client'

import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  AlertCircle,
  Bell,
  Bot,
  CheckCircle2,
  CircleDashed,
  Cloud,
  Code2,
  DatabaseBackup,
  GitBranch,
  KeyRound,
  Mail,
  MessageSquare,
  PlugZap,
  RadioTower,
  RefreshCw,
  Server,
  ShieldCheck,
  Workflow,
} from 'lucide-react'
import { toast } from 'sonner'
import { useRole } from '@/components/rbac/useRole'
import {
  getGatewayStats,
  getOpsFeatureStatus,
  getOtlpStats,
  createKafkaExportConfig,
  deleteKafkaExportConfig,
  listApiKeys,
  listGatewayRoutes,
  listKafkaExportConfigs,
  listKafkaExportDeliveries,
  testKafkaExportConfig,
  testSlackWebhook,
  updateKafkaExportConfig,
} from '@/lib/api'
import type { KafkaExportConfig, KafkaExportDelivery, KafkaEventType, KafkaSecurityProtocol } from '@/types/api'

const inputCls =
  'rounded-lg border border-slate-300 bg-white/85 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 dark:border-slate-300 dark:bg-white/85 dark:text-slate-900 dark:placeholder:text-slate-500'

const kafkaEvents: KafkaEventType[] = [
  'run.completed',
  'run.failed',
  'gateway.request.completed',
  'gateway.request.rejected',
  'budget.breached',
  'alert.fired',
  'optimization.applied',
  'mcp.tool.called',
  'mcp.tool.blocked',
]

type IntegrationStatus = 'available' | 'published' | 'planned' | 'docs' | 'coming-soon'
type HealthStatus = 'healthy' | 'setup' | 'disabled' | 'planned' | 'unknown'

type IntegrationCard = {
  name: string
  description: string
  status: IntegrationStatus
  icon: React.ComponentType<{ className?: string }>
  href?: string
  actionLabel?: string
  details: string[]
  brand?: {
    mark: string
    name: string
    className: string
  }
}

type HealthItem = {
  name: string
  description: string
  status: HealthStatus
  detail: string
  href?: string
  actionLabel?: string
  icon: React.ComponentType<{ className?: string }>
}

const statusStyles: Record<IntegrationStatus, string> = {
  available: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-200 dark:bg-emerald-50 dark:text-emerald-700',
  published: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-200 dark:bg-blue-50 dark:text-blue-700',
  planned: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-200 dark:bg-amber-50 dark:text-amber-700',
  docs: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-200 dark:bg-blue-50 dark:text-blue-700',
  'coming-soon': 'border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-200 dark:bg-slate-100 dark:text-slate-600',
}

const statusLabel: Record<IntegrationStatus, string> = {
  available: 'Available',
  published: 'Published skill',
  planned: 'Planned',
  docs: 'Guide',
  'coming-soon': 'Coming soon',
}

const healthStyles: Record<HealthStatus, { badge: string; icon: string; label: string }> = {
  healthy: {
    badge: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    icon: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    label: 'Healthy',
  },
  setup: {
    badge: 'border-amber-200 bg-amber-50 text-amber-700',
    icon: 'bg-amber-50 text-amber-700 ring-amber-200',
    label: 'Needs setup',
  },
  disabled: {
    badge: 'border-slate-200 bg-slate-100 text-slate-600',
    icon: 'bg-slate-100 text-slate-600 ring-slate-200',
    label: 'Disabled',
  },
  planned: {
    badge: 'border-blue-200 bg-blue-50 text-blue-700',
    icon: 'bg-blue-50 text-blue-700 ring-blue-200',
    label: 'Planned',
  },
  unknown: {
    badge: 'border-slate-200 bg-white text-slate-500',
    icon: 'bg-white text-slate-500 ring-slate-200',
    label: 'Unknown',
  },
}

const integrationGroups: { title: string; description: string; cards: IntegrationCard[] }[] = [
  {
    title: 'Published Agent Skills',
    description: 'Installable RunLedger skills that teach popular agent tools how to connect, check budget, and report outcomes.',
    cards: [
      {
        name: 'Claude Desktop',
        description: 'Adds Claude MCP setup, CLAUDE.md defaults, budget checks, and outcome logging for Claude-driven work.',
        status: 'published',
        icon: Bot,
        href: '/mcp',
        actionLabel: 'Open MCP setup',
        brand: {
          mark: 'C',
          name: 'Claude',
          className: 'border-orange-200 bg-orange-50 text-orange-700',
        },
        details: ['runledger-connect-claude', 'MCP config', 'CLAUDE.md'],
      },
      {
        name: 'OpenAI Codex',
        description: 'Adds AGENTS.md guidance and Codex hooks for sessions, subagents, tool use, and task outcomes.',
        status: 'published',
        icon: Code2,
        href: '/mcp',
        actionLabel: 'Open MCP setup',
        brand: {
          mark: 'OA',
          name: 'OpenAI',
          className: 'border-emerald-200 bg-emerald-50 text-emerald-700',
        },
        details: ['runledger-connect-codex', 'AGENTS.md', 'Codex hooks'],
      },
      {
        name: 'Cursor IDE',
        description: 'Adds Cursor rules and MCP setup so coding-agent usage can be tracked by repo, user, and workspace.',
        status: 'published',
        icon: Workflow,
        href: '/mcp',
        actionLabel: 'Open MCP setup',
        brand: {
          mark: 'Cu',
          name: 'Cursor',
          className: 'border-slate-300 bg-slate-100 text-slate-800',
        },
        details: ['runledger-connect-cursor', 'Cursor rules', 'MCP tools'],
      },
      {
        name: 'Devin',
        description: 'Adds a Devin bridge pattern for autonomous task lifecycle logging, budget checks, and outcomes.',
        status: 'published',
        icon: Bot,
        href: '/integrations',
        actionLabel: 'View bridge',
        brand: {
          mark: 'D',
          name: 'Devin',
          className: 'border-blue-200 bg-blue-50 text-blue-700',
        },
        details: ['runledger-connect-devin', 'API bridge', 'Task outcomes'],
      },
      {
        name: 'Windsurf',
        description: 'Documents Cascade hooks, MCP setup, and wrapper telemetry for Windsurf/Cascade workflows.',
        status: 'docs',
        icon: Workflow,
        href: '/integrations',
        actionLabel: 'View guide',
        brand: {
          mark: 'W',
          name: 'Windsurf',
          className: 'border-cyan-200 bg-cyan-50 text-cyan-700',
        },
        details: ['Integration guide', 'Cascade hooks', 'MCP setup'],
      },
    ],
  },
  {
    title: 'Agent Control Plane',
    description: 'Connect desktop IDEs, hosted agents, and MCP-aware tools to RunLedger.',
    cards: [
      {
        name: 'MCP Server',
        description: 'Expose RunLedger budget, policy, route recommendation, and outcome tools to agents.',
        status: 'available',
        icon: PlugZap,
        href: '/mcp',
        details: ['HTTP MCP endpoint', 'Tool filtering path', 'Agent budget checks'],
      },
      {
        name: 'Claude Desktop / Claude Code',
        description: 'Generate Claude instructions and MCP config so Claude can record agent work.',
        status: 'available',
        icon: Bot,
        details: ['Published skill', 'stdio/HTTP MCP bridge', 'Outcome capture'],
      },
      {
        name: 'OpenAI Codex',
        description: 'Add AGENTS.md and Codex hooks for sessions, subagents, tool use, and outcomes.',
        status: 'available',
        icon: Code2,
        details: ['Published skill', 'Codex hooks', 'Subagent telemetry'],
      },
      {
        name: 'Cursor / Windsurf / Devin',
        description: 'Provide publishable setup skills for IDE agents and hosted autonomous sessions.',
        status: 'available',
        icon: Workflow,
        details: ['Cursor skill', 'Windsurf docs', 'Devin skill'],
      },
    ],
  },
  {
    title: 'Notifications And Collaboration',
    description: 'Send operational alerts, budget events, lifecycle notifications, and approvals.',
    cards: [
      {
        name: 'Slack Webhook',
        description: 'Test incoming webhook connectivity for budget notifications and alerts.',
        status: 'available',
        icon: MessageSquare,
        details: ['Budget notifications', 'Alert Rules', 'Webhook smoke test'],
      },
      {
        name: 'Email / SMTP',
        description: 'Send welcome, invite, reset, backup, compliance, and budget alert emails.',
        status: 'planned',
        icon: Mail,
        details: ['Mailpit local', 'Google SMTP', 'SES/SendGrid/Postmark'],
      },
      {
        name: 'Teams And Webhooks',
        description: 'Deliver alerts to Microsoft Teams or any customer-owned webhook endpoint.',
        status: 'coming-soon',
        icon: Bell,
        details: ['Teams cards', 'Generic webhook', 'Approval workflows'],
      },
      {
        name: 'GitHub Actions',
        description: 'Record CI agent runs, model-assisted changes, and test outcomes from pipelines.',
        status: 'planned',
        icon: GitBranch,
        details: ['CI wrapper', 'PR metadata', 'Test outcome spans'],
      },
    ],
  },
  {
    title: 'Telemetry And AI Frameworks',
    description: 'Stream traces, metrics, logs, model calls, and framework spans into RunLedger.',
    cards: [
      {
        name: 'OTLP Collector',
        description: 'Ingest traces today and expand into metrics, logs, span metrics, and AI attributes.',
        status: 'available',
        icon: RadioTower,
        href: '/otlp',
        details: ['Traces', 'Metrics roadmap', 'User-to-model attribution'],
      },
      {
        name: 'OpenInference',
        description: 'Capture LLM spans from frameworks that emit OpenInference-compatible telemetry.',
        status: 'docs',
        icon: ShieldCheck,
        details: ['LLM semantic spans', 'Prompt/tool traces', 'Framework adapters'],
      },
      {
        name: 'LiteLLM / Open WebUI / OpenHands',
        description: 'Route local AI stack traffic through Gateway and export telemetry out-of-band.',
        status: 'planned',
        icon: Server,
        details: ['Gateway routing', 'Provider pricing', 'Optimization labs'],
      },
      {
        name: 'LangGraph / CrewAI / AutoGen',
        description: 'Use SDK wrappers and OTEL spans to track agent graphs and tool chains.',
        status: 'planned',
        icon: Bot,
        details: ['Run spans', 'Tool calls', 'Agent dependency graph'],
      },
      {
        name: 'Kafka / Redpanda Streaming',
        description: 'Export RunLedger events into customer Kafka-compatible streams in real time.',
        status: 'available',
        icon: RadioTower,
        href: '/integrations',
        actionLabel: 'Configure Kafka',
        details: ['Event export', 'Delivery log', 'Dead-letter topics'],
      },
    ],
  },
  {
    title: 'Infrastructure And Data',
    description: 'Connect the supporting services needed for real customer deployments.',
    cards: [
      {
        name: 'API Keys',
        description: 'Create scoped workspace keys for Gateway, MCP, SDK, and OTLP ingestion.',
        status: 'available',
        icon: KeyRound,
        href: '/api-keys',
        details: ['Workspace scoped', 'Gateway auth', 'MCP/OTLP keys'],
      },
      {
        name: 'S3 / MinIO Backup',
        description: 'Store backups, snapshots, exports, and trace archives in S3-compatible storage.',
        status: 'planned',
        icon: DatabaseBackup,
        details: ['Backup restore', 'Snapshots', 'Compliance exports'],
      },
      {
        name: 'Local Firebase Emulator',
        description: 'Optional local emulator suite for auth, storage, pub/sub, and integration demos.',
        status: 'coming-soon',
        icon: Cloud,
        details: ['Local dev parity', 'Auth experiments', 'Pub/Sub demos'],
      },
      {
        name: 'Generic REST Webhook',
        description: 'Receive external events from workflow tools that cannot use SDK, MCP, or OTLP.',
        status: 'planned',
        icon: PlugZap,
        details: ['Signed ingestion', 'Event mapping', 'Smoke test'],
      },
    ],
  },
]

function StatusBadge({ status }: { status: IntegrationStatus }) {
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${statusStyles[status]}`}>
      {statusLabel[status]}
    </span>
  )
}

function HealthBadge({ status }: { status: HealthStatus }) {
  const style = healthStyles[status]
  return <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${style.badge}`}>{style.label}</span>
}

function HealthIcon({ status, icon: Icon }: { status: HealthStatus; icon: React.ComponentType<{ className?: string }> }) {
  return (
    <div className={`rounded-xl p-2 ring-1 ${healthStyles[status].icon}`}>
      <Icon className="h-4 w-4" />
    </div>
  )
}

function HealthCard({ item }: { item: HealthItem }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-300 dark:bg-white/90">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <HealthIcon status={item.status} icon={item.icon} />
          <div>
            <h3 className="text-sm font-semibold text-slate-950">{item.name}</h3>
            <p className="mt-0.5 text-xs text-slate-500">{item.detail}</p>
          </div>
        </div>
        <HealthBadge status={item.status} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-600">{item.description}</p>
      {item.href && (
        <Link
          href={item.href}
          className="mt-4 inline-flex items-center rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
        >
          {item.actionLabel ?? 'Open'}
        </Link>
      )}
    </div>
  )
}

function IntegrationCardView({ card }: { card: IntegrationCard }) {
  const Icon = card.icon
  return (
    <div className="group rounded-2xl border border-slate-200 bg-white/85 p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300 hover:bg-white hover:shadow-lg dark:border-slate-300 dark:bg-white/85 dark:hover:border-blue-300">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          {card.brand ? (
            <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border text-sm font-black tracking-[-0.04em] shadow-sm ${card.brand.className}`}>
              {card.brand.mark}
            </div>
          ) : (
            <div className="rounded-xl bg-blue-50 p-2 text-blue-700 ring-1 ring-blue-100 dark:bg-blue-50 dark:text-blue-700">
              <Icon className="h-4 w-4" />
            </div>
          )}
          <div>
            {card.brand && <p className="mb-0.5 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">{card.brand.name}</p>}
            <h3 className="text-sm font-semibold text-slate-950 dark:text-slate-950">{card.name}</h3>
            <StatusBadge status={card.status} />
          </div>
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-600">{card.description}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {card.details.map((detail) => (
          <span key={detail} className="rounded-full bg-slate-100 px-2 py-1 text-[11px] text-slate-600 dark:bg-slate-100 dark:text-slate-600">
            {detail}
          </span>
        ))}
      </div>
      <div className="mt-4">
        {card.href ? (
          <Link href={card.href} className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-300 dark:text-slate-700 dark:hover:border-blue-300 dark:hover:text-blue-700">
            {card.actionLabel ?? 'Open'}
          </Link>
        ) : (
          <button disabled className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-400 dark:border-slate-200 dark:bg-slate-50 dark:text-slate-400">
            Configure soon
          </button>
        )}
      </div>
    </div>
  )
}

function fulfilledValue<T>(result: PromiseSettledResult<T>): T | null {
  return result.status === 'fulfilled' ? result.value : null
}

export default function IntegrationsPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { canManageOrgSettings } = useRole()

  const [slackWebhookUrl, setSlackWebhookUrl] = useState('')
  const [slackTestResult, setSlackTestResult] = useState<{ ok: boolean; error: string | null } | null>(null)
  const [testingSlack, setTestingSlack] = useState(false)
  const [healthItems, setHealthItems] = useState<HealthItem[]>([])
  const [healthLoading, setHealthLoading] = useState(false)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [kafkaConfigs, setKafkaConfigs] = useState<KafkaExportConfig[]>([])
  const [kafkaDeliveries, setKafkaDeliveries] = useState<Record<string, KafkaExportDelivery[]>>({})
  const [kafkaBusy, setKafkaBusy] = useState(false)
  const [kafkaForm, setKafkaForm] = useState({
    label: 'Local Redpanda',
    bootstrap_servers: 'localhost:9092',
    topic_prefix: 'runledger.dev',
    security_protocol: 'PLAINTEXT' as KafkaSecurityProtocol,
    event_types: ['run.completed', 'run.failed', 'alert.fired', 'budget.breached'] as KafkaEventType[],
  })

  const loadHealth = useCallback(async () => {
    if (!apiKey) return
    setHealthLoading(true)
    setHealthError(null)
    try {
      const [apiKeysResult, routesResult, gatewayStatsResult, otlpStatsResult, opsStatusResult, kafkaConfigsResult] =
        await Promise.allSettled([
          listApiKeys(apiKey),
          listGatewayRoutes(apiKey, true),
          getGatewayStats(apiKey),
          getOtlpStats(apiKey),
          getOpsFeatureStatus(apiKey),
          listKafkaExportConfigs(apiKey),
        ])

      const apiKeys = fulfilledValue(apiKeysResult)
      const routes = fulfilledValue(routesResult)
      const gatewayStats = fulfilledValue(gatewayStatsResult)
      const otlpStats = fulfilledValue(otlpStatsResult)
      const opsStatus = fulfilledValue(opsStatusResult)
      const kafkaConfigs = fulfilledValue(kafkaConfigsResult)
      if (kafkaConfigs) {
        setKafkaConfigs(kafkaConfigs.items)
        const deliveryPairs = await Promise.all(
          kafkaConfigs.items.slice(0, 3).map(async (config) => {
            try {
              const deliveries = await listKafkaExportDeliveries(apiKey, config.id, 10)
              return [config.id, deliveries.items] as const
            } catch {
              return [config.id, []] as const
            }
          })
        )
        setKafkaDeliveries(Object.fromEntries(deliveryPairs))
      }

      const customerApiKeys = apiKeys?.filter((key) => !key.is_session) ?? []
      const activeRoutes = routes?.items.filter((route) => route.is_active) ?? []
      const otlpSpanCount = (otlpStats?.last_24h.spans ?? 0) + (otlpStats?.last_7d.spans ?? 0)
      const kafkaEnabled = kafkaConfigs?.items.filter((config) => config.enabled) ?? []
      const smtpReady = opsStatus ? opsStatus.email_enabled && opsStatus.smtp_configured : false
      const reportsReady = opsStatus ? opsStatus.email_reports_enabled && smtpReady : false

      setHealthItems([
        {
          name: 'API Keys',
          description: 'Workspace keys are the entry point for SDKs, Gateway traffic, OTLP, and MCP tooling.',
          status: customerApiKeys.length > 0 ? 'healthy' : 'setup',
          detail: apiKeys ? `${customerApiKeys.length} workspace key${customerApiKeys.length === 1 ? '' : 's'}` : 'Unable to verify',
          href: '/api-keys',
          actionLabel: customerApiKeys.length > 0 ? 'Manage keys' : 'Create key',
          icon: KeyRound,
        },
        {
          name: 'MCP',
          description: 'Agents can call RunLedger tools once a workspace key exists and the MCP endpoint is configured.',
          status: customerApiKeys.length > 0 ? 'healthy' : 'setup',
          detail: customerApiKeys.length > 0 ? 'Ready for agent config' : 'Needs workspace key',
          href: '/mcp',
          actionLabel: 'Open MCP',
          icon: PlugZap,
        },
        {
          name: 'Gateway',
          description: 'Inline control is available when active model routes exist or recent Gateway requests are flowing.',
          status: activeRoutes.length > 0 || (gatewayStats?.total_requests ?? 0) > 0 ? 'healthy' : 'setup',
          detail: routes ? `${activeRoutes.length} active route${activeRoutes.length === 1 ? '' : 's'}` : 'Unable to verify',
          href: '/gateway',
          actionLabel: activeRoutes.length > 0 ? 'Review routes' : 'Add route',
          icon: Server,
        },
        {
          name: 'OTLP',
          description: 'Out-of-band traces can be pushed by collectors and frameworks with workspace attribution.',
          status: otlpSpanCount > 0 ? 'healthy' : 'setup',
          detail: otlpStats ? `${otlpSpanCount} spans observed` : 'Unable to verify',
          href: '/otlp',
          actionLabel: 'Open OTLP',
          icon: RadioTower,
        },
        {
          name: 'Slack',
          description: 'Slack alerting is available through the webhook smoke test below and budget notification setup.',
          status: slackTestResult?.ok ? 'healthy' : 'setup',
          detail: slackTestResult?.ok ? 'Last test succeeded' : 'Test webhook below',
          icon: MessageSquare,
        },
        {
          name: 'Email Reports',
          description: 'Scheduled reports stay quiet until email delivery and scheduled reports are explicitly enabled.',
          status: reportsReady ? 'healthy' : opsStatus ? 'disabled' : 'unknown',
          detail: opsStatus ? (reportsReady ? 'Reports enabled' : 'Disabled by feature flag') : 'Unable to verify',
          href: '/settings',
          actionLabel: 'Open settings',
          icon: Mail,
        },
        {
          name: 'Backup',
          description: 'Product-managed backup controls are gated by the backend backup feature flag.',
          status: opsStatus?.backup_enabled ? 'healthy' : opsStatus ? 'disabled' : 'unknown',
          detail: opsStatus?.backup_enabled ? 'Backup enabled' : opsStatus ? 'Disabled by feature flag' : 'Unable to verify',
          href: '/settings',
          actionLabel: 'Open settings',
          icon: DatabaseBackup,
        },
        {
          name: 'Kafka Export',
          description: 'Kafka/Redpanda export is the next streaming path for run, alert, budget, and optimization events.',
          status: kafkaEnabled.length > 0 ? 'healthy' : kafkaConfigs ? 'setup' : 'planned',
          detail: kafkaConfigs ? `${kafkaEnabled.length} enabled export${kafkaEnabled.length === 1 ? '' : 's'}` : 'Configure after backend migration',
          icon: Activity,
        },
      ])
    } catch (err) {
      setHealthError(String(err))
    } finally {
      setHealthLoading(false)
    }
  }, [apiKey, slackTestResult?.ok])

  useEffect(() => {
    if (canManageOrgSettings) {
      void loadHealth()
    }
  }, [canManageOrgSettings, loadHealth])

  async function handleTestSlack(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !slackWebhookUrl.trim()) return
    setTestingSlack(true)
    setSlackTestResult(null)
    try {
      const result = await testSlackWebhook(apiKey, slackWebhookUrl.trim())
      setSlackTestResult(result)
      if (result.ok) {
        toast.success('Test message sent to Slack')
        void loadHealth()
      } else {
        toast.error(`Slack test failed: ${result.error}`)
      }
    } catch (err) {
      const msg = String(err)
      setSlackTestResult({ ok: false, error: msg })
      toast.error(`Slack test failed: ${msg}`)
    } finally {
      setTestingSlack(false)
    }
  }

  async function handleCreateKafka(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setKafkaBusy(true)
    try {
      await createKafkaExportConfig(apiKey, kafkaForm)
      toast.success('Kafka export config created')
      await loadHealth()
    } catch (err) {
      toast.error(`Kafka config failed: ${String(err)}`)
    } finally {
      setKafkaBusy(false)
    }
  }

  async function handleTestKafka(config: KafkaExportConfig) {
    if (!apiKey) return
    setKafkaBusy(true)
    try {
      const result = await testKafkaExportConfig(apiKey, config.id)
      if (result.ok) {
        toast.success(`Kafka test delivered to ${result.topic}`)
      } else {
        toast.error(`Kafka test failed: ${result.error}`)
      }
      await loadHealth()
    } catch (err) {
      toast.error(`Kafka test failed: ${String(err)}`)
    } finally {
      setKafkaBusy(false)
    }
  }

  async function handleToggleKafka(config: KafkaExportConfig) {
    if (!apiKey) return
    setKafkaBusy(true)
    try {
      await updateKafkaExportConfig(apiKey, config.id, { enabled: !config.enabled })
      toast.success(config.enabled ? 'Kafka export disabled' : 'Kafka export enabled')
      await loadHealth()
    } catch (err) {
      toast.error(`Kafka update failed: ${String(err)}`)
    } finally {
      setKafkaBusy(false)
    }
  }

  async function handleDeleteKafka(config: KafkaExportConfig) {
    if (!apiKey) return
    setKafkaBusy(true)
    try {
      await deleteKafkaExportConfig(apiKey, config.id)
      toast.success('Kafka export config deleted')
      await loadHealth()
    } catch (err) {
      toast.error(`Kafka delete failed: ${String(err)}`)
    } finally {
      setKafkaBusy(false)
    }
  }

  function toggleKafkaEvent(eventType: KafkaEventType) {
    setKafkaForm((prev) => {
      const exists = prev.event_types.includes(eventType)
      return {
        ...prev,
        event_types: exists
          ? prev.event_types.filter((item) => item !== eventType)
          : [...prev.event_types, eventType],
      }
    })
  }

  if (!canManageOrgSettings) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-900">Integrations</h1>
        <p className="mt-4 text-sm text-slate-500">Integration management is an organization-admin function.</p>
      </div>
    )
  }

  const healthyCount = healthItems.filter((item) => item.status === 'healthy').length
  const setupCount = healthItems.filter((item) => item.status === 'setup').length
  const disabledCount = healthItems.filter((item) => item.status === 'disabled').length
  const plannedCount = healthItems.filter((item) => item.status === 'planned').length

  return (
    <div className="min-h-screen space-y-8 bg-[radial-gradient(circle_at_top_left,rgba(147,197,253,0.20),transparent_36rem)] p-8">
      <div className="max-w-6xl">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-blue-600 dark:text-blue-600">Control Plane</p>
            <h1 className="mt-2 text-3xl font-bold text-slate-950 dark:text-slate-950">Integrations</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-600 dark:text-slate-600">
              Connect notification channels, MCP-aware agents, telemetry pipelines, model gateways, and auxiliary infrastructure to RunLedger.
            </p>
          </div>
          <div className="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 shadow-sm dark:border-blue-200 dark:bg-blue-50 dark:text-blue-900">
            <div className="flex items-center gap-2 font-semibold">
              <CheckCircle2 className="h-4 w-4" />
              Integration hub
            </div>
            <p className="mt-1 text-xs text-blue-700/80">Slack test is live. Additional connectors are staged for setup workflows.</p>
          </div>
        </div>

        <section className="mt-8 rounded-3xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-300 dark:bg-white/90">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-blue-700" />
                <h2 className="text-xl font-semibold text-slate-950">Integration Health Center</h2>
              </div>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                A quick readiness view for the paths agents use most: keys, MCP, Gateway, OTLP, notifications, backup, and streaming.
              </p>
              {healthError && (
                <p className="mt-2 flex items-center gap-2 text-sm text-amber-700">
                  <AlertCircle className="h-4 w-4" />
                  Some health checks could not be loaded: {healthError}
                </p>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">{healthyCount} healthy</span>
              <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">{setupCount} needs setup</span>
              <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{disabledCount} disabled</span>
              <span className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">{plannedCount} planned</span>
              <button
                type="button"
                onClick={() => void loadHealth()}
                disabled={healthLoading}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-blue-50 disabled:opacity-60"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${healthLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
          {healthLoading && healthItems.length === 0 ? (
            <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500">
              <CircleDashed className="mx-auto mb-2 h-5 w-5 animate-spin" />
              Checking integration readiness...
            </div>
          ) : (
            <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {healthItems.map((item) => (
                <HealthCard key={item.name} item={item} />
              ))}
            </div>
          )}
        </section>

        <div className="mt-8 rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-300 dark:bg-white/90">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-blue-700 dark:text-blue-700" />
                <h2 className="text-lg font-semibold text-slate-950 dark:text-slate-950">Slack Webhook</h2>
                <StatusBadge status="available" />
              </div>
              <p className="mt-2 max-w-2xl text-sm text-slate-600 dark:text-slate-600">
                Paste an incoming webhook URL to test connectivity before configuring budget notifications via{' '}
                <code className="rounded bg-slate-100 px-1 font-mono text-xs text-slate-700 dark:bg-slate-100 dark:text-slate-700">POST /budgets/{'{id}'}/notifications</code>.
              </p>
            </div>
          </div>
          <form onSubmit={handleTestSlack} className="mt-4 flex flex-wrap gap-2">
            <input
              type="url"
              placeholder="https://hooks.slack.com/services/..."
              value={slackWebhookUrl}
              onChange={(e) => setSlackWebhookUrl(e.target.value)}
              className={`min-w-72 flex-1 ${inputCls}`}
              required
            />
            <button type="submit" disabled={testingSlack || !slackWebhookUrl.trim()} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 dark:bg-blue-600 dark:text-white dark:hover:bg-blue-700">
              {testingSlack ? 'Sending...' : 'Test'}
            </button>
          </form>
          {slackTestResult && (
            <div className={`mt-3 rounded border px-3 py-2 text-sm ${slackTestResult.ok ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300' : 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300'}`}>
              {slackTestResult.ok ? 'Test message sent successfully.' : <>Failed: {slackTestResult.error}</>}
            </div>
          )}
        </div>

        <div className="mt-8 rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-300 dark:bg-white/90">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <RadioTower className="h-5 w-5 text-blue-700" />
                <h2 className="text-lg font-semibold text-slate-950">Kafka / Redpanda Export</h2>
                <StatusBadge status="available" />
              </div>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">
                Optional real-time export for RunLedger events. Keep it disabled unless you have Redpanda, Kafka, Confluent, or MSK ready.
              </p>
            </div>
          </div>

          <form onSubmit={handleCreateKafka} className="mt-5 rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
            <div className="grid gap-3 lg:grid-cols-4">
              <label className="text-xs font-semibold text-slate-600">
                Label
                <input
                  className={`mt-1 w-full ${inputCls}`}
                  value={kafkaForm.label}
                  onChange={(e) => setKafkaForm((prev) => ({ ...prev, label: e.target.value }))}
                />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Bootstrap servers
                <input
                  className={`mt-1 w-full ${inputCls}`}
                  value={kafkaForm.bootstrap_servers}
                  onChange={(e) => setKafkaForm((prev) => ({ ...prev, bootstrap_servers: e.target.value }))}
                />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Topic prefix
                <input
                  className={`mt-1 w-full ${inputCls}`}
                  value={kafkaForm.topic_prefix}
                  onChange={(e) => setKafkaForm((prev) => ({ ...prev, topic_prefix: e.target.value }))}
                />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Security
                <select
                  className={`mt-1 w-full ${inputCls}`}
                  value={kafkaForm.security_protocol}
                  onChange={(e) => setKafkaForm((prev) => ({ ...prev, security_protocol: e.target.value as KafkaSecurityProtocol }))}
                >
                  <option value="PLAINTEXT">PLAINTEXT</option>
                  <option value="SSL">SSL</option>
                  <option value="SASL_PLAINTEXT">SASL_PLAINTEXT</option>
                  <option value="SASL_SSL">SASL_SSL</option>
                </select>
              </label>
            </div>
            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Events</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {kafkaEvents.map((eventType) => {
                  const active = kafkaForm.event_types.includes(eventType)
                  return (
                    <button
                      key={eventType}
                      type="button"
                      onClick={() => toggleKafkaEvent(eventType)}
                      className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
                        active ? 'border-blue-300 bg-blue-100 text-blue-700' : 'border-slate-200 bg-white text-slate-500 hover:bg-blue-50'
                      }`}
                    >
                      {eventType}
                    </button>
                  )
                })}
              </div>
            </div>
            <button
              type="submit"
              disabled={kafkaBusy || !kafkaForm.label.trim() || !kafkaForm.bootstrap_servers.trim() || kafkaForm.event_types.length === 0}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
            >
              Create Kafka Export
            </button>
          </form>

          <div className="mt-5 space-y-3">
            {kafkaConfigs.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">
                No Kafka export configs yet. Create one for local Redpanda or a customer Kafka cluster.
              </div>
            ) : (
              kafkaConfigs.map((config) => (
                <div key={config.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold text-slate-950">{config.label}</h3>
                        <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${config.enabled ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
                          {config.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">{config.security_protocol}</span>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">{config.bootstrap_servers} / {config.topic_prefix}</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {config.event_types.map((eventType) => (
                          <span key={eventType} className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700">{eventType}</span>
                        ))}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" disabled={kafkaBusy} onClick={() => void handleTestKafka(config)} className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-100 disabled:opacity-50">
                        Test
                      </button>
                      <button type="button" disabled={kafkaBusy} onClick={() => void handleToggleKafka(config)} className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">
                        {config.enabled ? 'Disable' : 'Enable'}
                      </button>
                      <button type="button" disabled={kafkaBusy} onClick={() => void handleDeleteKafka(config)} className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100 disabled:opacity-50">
                        Delete
                      </button>
                    </div>
                  </div>
                  <div className="mt-4 overflow-hidden rounded-xl border border-slate-200">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="bg-slate-50 text-left text-slate-500">
                          <th className="px-3 py-2 font-semibold">Event</th>
                          <th className="px-3 py-2 font-semibold">Topic</th>
                          <th className="px-3 py-2 font-semibold">Status</th>
                          <th className="px-3 py-2 font-semibold">Error</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {(kafkaDeliveries[config.id] ?? []).length === 0 ? (
                          <tr><td colSpan={4} className="px-3 py-4 text-center text-slate-500">No deliveries yet.</td></tr>
                        ) : (
                          (kafkaDeliveries[config.id] ?? []).map((delivery) => (
                            <tr key={delivery.id}>
                              <td className="px-3 py-2 font-medium text-slate-700">{delivery.event_type}</td>
                              <td className="px-3 py-2 text-slate-500">{delivery.topic}</td>
                              <td className="px-3 py-2">
                                <span className={`rounded-full px-2 py-0.5 font-semibold ${delivery.status === 'success' ? 'bg-emerald-50 text-emerald-700' : delivery.status === 'failed' ? 'bg-rose-50 text-rose-700' : 'bg-slate-100 text-slate-600'}`}>
                                  {delivery.status}
                                </span>
                              </td>
                              <td className="max-w-sm truncate px-3 py-2 text-slate-500">{delivery.error_detail ?? '-'}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="mt-8 space-y-8">
          {integrationGroups.map((group) => (
            <section key={group.title}>
              <div className="mb-4">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">{group.title}</h2>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{group.description}</p>
              </div>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                {group.cards.map((card) => (
                  <IntegrationCardView key={card.name} card={card} />
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  )
}
