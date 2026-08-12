'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import Link from 'next/link'
import {
  Rocket, CheckCircle2, Circle, Network, Globe, Code,
  GitBranch, Bot, Terminal, MousePointer, Wind, Cpu,
  Copy, Check, ChevronDown, ChevronUp,
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

/* ------------------------------------------------------------------ */
/*  Integration definitions                                           */
/* ------------------------------------------------------------------ */

interface Integration {
  id: string
  name: string
  subtitle: string
  icon: React.ComponentType<{ className?: string }>
  steps: string[]
  configTitle: string
  configSnippet: string
}

const INTEGRATIONS: Integration[] = [
  {
    id: 'litellm',
    name: 'LiteLLM',
    subtitle: 'LLM proxy gateway',
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

  return (
    <div className="mx-auto max-w-2xl space-y-6 py-10">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Rocket className="h-8 w-8 text-blue-500" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Getting Started</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Complete these steps to get the most out of RunLedger</p>
        </div>
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

      {/* ---- Integration Path Selector ---- */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold tracking-tight">Choose Your Integration</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Select the tool you want to connect to RunLedger for tailored setup instructions.
        </p>
        <div className="grid grid-cols-3 gap-3">
          {INTEGRATIONS.map((integration) => {
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

      {/* ---- Integration-specific instructions ---- */}
      {active && (
        <div className="rounded-2xl border border-blue-200 bg-white/90 p-6 shadow-sm dark:border-blue-800 dark:bg-slate-900">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold">Connect {active.name} to RunLedger</h3>
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
        </div>
      )}

      {/* ---- Steps checklist ---- */}
      <div className="space-y-3">
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

      {/* ---- Demo mode ---- */}
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="mb-1 font-semibold">Demo Mode</h2>
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
