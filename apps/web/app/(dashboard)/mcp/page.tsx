'use client'

import { useSession } from 'next-auth/react'
import { useState } from 'react'
import { Key, Terminal, CheckCheck } from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

export default function McpPage() {
  const { data: session } = useSession()
  const { canManageOrgSettings } = useRole()
  const workspaceName = (session as Record<string, unknown> | null)?.workspaceName as string | undefined

  const [mcpSelectedKey, setMcpSelectedKey] = useState('')
  const [mcpCopied, setMcpCopied] = useState<'cli' | 'json' | null>(null)

  const mcpKey = mcpSelectedKey || ''
  const mcpKeyDisplay = mcpKey || '<your-api-key>'

  if (!canManageOrgSettings) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">MCP Setup</h1>
        <p className="mt-4 text-sm text-slate-500">MCP configuration is an organization-admin function.</p>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6 max-w-3xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">MCP Setup</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Connect Claude Desktop or Claude Code to your RunLedger workspace via the Model Context Protocol.
            All MCP tool calls are attributed to <strong className="text-slate-700 dark:text-slate-200">{workspaceName ?? 'your workspace'}</strong>.
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-violet-100 px-2.5 py-1 text-xs font-semibold text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
          /mcp
        </span>
      </div>

      {/* Key selector */}
      <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-700 dark:bg-slate-800/40 space-y-3">
        <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Select API key to use</p>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          The key below will be pre-filled in the snippets. It must belong to{' '}
          <strong className="text-violet-600 dark:text-violet-400">{workspaceName ?? 'this workspace'}</strong>.
        </p>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={mcpSelectedKey}
            onChange={(e) => setMcpSelectedKey(e.target.value)}
            placeholder="Paste your API key here (rl_…)"
            className={`${inputCls} flex-1 font-mono`}
          />
          <a
            href="/api-keys"
            className="shrink-0 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 hover:border-violet-300 hover:text-violet-700 dark:hover:border-violet-600 dark:hover:text-violet-400 transition-colors"
          >
            + Create key
          </a>
        </div>
        {!mcpKey && (
          <p className="text-[11px] text-amber-600 dark:text-amber-400">
            Paste an API key or create a new one — snippets will auto-fill.
          </p>
        )}
      </div>

      {/* Claude Code CLI */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="flex items-center gap-2.5 border-b border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/60">
          <Terminal className="h-4 w-4 text-violet-600 dark:text-violet-400" />
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Claude Code</h3>
          <span className="text-xs text-slate-400">— one command to register</span>
        </div>
        <div className="p-4 space-y-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Run this once in your terminal. Claude Code will remember the server across sessions.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 overflow-x-auto rounded-lg bg-slate-900 px-3 py-2.5 font-mono text-xs text-emerald-400 dark:bg-slate-950">
              {`RUNLEDGER_API_KEY=${mcpKeyDisplay} claude mcp add --transport http runledger ${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/mcp`}
            </code>
            <button
              onClick={async () => {
                await navigator.clipboard.writeText(
                  `RUNLEDGER_API_KEY=${mcpKeyDisplay} claude mcp add --transport http runledger ${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/mcp`
                )
                setMcpCopied('cli')
                setTimeout(() => setMcpCopied(null), 2000)
              }}
              className="shrink-0 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-violet-300 hover:text-violet-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-violet-600 dark:hover:text-violet-400"
            >
              {mcpCopied === 'cli' ? <CheckCheck className="h-3.5 w-3.5 text-emerald-500" /> : 'Copy'}
            </button>
          </div>
        </div>
      </div>

      {/* Claude Desktop JSON */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="flex items-center gap-2.5 border-b border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/60">
          <Key className="h-4 w-4 text-violet-600 dark:text-violet-400" />
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Claude Desktop</h3>
          <span className="text-xs text-slate-400">— add to <code className="font-mono">claude_desktop_config.json</code></span>
        </div>
        <div className="p-4 space-y-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Add the block below to your Claude Desktop config file, then restart the app.
          </p>
          <div className="flex items-start gap-2">
            <pre className="flex-1 overflow-x-auto rounded-lg bg-slate-900 px-3 py-3 font-mono text-xs text-slate-300 dark:bg-slate-950 dark:text-slate-200">{`{
  "mcpServers": {
    "runledger": {
      "url": "${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/mcp",
      "env": {
        "RUNLEDGER_API_KEY": "${mcpKeyDisplay}"
      }
    }
  }
}`}</pre>
            <button
              onClick={async () => {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
                const json = `{\n  "mcpServers": {\n    "runledger": {\n      "url": "${apiUrl}/mcp",\n      "env": {\n        "RUNLEDGER_API_KEY": "${mcpKeyDisplay}"\n      }\n    }\n  }\n}`
                await navigator.clipboard.writeText(json)
                setMcpCopied('json')
                setTimeout(() => setMcpCopied(null), 2000)
              }}
              className="shrink-0 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-violet-300 hover:text-violet-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-violet-600 dark:hover:text-violet-400"
            >
              {mcpCopied === 'json' ? <CheckCheck className="h-3.5 w-3.5 text-emerald-500" /> : 'Copy'}
            </button>
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/30 px-4 py-3 text-xs text-slate-500 dark:text-slate-400 space-y-1">
        <p className="font-semibold text-slate-700 dark:text-slate-300">How it works</p>
        <ul className="list-disc list-inside space-y-0.5 pl-1">
          <li>The MCP server exposes RunLedger tools to Claude (query runs, budgets, analytics).</li>
          <li>All tool calls are authenticated with your workspace API key — data is scoped to <strong className="text-violet-600 dark:text-violet-400">{workspaceName ?? 'this workspace'}</strong>.</li>
          <li>Switch workspaces by changing <code className="font-mono">RUNLEDGER_API_KEY</code> to a key from the target workspace.</li>
        </ul>
      </div>
    </div>
  )
}
