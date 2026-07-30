'use client'

import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { useState } from 'react'
import {
  Bell,
  Bot,
  CheckCircle2,
  Cloud,
  Code2,
  DatabaseBackup,
  GitBranch,
  KeyRound,
  Mail,
  MessageSquare,
  PlugZap,
  RadioTower,
  Server,
  ShieldCheck,
  Workflow,
} from 'lucide-react'
import { toast } from 'sonner'
import { useRole } from '@/components/rbac/useRole'
import { testSlackWebhook } from '@/lib/api'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

type IntegrationStatus = 'available' | 'planned' | 'docs' | 'coming-soon'

type IntegrationCard = {
  name: string
  description: string
  status: IntegrationStatus
  icon: React.ComponentType<{ className?: string }>
  href?: string
  details: string[]
}

const statusStyles: Record<IntegrationStatus, string> = {
  available: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  planned: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  docs: 'border-sky-500/30 bg-sky-500/10 text-sky-300',
  'coming-soon': 'border-slate-500/30 bg-slate-500/10 text-slate-300',
}

const statusLabel: Record<IntegrationStatus, string> = {
  available: 'Available',
  planned: 'Planned',
  docs: 'Guide',
  'coming-soon': 'Coming soon',
}

const integrationGroups: { title: string; description: string; cards: IntegrationCard[] }[] = [
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
        status: 'planned',
        icon: Bot,
        details: ['CLAUDE.md defaults', 'stdio/HTTP MCP bridge', 'Outcome capture'],
      },
      {
        name: 'OpenAI Codex',
        description: 'Add AGENTS.md and Codex hooks for sessions, subagents, tool use, and outcomes.',
        status: 'planned',
        icon: Code2,
        details: ['AGENTS.md defaults', 'Codex hooks', 'Subagent telemetry'],
      },
      {
        name: 'Cursor / Windsurf / Devin',
        description: 'Provide publishable setup skills for IDE agents and hosted autonomous sessions.',
        status: 'planned',
        icon: Workflow,
        details: ['Cursor rules', 'Windsurf hooks', 'Devin API bridge'],
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

function IntegrationCardView({ card }: { card: IntegrationCard }) {
  const Icon = card.icon
  return (
    <div className="group rounded-2xl border border-slate-200/80 bg-white/80 p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-lg dark:border-slate-800 dark:bg-slate-950/60 dark:hover:border-indigo-500/50">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-indigo-100 p-2 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300">
            <Icon className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{card.name}</h3>
            <StatusBadge status={card.status} />
          </div>
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-400">{card.description}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {card.details.map((detail) => (
          <span key={detail} className="rounded-full bg-slate-100 px-2 py-1 text-[11px] text-slate-600 dark:bg-slate-900 dark:text-slate-400">
            {detail}
          </span>
        ))}
      </div>
      <div className="mt-4">
        {card.href ? (
          <Link href={card.href} className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-indigo-400 hover:text-indigo-600 dark:border-slate-700 dark:text-slate-300 dark:hover:border-indigo-500 dark:hover:text-indigo-300">
            Open
          </Link>
        ) : (
          <button disabled className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-400 dark:border-slate-800 dark:text-slate-600">
            Configure soon
          </button>
        )}
      </div>
    </div>
  )
}

export default function IntegrationsPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { canManageOrgSettings } = useRole()

  const [slackWebhookUrl, setSlackWebhookUrl] = useState('')
  const [slackTestResult, setSlackTestResult] = useState<{ ok: boolean; error: string | null } | null>(null)
  const [testingSlack, setTestingSlack] = useState(false)

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

  if (!canManageOrgSettings) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Integrations</h1>
        <p className="mt-4 text-sm text-slate-500">Integration management is an organization-admin function.</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen space-y-8 bg-[radial-gradient(circle_at_top_left,rgba(79,70,229,0.12),transparent_36rem)] p-8">
      <div className="max-w-6xl">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-indigo-400">Control Plane</p>
            <h1 className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">Integrations</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
              Connect notification channels, MCP-aware agents, telemetry pipelines, model gateways, and auxiliary infrastructure to RunLedger.
            </p>
          </div>
          <div className="rounded-2xl border border-indigo-500/20 bg-indigo-500/10 px-4 py-3 text-sm text-indigo-100">
            <div className="flex items-center gap-2 font-semibold">
              <CheckCircle2 className="h-4 w-4" />
              Integration hub
            </div>
            <p className="mt-1 text-xs text-indigo-200/80">Slack test is live. Additional connectors are staged for setup workflows.</p>
          </div>
        </div>

        <div className="mt-8 rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950/60">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-indigo-400" />
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Slack Webhook</h2>
                <StatusBadge status="available" />
              </div>
              <p className="mt-2 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
                Paste an incoming webhook URL to test connectivity before configuring budget notifications via{' '}
                <code className="rounded bg-slate-100 px-1 font-mono text-xs dark:bg-slate-800">POST /budgets/{'{id}'}/notifications</code>.
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
            <button type="submit" disabled={testingSlack || !slackWebhookUrl.trim()} className="rounded bg-indigo-600 px-4 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
              {testingSlack ? 'Sending...' : 'Test'}
            </button>
          </form>
          {slackTestResult && (
            <div className={`mt-3 rounded border px-3 py-2 text-sm ${slackTestResult.ok ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300' : 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300'}`}>
              {slackTestResult.ok ? 'Test message sent successfully.' : <>Failed: {slackTestResult.error}</>}
            </div>
          )}
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
