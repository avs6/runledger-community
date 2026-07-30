'use client'

import { useSession } from 'next-auth/react'
import { useState } from 'react'
import {
  Bot,
  CheckCheck,
  ClipboardCheck,
  Code2,
  Key,
  Laptop,
  RadioTower,
  Server,
  ShieldCheck,
  Sparkles,
  Terminal,
  Workflow,
} from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'

type Connector = {
  id: string
  name: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  description: string
  configTitle: string
  config: (apiUrl: string, apiKey: string) => string
}

const inputCls =
  'rounded-xl border border-slate-300 bg-white/80 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 shadow-sm outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200'

const mcpTools = [
  'runledger.budget_check',
  'runledger.policy_check',
  'runledger.recommend_route',
  'runledger.record_run_start',
  'runledger.record_span',
  'runledger.record_tool_call',
  'runledger.record_model_call',
  'runledger.record_outcome',
  'runledger.query_runs',
  'runledger.query_costs',
  'runledger.query_optimizations',
  'runledger.filter_mcp_tool',
]

const resources = [
  'runledger://orgs/{org_id}/summary',
  'runledger://workspaces/{workspace_id}/budget',
  'runledger://workspaces/{workspace_id}/routes',
  'runledger://workspaces/{workspace_id}/provider-profiles',
  'runledger://workspaces/{workspace_id}/recent-runs',
  'runledger://workspaces/{workspace_id}/optimization-recommendations',
  'runledger://runs/{run_id}/trace',
  'runledger://policies/{workspace_id}/tool-policy',
  'runledger://docs/agent-instructions',
]

const prompts = [
  'runledger_start_agent_task',
  'runledger_choose_model_route',
  'runledger_record_task_outcome',
  'runledger_optimize_prompt',
  'runledger_debug_expensive_request',
]

const connectors: Connector[] = [
  {
    id: 'claude-desktop',
    name: 'Claude Desktop',
    label: 'Desktop MCP',
    icon: Bot,
    description: 'Add RunLedger as an HTTP MCP server for local Claude workflows.',
    configTitle: 'claude_desktop_config.json',
    config: (apiUrl, apiKey) => `{
  "mcpServers": {
    "runledger": {
      "url": "${apiUrl}/mcp",
      "env": {
        "RUNLEDGER_API_KEY": "${apiKey}"
      }
    }
  }
}`,
  },
  {
    id: 'claude-code',
    name: 'Claude Code',
    label: 'CLI install',
    icon: Terminal,
    description: 'Register RunLedger once, then every Claude Code task can log cost and policy checks.',
    configTitle: 'Terminal command',
    config: (apiUrl, apiKey) =>
      `RUNLEDGER_API_KEY=${apiKey} claude mcp add --transport http runledger ${apiUrl}/mcp`,
  },
  {
    id: 'cursor',
    name: 'Cursor',
    label: 'IDE config',
    icon: Code2,
    description: 'Use RunLedger tools and default rules inside Cursor agent sessions.',
    configTitle: '.cursor/mcp.json',
    config: (apiUrl, apiKey) => `{
  "mcpServers": {
    "runledger": {
      "url": "${apiUrl}/mcp",
      "env": {
        "RUNLEDGER_API_KEY": "${apiKey}"
      }
    }
  }
}`,
  },
  {
    id: 'windsurf',
    name: 'Windsurf',
    label: 'Cascade rules',
    icon: Workflow,
    description: 'Connect Cascade to RunLedger and ship a workspace rule file with every repo.',
    configTitle: '.windsurf/mcp.json',
    config: (apiUrl, apiKey) => `{
  "servers": {
    "runledger": {
      "url": "${apiUrl}/mcp",
      "headers": {
        "Authorization": "Bearer ${apiKey}"
      }
    }
  }
}`,
  },
  {
    id: 'codex',
    name: 'OpenAI Codex',
    label: 'Agent hook',
    icon: Sparkles,
    description: 'Use a repo instruction file plus MCP endpoint so spawned agents report to RunLedger.',
    configTitle: 'config.toml / AGENTS.md hint',
    config: (apiUrl, apiKey) => `[mcp_servers.runledger]
url = "${apiUrl}/mcp"
env = { RUNLEDGER_API_KEY = "${apiKey}" }

# Add to AGENTS.md:
# Use RunLedger MCP tools for budget checks, policy checks, spans, model calls, and outcomes.`,
  },
  {
    id: 'devin',
    name: 'Devin',
    label: 'Hosted agent',
    icon: Laptop,
    description: 'Give Devin a workspace-scoped key and repo instruction file for task-level reporting.',
    configTitle: 'Environment + instruction block',
    config: (apiUrl, apiKey) => `RUNLEDGER_BASE_URL=${apiUrl}
RUNLEDGER_API_KEY=${apiKey}

Instruction:
Before each task call runledger.budget_check, record run start, model calls, tool calls, and final outcome.`,
  },
  {
    id: 'http',
    name: 'Direct HTTP MCP',
    label: 'Universal',
    icon: RadioTower,
    description: 'Use this for LiteLLM, Open WebUI, LangGraph, OpenHands, Dify, n8n, and custom agents.',
    configTitle: 'HTTP endpoint',
    config: (apiUrl, apiKey) => `MCP endpoint: ${apiUrl}/mcp
Authorization: Bearer ${apiKey}
Transport: streamable HTTP
Scope: current workspace API key`,
  },
  {
    id: 'stdio',
    name: 'Local stdio Bridge',
    label: 'Local bridge',
    icon: Server,
    description: 'For clients that only support local stdio MCP servers, proxy stdio to RunLedger HTTP MCP.',
    configTitle: 'stdio bridge command',
    config: (apiUrl, apiKey) => `RUNLEDGER_BASE_URL=${apiUrl}
RUNLEDGER_API_KEY=${apiKey}
python scripts/runledger/mcp_stdio_bridge.py`,
  },
]

export default function McpPage() {
  const { data: session } = useSession()
  const { canManageOrgSettings } = useRole()
  const workspaceName = (session as Record<string, unknown> | null)?.workspaceName as string | undefined
  const workspaceId = (session as Record<string, unknown> | null)?.workspaceId as string | undefined
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8201'

  const [apiKey, setApiKey] = useState('')
  const [selectedId, setSelectedId] = useState('claude-desktop')
  const [copied, setCopied] = useState<string | null>(null)

  const selected = connectors.find((item) => item.id === selectedId) ?? connectors[0]
  const resolvedKey = apiKey || '<workspace-api-key>'
  const snippet = selected.config(apiUrl, resolvedKey)

  async function copy(value: string, id: string) {
    await navigator.clipboard.writeText(value)
    setCopied(id)
    setTimeout(() => setCopied(null), 1800)
  }

  if (!canManageOrgSettings) {
    return (
      <div className="max-w-3xl p-8">
        <h1 className="text-2xl font-semibold text-slate-950">MCP Servers</h1>
        <p className="mt-3 text-sm text-slate-600">
          MCP configuration is available to organization admins and workspace admins.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-8 p-8">
      <div className="max-w-5xl">
        <span className="inline-flex rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">
          Phase 1A integration surface
        </span>
        <h1 className="mt-3 text-3xl font-semibold text-slate-950">MCP Servers</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          Connect IDEs, desktop agents, hosted agents, model gateways, and workflow tools to RunLedger.
          Use RunLedger inline for budget/policy/routing decisions and out of band for observability,
          FinOps, optimization, and request exploration.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="rounded-2xl bg-blue-100 p-2 text-blue-700">
              <Key className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-950">Setup Wizard</h2>
              <p className="mt-1 text-sm text-slate-600">
                Choose a tool, paste or create a workspace key, copy the generated config, then run a smoke test.
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {connectors.map((connector) => {
              const Icon = connector.icon
              const isSelected = connector.id === selected.id
              return (
                <button
                  key={connector.id}
                  type="button"
                  onClick={() => setSelectedId(connector.id)}
                  className={`rounded-2xl border p-4 text-left transition ${
                    isSelected
                      ? 'border-blue-300 bg-blue-50 shadow-sm ring-2 ring-blue-100'
                      : 'border-slate-200 bg-slate-50/70 hover:border-blue-200 hover:bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <Icon className={`h-5 w-5 ${isSelected ? 'text-blue-700' : 'text-slate-500'}`} />
                    <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold text-slate-500">
                      {connector.label}
                    </span>
                  </div>
                  <p className="mt-3 text-sm font-semibold text-slate-950">{connector.name}</p>
                  <p className="mt-1 text-xs leading-5 text-slate-600">{connector.description}</p>
                </button>
              )
            })}
          </div>

          <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="grid gap-4 md:grid-cols-[1fr_auto]">
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Workspace API key
                </span>
                <input
                  type="text"
                  value={apiKey}
                  onChange={(event) => setApiKey(event.target.value)}
                  placeholder="Paste a workspace-scoped key, for example rl_..."
                  className={`${inputCls} w-full font-mono`}
                />
              </label>
              <a
                href="/api-keys"
                className="self-end rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
              >
                Create key
              </a>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              Current workspace: <span className="font-semibold text-slate-700">{workspaceName ?? 'selected workspace'}</span>
              {workspaceId ? <span className="font-mono"> ({workspaceId})</span> : null}
            </p>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-950">{selected.name}</h2>
              <p className="mt-1 text-sm text-slate-600">{selected.configTitle}</p>
            </div>
            <button
              type="button"
              onClick={() => copy(snippet, selected.id)}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-blue-300 hover:text-blue-700"
            >
              {copied === selected.id ? <CheckCheck className="h-4 w-4 text-emerald-600" /> : <ClipboardCheck className="h-4 w-4" />}
              {copied === selected.id ? 'Copied' : 'Copy'}
            </button>
          </div>
          <pre className="mt-4 max-h-[460px] overflow-auto rounded-2xl bg-slate-950 p-4 text-xs leading-6 text-blue-50 shadow-inner">
            {snippet}
          </pre>
          <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-xs leading-5 text-slate-700">
            <p className="font-semibold text-slate-950">Smoke test</p>
            <p className="mt-1">
              After connecting, ask the agent to use RunLedger to check budget, start a task, record one tool call,
              and close the task outcome. The run should appear in Runs and Request Explorer.
            </p>
          </div>
        </section>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-blue-700" />
            <h2 className="text-lg font-semibold text-slate-950">MCP Tools</h2>
          </div>
          <p className="mt-1 text-sm text-slate-600">Inline control and out-of-band telemetry.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {mcpTools.map((item) => (
              <code key={item} className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] text-slate-700">
                {item}
              </code>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <Server className="h-5 w-5 text-blue-700" />
            <h2 className="text-lg font-semibold text-slate-950">Resources</h2>
          </div>
          <p className="mt-1 text-sm text-slate-600">Read-only context agents can fetch when diagnosing work.</p>
          <div className="mt-4 space-y-2">
            {resources.map((item) => (
              <code key={item} className="block rounded-xl bg-slate-100 px-3 py-2 text-[11px] text-slate-700">
                {item}
              </code>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-blue-700" />
            <h2 className="text-lg font-semibold text-slate-950">Prompts</h2>
          </div>
          <p className="mt-1 text-sm text-slate-600">Reusable agent workflows for consistent RunLedger behavior.</p>
          <div className="mt-4 space-y-2">
            {prompts.map((item) => (
              <code key={item} className="block rounded-xl bg-slate-100 px-3 py-2 text-[11px] text-slate-700">
                {item}
              </code>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <RadioTower className="h-5 w-5 text-blue-700" />
          <h2 className="text-lg font-semibold text-slate-950">Connection Modes</h2>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {[
            ['Direct HTTP MCP', `${apiUrl}/mcp`, 'Best for Claude, Cursor, hosted agents, and modern MCP clients.'],
            ['Local stdio bridge', 'scripts/runledger/mcp_stdio_bridge.py', 'Best for desktop tools that only launch local MCP processes.'],
            ['SSE compatibility', `${apiUrl}/mcp`, 'Use streamable HTTP today; keep SSE-compatible clients pointed at the MCP endpoint.'],
          ].map(([title, value, body]) => (
            <div key={title} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-950">{title}</p>
              <code className="mt-2 block rounded-lg bg-white px-2 py-1 text-[11px] text-slate-600">{value}</code>
              <p className="mt-2 text-xs leading-5 text-slate-600">{body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
