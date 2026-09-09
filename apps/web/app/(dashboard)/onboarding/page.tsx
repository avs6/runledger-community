'use client'

import { useEffect, useMemo, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import {
  Rocket, CheckCircle2, Circle, Network, Globe, Code,
  GitBranch, Bot, Terminal, MousePointer, Wind, Cpu,
  Copy, Check, ChevronDown, ChevronUp, DollarSign, Shield, Eye,
  Sparkles, ArrowRight, Play, RotateCcw, FlaskConical,
} from 'lucide-react'
import {
  getDemoModeStatus,
  getOnboardingStatus,
  triggerDemoReset,
  triggerDemoSeed,
} from '@/lib/api'
import type { DemoModeStatus, OnboardingStatus } from '@/types/api'

/* ------------------------------------------------------------------ */
/*  Steps                                                              */
/* ------------------------------------------------------------------ */

type Step = { key: keyof OnboardingStatus; label: string; description: string; href: string }

const STEPS: Step[] = [
  { key: 'has_org', label: 'Create Organization', description: 'Create the first organization, then open the org console to manage workspaces, users, and access', href: '/organizations' },
  { key: 'has_workspace', label: 'Set Up Workspace', description: 'Create a workspace to group your AI workloads', href: '/workspace' },
  { key: 'has_api_key', label: 'Generate API Key', description: 'Create an API key to authenticate your requests', href: '/api-keys' },
  { key: 'has_first_run', label: 'Send First Run', description: 'Log your first LLM inference run through RunLedger', href: '/runs' },
  { key: 'has_gateway_route', label: 'Configure Gateway Route', description: 'Route LLM traffic through the RunLedger gateway', href: '/gateway' },
  { key: 'has_budget', label: 'Set a Budget', description: 'Define spending limits for your AI operations', href: '/budgets' },
  { key: 'has_alert_rule', label: 'Create Alert Rule', description: 'Get notified when costs or usage cross a threshold', href: '/alert-rules' },
]

const FINOPS_STEPS: Step[] = [
  { key: 'has_budget_notification', label: 'Configure Budget Notifications', description: 'Set up webhook or Slack alerts for budget events', href: '/budgets' },
  { key: 'has_billing_period', label: 'Create Billing Period', description: 'Define a billing cycle to track spend over time', href: '/billing' },
]

const GATEWAY_STEPS: Step[] = [
  { key: 'has_provider_profile', label: 'Connect a Provider', description: 'Add an LLM provider to route traffic through the gateway', href: '/gateway' },
  { key: 'has_guardrail', label: 'Activate a Guardrail', description: 'Enable content safety or policy guardrails on gateway traffic', href: '/guardrails' },
  { key: 'has_rate_limit', label: 'Set a Rate Limit', description: 'Configure per-user RPM limits on a gateway route', href: '/gateway' },
]

const SAFETY_STEPS: Step[] = [
  { key: 'has_mcp_server', label: 'Register MCP Server', description: 'Add an MCP server to the workspace registry', href: '/mcp' },
  { key: 'has_search_tool', label: 'Add Search Tool', description: 'Register a search tool for agent retrieval workflows', href: '/tools' },
  { key: 'has_tool_policy', label: 'Create Tool Policy', description: 'Define allow/deny rules for tool usage', href: '/tool-policies' },
  { key: 'has_approval_config', label: 'Set Up Approvals', description: 'Create an approval workflow for sensitive actions', href: '/approvals' },
  { key: 'has_data_capture', label: 'Configure Data Capture', description: 'Set the privacy mode and sampling for payload capture', href: '/data-capture' },
  { key: 'has_security_config', label: 'Review Security Settings', description: 'Configure metadata requirements, IP ACLs, and OIDC', href: '/security' },
  { key: 'has_tag', label: 'Create a Tag', description: 'Add taxonomy tags for classification and filtering', href: '/tags' },
]

type SectionDef = {
  id: string
  title: string
  subtitle: string
  icon: React.ComponentType<{ className?: string }>
  iconColor: string
  ringColor: string
  steps: Step[]
}

const SECTIONS: SectionDef[] = [
  {
    id: 'foundation',
    title: 'Foundation',
    subtitle: 'Organization, workspace, API key, first traffic, and baseline controls.',
    icon: Rocket,
    iconColor: 'text-blue-600 dark:text-blue-400',
    ringColor: 'bg-blue-100 ring-blue-200 dark:bg-blue-500/20 dark:ring-blue-500/30',
    steps: STEPS,
  },
  {
    id: 'finops',
    title: 'FinOps Readiness',
    subtitle: 'Budget notifications and billing cycles.',
    icon: DollarSign,
    iconColor: 'text-emerald-600 dark:text-emerald-400',
    ringColor: 'bg-emerald-100 ring-emerald-200 dark:bg-emerald-500/20 dark:ring-emerald-500/30',
    steps: FINOPS_STEPS,
  },
  {
    id: 'gateway',
    title: 'Gateway & Routing',
    subtitle: 'Providers, guardrails, and rate limits.',
    icon: Network,
    iconColor: 'text-violet-600 dark:text-violet-400',
    ringColor: 'bg-violet-100 ring-violet-200 dark:bg-violet-500/20 dark:ring-violet-500/30',
    steps: GATEWAY_STEPS,
  },
  {
    id: 'safety',
    title: 'Safety & Governance',
    subtitle: 'Tool policies, approvals, security posture, and tags.',
    icon: Shield,
    iconColor: 'text-amber-600 dark:text-amber-400',
    ringColor: 'bg-amber-100 ring-amber-200 dark:bg-amber-500/20 dark:ring-amber-500/30',
    steps: SAFETY_STEPS,
  },
]

/* ------------------------------------------------------------------ */
/*  Integrations                                                       */
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

const INTEGRATION_GROUPS: Array<{
  id: Integration['category']
  title: string
  description: string
}> = [
  { id: 'desktop_agents', title: 'Desktop Agents & MCP Clients', description: 'Claude, Codex, Cursor, Windsurf, and hosted coding tools.' },
  { id: 'gateway_clients', title: 'Gateway-Routed Clients', description: 'Tools sending inference through the RunLedger gateway.' },
  { id: 'telemetry_frameworks', title: 'Telemetry & Framework Hooks', description: 'App code, callback hooks, and orchestration frameworks.' },
]

const INTEGRATIONS: Integration[] = [
  {
    id: 'claude-code', name: 'Claude Code', subtitle: 'Anthropic CLI agent', category: 'desktop_agents', icon: Bot,
    steps: ['Add the RunLedger MCP server to your Claude Code configuration.', 'Restart Claude Code to pick up the new MCP server.', 'All Claude Code sessions will now report usage to RunLedger.'],
    configTitle: 'MCP Configuration (~/.claude.json)',
    configSnippet: `{\n  "mcpServers": {\n    "runledger": {\n      "command": "npx",\n      "args": ["-y", "runledger-mcp"],\n      "env": {\n        "RUNLEDGER_API_KEY": "rl_YOUR_API_KEY"\n      }\n    }\n  }\n}`,
  },
  {
    id: 'codex', name: 'Codex', subtitle: 'OpenAI CLI agent', category: 'desktop_agents', icon: Terminal,
    steps: ['Set your API base URL to the RunLedger gateway.', 'Use your RunLedger API key in place of the OpenAI key.', 'Run Codex as usual - requests are proxied and tracked.'],
    configTitle: 'Environment Variables',
    configSnippet: `export OPENAI_BASE_URL="https://gateway.runledger.app/v1"\nexport OPENAI_API_KEY="rl_YOUR_API_KEY"`,
  },
  {
    id: 'cursor', name: 'Cursor', subtitle: 'AI-powered IDE', category: 'desktop_agents', icon: MousePointer,
    steps: ['Create or edit the MCP config file in your project.', 'Add the RunLedger MCP server entry.', 'Restart Cursor to enable the integration.'],
    configTitle: '.cursor/mcp.json',
    configSnippet: `{\n  "mcpServers": {\n    "runledger": {\n      "command": "npx",\n      "args": ["-y", "runledger-mcp"],\n      "env": {\n        "RUNLEDGER_API_KEY": "rl_YOUR_API_KEY"\n      }\n    }\n  }\n}`,
  },
  {
    id: 'windsurf', name: 'Windsurf', subtitle: 'AI-powered IDE', category: 'desktop_agents', icon: Wind,
    steps: ['Open Windsurf settings and navigate to the AI provider section.', 'Set the API base URL to your RunLedger gateway endpoint.', 'Enter your RunLedger API key and select your preferred model.'],
    configTitle: 'Windsurf Settings (settings.json)',
    configSnippet: `{\n  "ai.provider": {\n    "baseUrl": "https://gateway.runledger.app/v1",\n    "apiKey": "rl_YOUR_API_KEY",\n    "model": "gpt-4o"\n  }\n}`,
  },
  {
    id: 'devin', name: 'Devin', subtitle: 'Autonomous coding agent', category: 'desktop_agents', icon: Cpu,
    steps: ['In the Devin dashboard, go to Settings > API Configuration.', 'Set the LLM proxy URL to your RunLedger gateway.', 'Save and re-launch your Devin session to apply.'],
    configTitle: 'Devin API Configuration',
    configSnippet: `LLM Proxy URL: https://gateway.runledger.app/v1\nAPI Key:       rl_YOUR_API_KEY\nWorkspace:     default`,
  },
  {
    id: 'litellm', name: 'LiteLLM', subtitle: 'LLM proxy gateway', category: 'gateway_clients', icon: Network,
    steps: ['Install the RunLedger callback package: pip install runledger-litellm', 'Add the RunLedger callback to your LiteLLM proxy config file.', 'Restart the LiteLLM proxy and verify the connection on the Gateway page.'],
    configTitle: 'litellm_settings (config.yaml)',
    configSnippet: `litellm_settings:\n  success_callback: ["runledger"]\n  runledger_api_key: "rl_YOUR_API_KEY"\n  runledger_api_base: "https://api.runledger.app"`,
  },
  {
    id: 'openwebui', name: 'Open WebUI', subtitle: 'Chat interface', category: 'gateway_clients', icon: Globe,
    steps: ['Navigate to Admin > Settings > Connections in Open WebUI.', 'Set the OpenAI-compatible API base URL to your RunLedger gateway endpoint.', 'Enter your RunLedger API key and save.'],
    configTitle: 'Open WebUI Connection Settings',
    configSnippet: `API Base URL: https://gateway.runledger.app/v1\nAPI Key:      rl_YOUR_API_KEY\nModel Filter: (leave empty to proxy all models)`,
  },
  {
    id: 'openhands', name: 'OpenHands', subtitle: 'AI coding agent', category: 'gateway_clients', icon: Code,
    steps: ['Set the LLM base URL environment variable to your RunLedger gateway.', 'Export your RunLedger API key as the provider key.', 'Launch the OpenHands agent - all calls are now routed through RunLedger.'],
    configTitle: 'Environment Variables',
    configSnippet: `export LLM_BASE_URL="https://gateway.runledger.app/v1"\nexport LLM_API_KEY="rl_YOUR_API_KEY"\nexport LLM_MODEL="gpt-4o"`,
  },
  {
    id: 'langgraph', name: 'LangGraph', subtitle: 'Agent orchestration', category: 'telemetry_frameworks', icon: GitBranch,
    steps: ['Install the RunLedger LangChain integration: pip install runledger-langchain', 'Add the RunLedger callback handler to your LangGraph agent.', 'Run your graph - each node invocation is tracked automatically.'],
    configTitle: 'Python Agent Code',
    configSnippet: `from runledger_langchain import RunLedgerCallbackHandler\n\nhandler = RunLedgerCallbackHandler(\n    api_key="rl_YOUR_API_KEY",\n)\n\n# Pass to your LangGraph agent\napp.invoke(input, config={"callbacks": [handler]})`,
  },
]

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const inputCls =
  'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100'

function CodeBlock({ title, code }: { title: string; code: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      toast.success('Copied to clipboard')
      setTimeout(() => setCopied(false), 2000)
    } catch { toast.error('Failed to copy') }
  }
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
      <div className="flex items-center justify-between bg-slate-100 px-4 py-2 dark:bg-slate-800">
        <span className="text-xs font-medium text-slate-600 dark:text-slate-300">{title}</span>
        <button onClick={handleCopy} className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-slate-500 transition-colors hover:bg-slate-200 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-200">
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

function SectionProgress({ done, total }: { done: number; total: number }) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
        <div className="h-full rounded-full bg-blue-500 transition-all duration-500" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{done}/{total}</span>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Main page                                                          */
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
  const [expandedSection, setExpandedSection] = useState<string | null>('foundation')

  useEffect(() => {
    if (!apiKey) return
    getOnboardingStatus(apiKey).then(setStatus).catch(() => toast.error('Failed to load onboarding status'))
    getDemoModeStatus(apiKey).then((state) => {
      setDemoStatus(state)
      if (state.profile === 'quick' || state.profile === 'full') setSelectedDemoProfile(state.profile)
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
      } catch {}
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
    } catch { toast.error('Failed to trigger demo seed') } finally { setSeeding(false) }
  }

  const handleReset = async () => {
    setResetting(true)
    try {
      const res = await triggerDemoReset(apiKey)
      setDemoStatus(res.state)
      toast.success(res.message)
    } catch { toast.error('Failed to trigger demo reset') } finally { setResetting(false) }
  }

  const sectionStats = useMemo(() => {
    if (!status) return {}
    const result: Record<string, { done: number; total: number }> = {}
    for (const section of SECTIONS) {
      const done = section.steps.filter(s => !!status[s.key]).length
      result[section.id] = { done, total: section.steps.length }
    }
    return result
  }, [status])

  if (!status) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    )
  }

  const active = INTEGRATIONS.find((i) => i.id === selectedIntegration)
  const demoProfiles = demoStatus?.available_profiles ?? []
  const manualProfile = demoProfiles.find((p) => p.id === 'manual')
  const automatedProfiles = demoProfiles.filter((p) => p.kind === 'automated')
  const showConnectionsSection = searchParams.get('section') === 'connections'
  const groupedIntegrations = INTEGRATION_GROUPS.map((g) => ({ ...g, items: INTEGRATIONS.filter((i) => i.category === g.id) }))

  return (
    <div className="space-y-5">
      {/* ── Hero ── */}
      <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="rounded-xl bg-blue-100 p-2 ring-1 ring-blue-200 dark:bg-blue-500/20 dark:ring-blue-500/30">
              <Rocket className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">Onboarding</h1>
              <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">
                Complete these steps to get the most out of RunLedger — from foundation to integrations.
              </p>
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-4 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-slate-600 dark:text-slate-300">{status.completed} of {status.total} steps completed</span>
            <span className="font-bold text-blue-600 dark:text-blue-400">{status.pct}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
            <div className="h-full rounded-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-700" style={{ width: `${status.pct}%` }} />
          </div>
        </div>

        {/* Section KPIs */}
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {SECTIONS.map(sec => {
            const stats = sectionStats[sec.id]
            const Icon = sec.icon
            const allDone = stats && stats.done === stats.total
            return (
              <button
                key={sec.id}
                onClick={() => setExpandedSection(expandedSection === sec.id ? null : sec.id)}
                className={`rounded-lg border px-3 py-2 text-left transition-all ${
                  expandedSection === sec.id
                    ? 'border-blue-300 bg-blue-50/80 dark:border-blue-700 dark:bg-blue-950/30'
                    : 'border-slate-200 bg-slate-50/80 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800/60 dark:hover:border-slate-600'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <Icon className={`h-3.5 w-3.5 ${sec.iconColor}`} />
                  <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">{sec.title}</span>
                </div>
                <div className="mt-1.5 flex items-center gap-2">
                  {allDone ? (
                    <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400">Complete</span>
                  ) : stats ? (
                    <SectionProgress done={stats.done} total={stats.total} />
                  ) : null}
                </div>
              </button>
            )
          })}
        </div>
      </section>

      {showConnectionsSection && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/80 p-3 text-sm text-blue-800 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-200">
          The legacy <span className="font-semibold">Integrations</span> route now redirects here.
        </div>
      )}

      {status.pct === 100 && (
        <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          <div>
            <p className="text-sm font-semibold">You&apos;re all set!</p>
            <p className="text-xs opacity-80">RunLedger is fully configured. Explore integrations below to connect external tools.</p>
          </div>
        </div>
      )}

      {/* ── Checklist Sections (accordion) ── */}
      {SECTIONS.map((sec, idx) => {
        const Icon = sec.icon
        const stats = sectionStats[sec.id]
        const isOpen = expandedSection === sec.id
        return (
          <section key={sec.id} className="rounded-xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
            <button
              onClick={() => setExpandedSection(isOpen ? null : sec.id)}
              className="flex w-full items-center justify-between gap-3 p-4"
            >
              <div className="flex items-center gap-3">
                <div className={`rounded-lg p-1.5 ring-1 ${sec.ringColor}`}>
                  <Icon className={`h-4 w-4 ${sec.iconColor}`} />
                </div>
                <div className="text-left">
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                      <span className="mr-1.5 text-xs text-slate-400">{idx + 1}.</span>
                      {sec.title}
                    </h2>
                    {stats && stats.done === stats.total && (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                    )}
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">{sec.subtitle}</p>
                </div>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                {stats && <SectionProgress done={stats.done} total={stats.total} />}
                {isOpen ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
              </div>
            </button>
            {isOpen && (
              <div className="border-t border-slate-100 dark:border-slate-800">
                {sec.steps.map((step) => {
                  const done = !!status[step.key]
                  return (
                    <Link
                      key={step.key}
                      href={step.href}
                      className="flex items-center gap-3 border-b border-slate-50 px-4 py-3 transition-colors last:border-b-0 hover:bg-slate-50 dark:border-slate-800/50 dark:hover:bg-slate-800/50"
                    >
                      {done ? (
                        <CheckCircle2 className="h-4.5 w-4.5 shrink-0 text-emerald-500" />
                      ) : (
                        <Circle className="h-4.5 w-4.5 shrink-0 text-slate-300 dark:text-slate-600" />
                      )}
                      <div className="min-w-0 flex-1">
                        <p className={`text-sm font-medium ${done ? 'text-slate-400 line-through dark:text-slate-500' : 'text-slate-800 dark:text-slate-200'}`}>
                          {step.label}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{step.description}</p>
                      </div>
                      {done ? (
                        <span className="shrink-0 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400">
                          Done
                        </span>
                      ) : (
                        <ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-300 dark:text-slate-600" />
                      )}
                    </Link>
                  )
                })}
              </div>
            )}
          </section>
        )
      })}

      {/* ── Observe & Monitor ── */}
      <section className="rounded-xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
        <div className="flex items-center gap-3 mb-3">
          <div className="rounded-lg bg-teal-100 p-1.5 ring-1 ring-teal-200 dark:bg-teal-500/20 dark:ring-teal-500/30">
            <Eye className="h-4 w-4 text-teal-600 dark:text-teal-400" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
              <span className="mr-1.5 text-xs text-slate-400">5.</span>Observe & Monitor
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">Verify your observability surfaces are receiving data.</p>
          </div>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: 'Dashboard', desc: 'Workspace activity overview', href: '/analytics' },
            { label: 'Runs', desc: 'Run list and execution traces', href: '/runs' },
            { label: 'Analytics', desc: 'Volume, latency, model usage', href: '/analytics' },
            { label: 'Monitoring', desc: 'Alert rules and notifications', href: '/alert-rules' },
          ].map(item => (
            <Link
              key={item.label}
              href={item.href}
              className="group rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2.5 transition-all hover:border-teal-300 hover:bg-teal-50/50 dark:border-slate-700 dark:bg-slate-800/60 dark:hover:border-teal-700 dark:hover:bg-teal-950/20"
            >
              <p className="text-sm font-medium text-slate-800 group-hover:text-teal-700 dark:text-slate-200 dark:group-hover:text-teal-300">{item.label}</p>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{item.desc}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* ── Integration Path Selector ── */}
      <section id="connection-paths" className="space-y-4">
        <div className="rounded-xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
          <div className="flex items-center gap-3 mb-3">
            <div className="rounded-lg bg-indigo-100 p-1.5 ring-1 ring-indigo-200 dark:bg-indigo-500/20 dark:ring-indigo-500/30">
              <Sparkles className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                <span className="mr-1.5 text-xs text-slate-400">6.</span>Connect Your Tools
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Pick the path that matches how your tool connects to RunLedger.</p>
            </div>
          </div>

          {groupedIntegrations.map((group) => (
            <div key={group.id} className="mt-4 first:mt-0">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{group.title}</h3>
              <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-5">
                {group.items.map((integration) => {
                  const Icon = integration.icon
                  const isSelected = selectedIntegration === integration.id
                  return (
                    <button
                      key={integration.id}
                      onClick={() => setSelectedIntegration(isSelected ? null : integration.id)}
                      className={`flex items-center gap-2.5 rounded-lg border px-3 py-2.5 text-left transition-all ${
                        isSelected
                          ? 'border-blue-400 bg-blue-50 shadow-sm dark:border-blue-500 dark:bg-blue-950/40'
                          : 'border-slate-200 bg-slate-50/80 hover:border-blue-300 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800/60 dark:hover:border-blue-600 dark:hover:bg-slate-800'
                      }`}
                    >
                      <Icon className={`h-4 w-4 shrink-0 ${isSelected ? 'text-blue-600 dark:text-blue-400' : 'text-slate-400'}`} />
                      <div className="min-w-0">
                        <p className={`text-sm font-medium truncate ${isSelected ? 'text-blue-700 dark:text-blue-300' : 'text-slate-700 dark:text-slate-200'}`}>{integration.name}</p>
                        <p className="text-[10px] text-slate-400 truncate">{integration.subtitle}</p>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Selected integration instructions */}
        {active && (
          <div className="rounded-xl border border-blue-200 bg-white/90 p-5 shadow-sm dark:border-blue-800 dark:bg-slate-900">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <active.icon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                <h3 className="text-base font-semibold text-slate-900 dark:text-white">Connect {active.name}</h3>
              </div>
              <button onClick={() => setSelectedIntegration(null)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
                <ChevronUp className="h-5 w-5" />
              </button>
            </div>
            <ol className="mb-4 space-y-2">
              {active.steps.map((step, i) => (
                <li key={i} className="flex items-start gap-2.5 text-sm text-slate-700 dark:text-slate-300">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-[10px] font-bold text-blue-700 dark:bg-blue-900/60 dark:text-blue-300">
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
            <CodeBlock title={active.configTitle} code={active.configSnippet} />
            <div className="mt-4 flex flex-wrap gap-2">
              {[
                { label: 'Validate in Telemetry', href: '/monitoring/telemetry' },
                { label: 'Check Runs', href: '/runs' },
                { label: 'Request Explorer', href: '/request-explorer' },
              ].map(link => (
                <Link key={link.href} href={link.href} className="rounded-full border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:text-slate-300 dark:hover:border-blue-700 dark:hover:text-blue-300">
                  {link.label}
                </Link>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* ── Demo Mode ── */}
      <section className="rounded-xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-pink-100 p-1.5 ring-1 ring-pink-200 dark:bg-pink-500/20 dark:ring-pink-500/30">
              <FlaskConical className="h-4 w-4 text-pink-600 dark:text-pink-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                <span className="mr-1.5 text-xs text-slate-400">7.</span>Demo Mode & Labs
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Seed sample data to explore RunLedger, or reset to start fresh.
              </p>
            </div>
          </div>
          {demoStatus && (
            <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase ${
              demoStatus.status === 'running' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' :
              demoStatus.status === 'completed' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' :
              'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
            }`}>
              {demoStatus.status}
            </span>
          )}
        </div>

        {automatedProfiles.length > 0 && (
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {automatedProfiles.map((profile) => {
              const selected = selectedDemoProfile === profile.id
              return (
                <button
                  key={profile.id}
                  type="button"
                  onClick={() => setSelectedDemoProfile(profile.id as 'full' | 'quick')}
                  className={`rounded-lg border p-3 text-left transition-all ${
                    selected
                      ? 'border-blue-400 bg-blue-50 dark:border-blue-500 dark:bg-blue-950/40'
                      : 'border-slate-200 bg-slate-50 hover:border-blue-300 dark:border-slate-700 dark:bg-slate-800/60 dark:hover:border-blue-600'
                  }`}
                >
                  <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{profile.label}</p>
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{profile.description}</p>
                </button>
              )
            })}
          </div>
        )}

        {demoStatus && (
          <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/60">
            <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
              {demoStatus.profile ? `${demoStatus.profile.toUpperCase()} ` : ''}
              {demoStatus.action ? `${demoStatus.action.toUpperCase()}: ` : ''}
              {demoStatus.message}
            </p>
            <p className="mt-1 text-[10px] text-slate-400">Updated {new Date(demoStatus.updated_at).toLocaleString()}</p>
            <div className="mt-2 flex gap-3">
              <a href={demoStatus.runbook_path} target="_blank" rel="noreferrer" className="text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300">
                Open demo runbook
              </a>
              {manualProfile && (
                <a href={manualProfile.runbook_path} target="_blank" rel="noreferrer" className="text-xs font-medium text-slate-600 hover:text-slate-700 dark:text-slate-300 dark:hover:text-slate-100">
                  Open labs workbook
                </a>
              )}
            </div>
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            onClick={handleSeed}
            disabled={seeding || resetting}
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {seeding ? <Play className="h-3.5 w-3.5 animate-pulse" /> : <Play className="h-3.5 w-3.5" />}
            {seeding ? 'Seeding...' : 'Seed Demo Data'}
          </button>
          <button
            onClick={handleReset}
            disabled={seeding || resetting}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            {resetting ? <RotateCcw className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
            {resetting ? 'Resetting...' : 'Reset Demo Data'}
          </button>
        </div>
      </section>
    </div>
  )
}
