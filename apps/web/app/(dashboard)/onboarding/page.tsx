'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import {
  Rocket, CheckCircle2, Circle, Network, Globe, Code,
  GitBranch, Bot, Terminal, MousePointer, Wind, Cpu,
  Copy, Check, ChevronUp, DollarSign, Shield, Eye,
} from 'lucide-react'
import {
  getDemoModeStatus,
  getOnboardingStatus,
  triggerDemoReset,
  triggerDemoSeed,
} from '@/lib/api'
import type { DemoModeStatus, OnboardingStatus } from '@/types/api'

/* ------------------------------------------------------------------ */
/*  Steps checklist (unchanged)                                       */
/* ------------------------------------------------------------------ */

const STEPS: { key: keyof OnboardingStatus; label: string; description: string; href: string }[] = [
  { key: 'has_org', label: 'Create Organization', description: 'Create the first organization, then open the org console to manage workspaces, users, and access', href: '/organizations' },
  { key: 'has_workspace', label: 'Set Up Workspace', description: 'Create a workspace to group your AI workloads', href: '/workspace' },
  { key: 'has_api_key', label: 'Generate API Key', description: 'Create an API key to authenticate your requests', href: '/api-keys' },
  { key: 'has_first_run', label: 'Send First Run', description: 'Log your first LLM inference run through RunLedger', href: '/runs' },
  { key: 'has_gateway_route', label: 'Configure Gateway Route', description: 'Route LLM traffic through the RunLedger gateway', href: '/gateway' },
  { key: 'has_budget', label: 'Set a Budget', description: 'Define spending limits for your AI operations', href: '/budgets' },
  { key: 'has_alert_rule', label: 'Create Alert Rule', description: 'Get notified when costs or usage cross a threshold', href: '/alert-rules' },
]

const FINOPS_STEPS: { key: keyof OnboardingStatus; label: string; description: string; href: string }[] = [
  { key: 'has_budget_notification', label: 'Configure Budget Notifications', description: 'Set up webhook or Slack alerts for budget events', href: '/budgets' },
  { key: 'has_billing_period', label: 'Create Billing Period', description: 'Define a billing cycle to track spend over time', href: '/billing' },
]

const GATEWAY_STEPS: { key: keyof OnboardingStatus; label: string; description: string; href: string }[] = [
  { key: 'has_provider_profile', label: 'Connect a Provider', description: 'Add an LLM provider to route traffic through the gateway', href: '/gateway' },
  { key: 'has_guardrail', label: 'Activate a Guardrail', description: 'Enable content safety or policy guardrails on gateway traffic', href: '/guardrails' },
  { key: 'has_rate_limit', label: 'Set a Rate Limit', description: 'Configure per-user RPM limits on a gateway route', href: '/gateway' },
]

const SAFETY_STEPS: { key: keyof OnboardingStatus; label: string; description: string; href: string }[] = [
  { key: 'has_mcp_server', label: 'Register MCP Server', description: 'Add an MCP server to the workspace registry', href: '/mcp' },
  { key: 'has_search_tool', label: 'Add Search Tool', description: 'Register a search tool for agent retrieval workflows', href: '/tools' },
  { key: 'has_tool_policy', label: 'Create Tool Policy', description: 'Define allow/deny rules for tool usage', href: '/tool-policies' },
  { key: 'has_approval_config', label: 'Set Up Approvals', description: 'Create an approval workflow for sensitive actions', href: '/approvals' },
  { key: 'has_data_capture', label: 'Configure Data Capture', description: 'Set the privacy mode and sampling for payload capture', href: '/data-capture' },
  { key: 'has_security_config', label: 'Review Security Settings', description: 'Configure metadata requirements, IP ACLs, and OIDC', href: '/security' },
  { key: 'has_tag', label: 'Create a Tag', description: 'Add taxonomy tags for classification and filtering', href: '/tags' },
]

/* ------------------------------------------------------------------ */
/*  Integration definitions                                           */
/* ------------------------------------------------------------------ */

interface Integration {
  id: string
  name: string
  subtitle: string
  category: 'desktop_agents' | 'gateway_clients' | 'telemetry_frameworks'
  icon: React.ComponentType<{ className?: string }>
  steps: string[]
  configTitle: string
  configSnippet: string
}

type SetupLane = {
  id: string
  title: string
  description: string
  href: string
  icon: React.ComponentType<{ className?: string }>
}

const SETUP_LANES: SetupLane[] = [
  {
    id: 'foundation',
    title: 'Foundation',
    description: 'Create the org, workspace, API key, and first controls before connecting external tools.',
    href: '#foundation-checklist',
    icon: Rocket,
  },
  {
    id: 'desktop',
    title: 'Desktop Agents',
    description: 'Claude, Codex, Cursor, Windsurf, and similar tools connect here first.',
    href: '#connection-paths',
    icon: Bot,
  },
  {
    id: 'telemetry',
    title: 'Telemetry',
    description: 'Use OTLP, OpenInference, and framework callbacks when you already have an instrumented stack.',
    href: '/monitoring/telemetry',
    icon: Network,
  },
  {
    id: 'destinations',
    title: 'Destinations',
    description: 'Manage Kafka, export webhooks, and storage overrides in the Organization Console.',
    href: '/organization?tab=destinations',
    icon: Globe,
  },
]

const INTEGRATION_GROUPS: Array<{
  id: Integration['category']
  title: string
  description: string
}> = [
  {
    id: 'desktop_agents',
    title: 'Desktop Agents And MCP Clients',
    description: 'Best when you want Claude, Codex, Cursor, Windsurf, or hosted coding tools to report work into RunLedger.',
  },
  {
    id: 'gateway_clients',
    title: 'Gateway-Routed Clients',
    description: 'Best when you want a tool to send inference through the RunLedger gateway for routing, budgets, and control.',
  },
  {
    id: 'telemetry_frameworks',
    title: 'Telemetry And Framework Hooks',
    description: 'Best when you already have app code, callback hooks, or orchestration frameworks that can emit traces out of band.',
  },
]

const INTEGRATIONS: Integration[] = [
  {
    id: 'litellm',
    name: 'LiteLLM',
    subtitle: 'LLM proxy gateway',
    category: 'gateway_clients',
    icon: Network,
    steps: [
      'Install the RunLedger callback package: pip install runledger-litellm',
      'Add the RunLedger callback to your LiteLLM proxy config file.',
      'Restart the LiteLLM proxy and verify the connection on the Gateway page.',
    ],
    configTitle: 'litellm_settings (config.yaml)',
    configSnippet: `litellm_settings:
  success_callback: ["runledger"]
  runledger_api_key: "rl_YOUR_API_KEY"
  runledger_api_base: "https://api.runledger.app"`,
  },
  {
    id: 'openwebui',
    name: 'Open WebUI',
    subtitle: 'Chat interface',
    category: 'gateway_clients',
    icon: Globe,
    steps: [
      'Navigate to Admin > Settings > Connections in Open WebUI.',
      'Set the OpenAI-compatible API base URL to your RunLedger gateway endpoint.',
      'Enter your RunLedger API key and save.',
    ],
    configTitle: 'Open WebUI Connection Settings',
    configSnippet: `API Base URL: https://gateway.runledger.app/v1
API Key:      rl_YOUR_API_KEY
Model Filter: (leave empty to proxy all models)`,
  },
  {
    id: 'openhands',
    name: 'OpenHands',
    subtitle: 'AI coding agent',
    category: 'gateway_clients',
    icon: Code,
    steps: [
      'Set the LLM base URL environment variable to your RunLedger gateway.',
      'Export your RunLedger API key as the provider key.',
      'Launch the OpenHands agent - all calls are now routed through RunLedger.',
    ],
    configTitle: 'Environment Variables',
    configSnippet: `export LLM_BASE_URL="https://gateway.runledger.app/v1"
export LLM_API_KEY="rl_YOUR_API_KEY"
export LLM_MODEL="gpt-4o"`,
  },
  {
    id: 'langgraph',
    name: 'LangGraph',
    subtitle: 'Agent orchestration',
    category: 'telemetry_frameworks',
    icon: GitBranch,
    steps: [
      'Install the RunLedger LangChain integration: pip install runledger-langchain',
      'Add the RunLedger callback handler to your LangGraph agent.',
      'Run your graph - each node invocation is tracked automatically.',
    ],
    configTitle: 'Python Agent Code',
    configSnippet: `from runledger_langchain import RunLedgerCallbackHandler

handler = RunLedgerCallbackHandler(
    api_key="rl_YOUR_API_KEY",
)

# Pass to your LangGraph agent
app.invoke(input, config={"callbacks": [handler]})`,
  },
  {
    id: 'claude-code',
    name: 'Claude Code',
    subtitle: 'Anthropic CLI agent',
    category: 'desktop_agents',
    icon: Bot,
    steps: [
      'Add the RunLedger MCP server to your Claude Code configuration.',
      'Restart Claude Code to pick up the new MCP server.',
      'All Claude Code sessions will now report usage to RunLedger.',
    ],
    configTitle: 'MCP Configuration (~/.claude.json)',
    configSnippet: `{
  "mcpServers": {
    "runledger": {
      "command": "npx",
      "args": ["-y", "runledger-mcp"],
      "env": {
        "RUNLEDGER_API_KEY": "rl_YOUR_API_KEY"
      }
    }
  }
}`,
  },
  {
    id: 'codex',
    name: 'Codex',
    subtitle: 'OpenAI CLI agent',
    category: 'desktop_agents',
    icon: Terminal,
    steps: [
      'Set your API base URL to the RunLedger gateway.',
      'Use your RunLedger API key in place of the OpenAI key.',
      'Run Codex as usual - requests are proxied and tracked.',
    ],
    configTitle: 'Environment Variables',
    configSnippet: `export OPENAI_BASE_URL="https://gateway.runledger.app/v1"
export OPENAI_API_KEY="rl_YOUR_API_KEY"`,
  },
  {
    id: 'cursor',
    name: 'Cursor',
    subtitle: 'AI-powered IDE',
    category: 'desktop_agents',
    icon: MousePointer,
    steps: [
      'Create or edit the MCP config file in your project.',
      'Add the RunLedger MCP server entry.',
      'Restart Cursor to enable the integration.',
    ],
    configTitle: '.cursor/mcp.json',
    configSnippet: `{
  "mcpServers": {
    "runledger": {
      "command": "npx",
      "args": ["-y", "runledger-mcp"],
      "env": {
        "RUNLEDGER_API_KEY": "rl_YOUR_API_KEY"
      }
    }
  }
}`,
  },
  {
    id: 'windsurf',
    name: 'Windsurf',
    subtitle: 'AI-powered IDE',
    category: 'desktop_agents',
    icon: Wind,
    steps: [
      'Open Windsurf settings and navigate to the AI provider section.',
      'Set the API base URL to your RunLedger gateway endpoint.',
      'Enter your RunLedger API key and select your preferred model.',
    ],
    configTitle: 'Windsurf Settings (settings.json)',
    configSnippet: `{
  "ai.provider": {
    "baseUrl": "https://gateway.runledger.app/v1",
    "apiKey": "rl_YOUR_API_KEY",
    "model": "gpt-4o"
  }
}`,
  },
  {
    id: 'devin',
    name: 'Devin',
    subtitle: 'Autonomous coding agent',
    category: 'desktop_agents',
    icon: Cpu,
    steps: [
      'In the Devin dashboard, go to Settings > API Configuration.',
      'Set the LLM proxy URL to your RunLedger gateway.',
      'Save and re-launch your Devin session to apply.',
    ],
    configTitle: 'Devin API Configuration',
    configSnippet: `LLM Proxy URL: https://gateway.runledger.app/v1
API Key:       rl_YOUR_API_KEY
Workspace:     default`,
  },
]

/* ------------------------------------------------------------------ */
/*  Code snippet with copy button                                     */
/* ------------------------------------------------------------------ */

function CodeBlock({ title, code }: { title: string; code: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      toast.success('Copied to clipboard')
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error('Failed to copy')
    }
  }

  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
      <div className="flex items-center justify-between bg-slate-100 px-4 py-2 dark:bg-slate-800">
        <span className="text-xs font-medium text-slate-600 dark:text-slate-300">{title}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-slate-500 transition-colors hover:bg-slate-200 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-200"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="overflow-x-auto bg-slate-50 p-4 text-sm leading-relaxed text-slate-800 dark:bg-slate-900 dark:text-slate-200">
        <code>{code}</code>
      </pre>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Main page                                                         */
/* ------------------------------------------------------------------ */

export default function OnboardingPage() {
  const { data: session } = useSession()
  const searchParams = useSearchParams()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''
  const [status, setStatus] = useState<OnboardingStatus | null>(null)
  const [demoStatus, setDemoStatus] = useState<DemoModeStatus | null>(null)
  const [selectedDemoProfile, setSelectedDemoProfile] = useState<'full' | 'quick'>('full')
  const [seeding, setSeeding] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [selectedIntegration, setSelectedIntegration] = useState<string | null>(null)

  useEffect(() => {
    if (!apiKey) return
    getOnboardingStatus(apiKey).then(setStatus).catch(() => toast.error('Failed to load onboarding status'))
    getDemoModeStatus(apiKey).then((state) => {
      setDemoStatus(state)
      if (state.profile === 'quick' || state.profile === 'full') {
        setSelectedDemoProfile(state.profile)
      }
    }).catch(() => {})
  }, [apiKey])

  useEffect(() => {
    if (!apiKey || !demoStatus || !['queued', 'running'].includes(demoStatus.status)) return

    const interval = window.setInterval(async () => {
      try {
        const next = await getDemoModeStatus(apiKey)
        setDemoStatus(next)
        if (!['queued', 'running'].includes(next.status)) {
          const updated = await getOnboardingStatus(apiKey)
          setStatus(updated)
        }
      } catch {
      }
    }, 2500)

    return () => window.clearInterval(interval)
  }, [apiKey, demoStatus])

  const handleSeed = async () => {
    setSeeding(true)
    try {
      const res = await triggerDemoSeed(apiKey, selectedDemoProfile)
      setDemoStatus(res.state)
      toast.success(res.message)
      const updated = await getOnboardingStatus(apiKey)
      setStatus(updated)
    } catch {
      toast.error('Failed to trigger demo seed')
    } finally {
      setSeeding(false)
    }
  }

  const handleReset = async () => {
    setResetting(true)
    try {
      const res = await triggerDemoReset(apiKey)
      setDemoStatus(res.state)
      toast.success(res.message)
    } catch {
      toast.error('Failed to trigger demo reset')
    } finally {
      setResetting(false)
    }
  }

  if (!status) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    )
  }

  const active = INTEGRATIONS.find((i) => i.id === selectedIntegration)
  const demoProfiles = demoStatus?.available_profiles ?? []
  const manualProfile = demoProfiles.find((profile) => profile.id === 'manual')
  const automatedProfiles = demoProfiles.filter((profile) => profile.kind === 'automated')
  const showConnectionsSection = searchParams.get('section') === 'connections'
  const groupedIntegrations = INTEGRATION_GROUPS.map((group) => ({
    ...group,
    items: INTEGRATIONS.filter((integration) => integration.category === group.id),
  }))

  return (
    <div className="mx-auto max-w-2xl space-y-6 py-10">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Rocket className="h-8 w-8 text-blue-500" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Getting Started</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Complete these steps to get the most out of RunLedger</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            External-tool setup now lives here. Use this page for Claude, Codex, Cursor, Windsurf, MCP, telemetry, and existing-stack connection guidance.
          </p>
        </div>
      </div>

      {showConnectionsSection && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50/80 p-4 text-sm text-blue-800 shadow-sm dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-200">
          The legacy <span className="font-semibold">Integrations</span> route now redirects into Onboarding. Setup guidance lives here, while deep operational surfaces stay in MCP, Telemetry, Organization Console, and Platform Settings.
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {SETUP_LANES.map((lane) => {
          const Icon = lane.icon
          const isAnchor = lane.href.startsWith('#')
          const className = 'rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition-colors hover:border-blue-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-700 dark:hover:bg-slate-800'
          const content = (
            <>
              <div className="flex items-center gap-2">
                <Icon className="h-5 w-5 text-blue-500" />
                <h2 className="font-medium">{lane.title}</h2>
              </div>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{lane.description}</p>
            </>
          )

          if (isAnchor) {
            return (
              <a key={lane.id} href={lane.href} className={className}>
                {content}
              </a>
            )
          }

          return (
            <Link key={lane.id} href={lane.href} className={className}>
              {content}
            </Link>
          )
        })}
      </div>

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
          <div
            className="h-full rounded-full bg-blue-500 transition-all duration-500"
            style={{ width: `${status.pct}%` }}
          />
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {status.completed} of {status.total} steps completed
        </p>
      </div>

      {status.pct === 100 && (
        <div className="rounded-2xl border border-green-200 bg-green-50 p-4 text-center text-green-700 dark:border-green-800 dark:bg-green-900/30 dark:text-green-300">
          You&apos;re all set! RunLedger is fully configured.
        </div>
      )}

      {/* ---- Foundation checklist ---- */}
      <div id="foundation-checklist" className="space-y-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">1. Lay The Foundation</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Start with organization, workspace, API key, first traffic, and baseline controls before connecting external tools.
          </p>
        </div>
        {STEPS.map((step) => {
          const done = !!status[step.key]
          return (
            <Link key={step.key} href={step.href}>
              <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800">
                {done ? (
                  <CheckCircle2 className="h-6 w-6 shrink-0 text-green-500" />
                ) : (
                  <Circle className="h-6 w-6 shrink-0 text-slate-400" />
                )}
                <div className="min-w-0 flex-1">
                  <p className={`font-medium ${done ? 'text-slate-400 line-through dark:text-slate-500' : ''}`}>{step.label}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{step.description}</p>
                </div>
                {done ? (
                  <span className="shrink-0 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/40 dark:text-green-400">
                    Connected
                  </span>
                ) : (
                  <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                    Pending
                  </span>
                )}
              </div>
            </Link>
          )
        })}
      </div>

      {/* ---- FinOps Readiness ---- */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <DollarSign className="h-5 w-5 text-emerald-500" />
          <div>
            <h2 className="text-lg font-semibold tracking-tight">2. FinOps Readiness</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">Complete your financial operations setup.</p>
          </div>
        </div>
        {FINOPS_STEPS.map((step) => {
          const done = !!status[step.key]
          return (
            <Link key={step.key} href={step.href}>
              <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800">
                {done ? <CheckCircle2 className="h-6 w-6 shrink-0 text-green-500" /> : <Circle className="h-6 w-6 shrink-0 text-slate-400" />}
                <div className="min-w-0 flex-1">
                  <p className={`font-medium ${done ? 'text-slate-400 line-through dark:text-slate-500' : ''}`}>{step.label}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{step.description}</p>
                </div>
                {done ? (
                  <span className="shrink-0 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/40 dark:text-green-400">Done</span>
                ) : (
                  <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">Set up now</span>
                )}
              </div>
            </Link>
          )
        })}
      </div>

      {/* ---- Gateway & Routing ---- */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Network className="h-5 w-5 text-violet-500" />
          <div>
            <h2 className="text-lg font-semibold tracking-tight">3. Gateway &amp; Routing</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">Configure providers, guardrails, and rate limits.</p>
          </div>
        </div>
        {GATEWAY_STEPS.map((step) => {
          const done = !!status[step.key]
          return (
            <Link key={step.key} href={step.href}>
              <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800">
                {done ? <CheckCircle2 className="h-6 w-6 shrink-0 text-green-500" /> : <Circle className="h-6 w-6 shrink-0 text-slate-400" />}
                <div className="min-w-0 flex-1">
                  <p className={`font-medium ${done ? 'text-slate-400 line-through dark:text-slate-500' : ''}`}>{step.label}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{step.description}</p>
                </div>
                {done ? (
                  <span className="shrink-0 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/40 dark:text-green-400">Done</span>
                ) : (
                  <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">Set up now</span>
                )}
              </div>
            </Link>
          )
        })}
      </div>

      {/* ---- Observe & Monitor ---- */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Eye className="h-5 w-5 text-teal-500" />
          <div>
            <h2 className="text-lg font-semibold tracking-tight">4. Observe &amp; Monitor</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">Verify your observability surfaces are receiving data.</p>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <Link href="/analytics" className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition-colors hover:border-teal-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-teal-700 dark:hover:bg-slate-800">
            <h3 className="font-medium">Workspace Dashboard</h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Overview of workspace activity and health.</p>
          </Link>
          <Link href="/runs" className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition-colors hover:border-teal-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-teal-700 dark:hover:bg-slate-800">
            <h3 className="font-medium">Runs</h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Run list, detail, and execution traces.</p>
          </Link>
          <Link href="/analytics" className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition-colors hover:border-teal-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-teal-700 dark:hover:bg-slate-800">
            <h3 className="font-medium">Analytics Overview</h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Explore run volume, latency, and model usage.</p>
          </Link>
          <Link href="/alert-rules" className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition-colors hover:border-teal-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-teal-700 dark:hover:bg-slate-800">
            <h3 className="font-medium">Monitoring</h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Alert rules and threshold-based notifications.</p>
          </Link>
        </div>
      </div>

      {/* ---- Safety & Governance ---- */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-amber-500" />
          <div>
            <h2 className="text-lg font-semibold tracking-tight">5. Safety &amp; Governance</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">Establish governance policies, tool controls, and security posture.</p>
          </div>
        </div>
        {SAFETY_STEPS.map((step) => {
          const done = !!status[step.key]
          return (
            <Link key={step.key} href={step.href}>
              <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800">
                {done ? <CheckCircle2 className="h-6 w-6 shrink-0 text-green-500" /> : <Circle className="h-6 w-6 shrink-0 text-slate-400" />}
                <div className="min-w-0 flex-1">
                  <p className={`font-medium ${done ? 'text-slate-400 line-through dark:text-slate-500' : ''}`}>{step.label}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{step.description}</p>
                </div>
                {done ? (
                  <span className="shrink-0 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/40 dark:text-green-400">Done</span>
                ) : (
                  <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">Set up now</span>
                )}
              </div>
            </Link>
          )
        })}
      </div>

      {/* ---- Integration Path Selector ---- */}
      <div id="connection-paths" className="space-y-5">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">6. Choose A Connection Path</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Pick the path that matches how your tool connects to RunLedger: desktop agent, gateway-routed client, or telemetry/framework hook.
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <Link
            href="/mcp"
            className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition-colors hover:border-blue-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-700 dark:hover:bg-slate-800"
          >
            <div className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-blue-500" />
              <h3 className="font-medium">MCP Setup</h3>
            </div>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Use MCP setup and registry flows for Claude, Cursor, and other MCP-aware tools.
            </p>
          </Link>
          <Link
            href="/settings"
            className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition-colors hover:border-blue-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-700 dark:hover:bg-slate-800"
          >
            <div className="flex items-center gap-2">
              <Rocket className="h-5 w-5 text-blue-500" />
              <h3 className="font-medium">Platform Settings</h3>
            </div>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Use platform settings for SMTP, platform webhook defaults, and other deployment-wide controls.
            </p>
          </Link>
          <Link
            href="/users"
            className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition-colors hover:border-blue-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-700 dark:hover:bg-slate-800"
          >
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-blue-500" />
              <h3 className="font-medium">Users</h3>
            </div>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Manage organization members, invite users, and assign workspace roles.
            </p>
          </Link>
          <Link
            href="/access-groups"
            className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition-colors hover:border-blue-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-700 dark:hover:bg-slate-800"
          >
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-blue-500" />
              <h3 className="font-medium">Access Groups</h3>
            </div>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Group-based permissions with dashboard filtering profiles and budget envelopes.
            </p>
          </Link>
          <Link
            href="/monitoring/telemetry"
            className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition-colors hover:border-blue-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-700 dark:hover:bg-slate-800"
          >
            <div className="flex items-center gap-2">
              <Eye className="h-5 w-5 text-blue-500" />
              <h3 className="font-medium">Telemetry</h3>
            </div>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Platform telemetry, traces, and diagnostic data for monitoring system health.
            </p>
          </Link>
          <Link
            href="/mcp-registry"
            className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition-colors hover:border-blue-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-700 dark:hover:bg-slate-800"
          >
            <div className="flex items-center gap-2">
              <Network className="h-5 w-5 text-blue-500" />
              <h3 className="font-medium">MCP Registry</h3>
            </div>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Browse and manage registered MCP servers and tool integrations.
            </p>
          </Link>
          <Link
            href="/ai-hub"
            className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition-colors hover:border-blue-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-700 dark:hover:bg-slate-800"
          >
            <div className="flex items-center gap-2">
              <Cpu className="h-5 w-5 text-blue-500" />
              <h3 className="font-medium">AI Hub</h3>
            </div>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Central AI operations hub for model management and orchestration.
            </p>
          </Link>
          <Link
            href="/organizations"
            className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm transition-colors hover:border-blue-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-700 dark:hover:bg-slate-800"
          >
            <div className="flex items-center gap-2">
              <Globe className="h-5 w-5 text-blue-500" />
              <h3 className="font-medium">All Organizations</h3>
            </div>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              View and manage all organizations across the platform.
            </p>
          </Link>
        </div>

        {groupedIntegrations.map((group) => (
          <div key={group.id} className="space-y-3">
            <div>
              <h3 className="text-base font-semibold tracking-tight">{group.title}</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">{group.description}</p>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              {group.items.map((integration) => {
                const Icon = integration.icon
                const isSelected = selectedIntegration === integration.id
                return (
                  <button
                    key={integration.id}
                    onClick={() => setSelectedIntegration(isSelected ? null : integration.id)}
                    className={`flex flex-col items-center gap-2 rounded-2xl border p-4 text-center transition-all ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50 shadow-md dark:border-blue-400 dark:bg-blue-950/40'
                        : 'border-slate-200 bg-white/90 shadow-sm hover:border-blue-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-600 dark:hover:bg-slate-800'
                    }`}
                  >
                    <Icon className={`h-6 w-6 ${isSelected ? 'text-blue-500 dark:text-blue-400' : 'text-slate-500 dark:text-slate-400'}`} />
                    <span className={`text-sm font-medium ${isSelected ? 'text-blue-700 dark:text-blue-300' : ''}`}>{integration.name}</span>
                    <span className="text-xs text-slate-400 dark:text-slate-500">{integration.subtitle}</span>
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* ---- Integration-specific instructions ---- */}
      {active && (
        <div className="rounded-2xl border border-blue-200 bg-white/90 p-6 shadow-sm dark:border-blue-800 dark:bg-slate-900">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">7. Connect {active.name} To RunLedger</h3>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                Follow the smallest possible setup path, then validate the resulting traffic in Telemetry, Runs, or Request Explorer.
              </p>
            </div>
            <button
              onClick={() => setSelectedIntegration(null)}
              className="text-sm text-slate-400 transition-colors hover:text-slate-600 dark:hover:text-slate-300"
            >
              <ChevronUp className="h-5 w-5" />
            </button>
          </div>
          <ol className="mb-4 list-inside list-decimal space-y-2 text-sm text-slate-700 dark:text-slate-300">
            {active.steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
          <CodeBlock title={active.configTitle} code={active.configSnippet} />
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href="/monitoring/telemetry" className="rounded-full border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:text-slate-300 dark:hover:border-blue-700 dark:hover:text-blue-300">
              Validate in Telemetry
            </Link>
            <Link href="/runs" className="rounded-full border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:text-slate-300 dark:hover:border-blue-700 dark:hover:text-blue-300">
              Check Runs
            </Link>
            <Link href="/request-explorer" className="rounded-full border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:text-slate-300 dark:hover:border-blue-700 dark:hover:text-blue-300">
              Open Request Explorer
            </Link>
          </div>
        </div>
      )}

      {/* ---- Demo mode ---- */}
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="mb-1 font-semibold">8. Demo Mode And Labs</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Use the full simulator for the complete Phase 13 story, the quick seed for a lighter REST-only setup, or the labs for a manual walkthrough.
            </p>
          </div>
          {demoStatus && (
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium uppercase text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {demoStatus.status}
            </span>
          )}
        </div>

        {automatedProfiles.length > 0 && (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {automatedProfiles.map((profile) => {
              const selected = selectedDemoProfile === profile.id
              return (
                <button
                  key={profile.id}
                  type="button"
                  onClick={() => setSelectedDemoProfile(profile.id as 'full' | 'quick')}
                  className={`rounded-xl border p-4 text-left transition-colors ${
                    selected
                      ? 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-950/40'
                      : 'border-slate-200 bg-slate-50 hover:border-blue-300 dark:border-slate-700 dark:bg-slate-800/60 dark:hover:border-blue-600'
                  }`}
                >
                  <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{profile.label}</p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{profile.description}</p>
                </button>
              )
            })}
          </div>
        )}

        {demoStatus && (
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/60">
            <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
              {demoStatus.profile ? `${demoStatus.profile.toUpperCase()} ` : ''}
              {demoStatus.action ? `${demoStatus.action.toUpperCase()}: ` : ''}
              {demoStatus.message}
            </p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Updated {new Date(demoStatus.updated_at).toLocaleString()}
            </p>
            <a
              href={demoStatus.runbook_path}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
            >
              Open demo runbook
            </a>
            {manualProfile && (
              <a
                href={manualProfile.runbook_path}
                target="_blank"
                rel="noreferrer"
                className="ml-4 inline-flex text-xs font-medium text-slate-600 hover:text-slate-700 dark:text-slate-300 dark:hover:text-slate-100"
              >
                Open labs workbook
              </a>
            )}
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            onClick={handleSeed}
            disabled={seeding || resetting}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium transition-colors hover:bg-slate-100 disabled:opacity-50 dark:border-slate-600 dark:hover:bg-slate-800"
          >
            {seeding ? 'Seeding…' : 'Seed Demo Data'}
          </button>
          <button
            onClick={handleReset}
            disabled={seeding || resetting}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium transition-colors hover:bg-slate-100 disabled:opacity-50 dark:border-slate-600 dark:hover:bg-slate-800"
          >
            {resetting ? 'Resetting…' : 'Reset Demo Data'}
          </button>
        </div>
      </div>
    </div>
  )
}
