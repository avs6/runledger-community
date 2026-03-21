'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Wrench, Plus, Trash2, RefreshCw, ShieldCheck } from 'lucide-react'
import { listToolRegistry, upsertToolRegistry, deleteToolRegistry } from '@/lib/api'
import type { ToolRegistryResponse } from '@/types/api'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

const POLICY_COLORS: Record<string, string> = {
  audit: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  block: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  allow: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  require_approval: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
}

export default function ToolRegistryPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey

  const [tools, setTools] = useState<ToolRegistryResponse[]>([])
  const [loading, setLoading] = useState(true)

  const [showForm, setShowForm] = useState(false)
  const [newToolName, setNewToolName] = useState('')
  const [newToolPolicy, setNewToolPolicy] = useState('audit')
  const [newToolDesc, setNewToolDesc] = useState('')
  const [registeringTool, setRegisteringTool] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const data = await listToolRegistry(apiKey)
      setTools(data.items)
    } catch {
      toast.error('Failed to load tool registry')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { load() }, [load])

  async function handleRegisterTool(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !newToolName.trim()) return
    setRegisteringTool(true)
    try {
      await upsertToolRegistry(apiKey, {
        tool_name: newToolName.trim(),
        policy: newToolPolicy,
        description: newToolDesc.trim() || null,
      })
      await load()
      setNewToolName('')
      setNewToolDesc('')
      setNewToolPolicy('audit')
      setShowForm(false)
      toast.success('Tool registered')
    } catch {
      toast.error('Failed to register tool')
    } finally {
      setRegisteringTool(false)
    }
  }

  async function handleDeleteTool(toolName: string) {
    if (!apiKey || !confirm(`Remove "${toolName}" from the registry?`)) return
    try {
      await deleteToolRegistry(apiKey, toolName)
      setTools((prev) => prev.filter((t) => t.tool_name !== toolName))
      toast.success('Tool removed')
    } catch {
      toast.error('Failed to remove tool')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <RefreshCw className="h-5 w-5 animate-spin text-slate-400" />
      </div>
    )
  }

  return (
    <div className="space-y-8 max-w-4xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Wrench className="h-5 w-5 text-teal-600 dark:text-teal-400" />
            <h1 className="text-2xl font-bold tracking-tight dark:text-white">Tool Registry</h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Register and govern the tools available to agents in this workspace. Set audit, block, or allow policies per tool.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="shrink-0 flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-teal-700 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            {showForm ? 'Cancel' : 'Register Tool'}
          </button>
        </div>
      </div>

      {/* Add form */}
      {showForm && (
        <div className="rounded-xl border border-teal-200 dark:border-teal-800 bg-teal-50/50 dark:bg-teal-900/10 p-5">
          <h3 className="text-sm font-semibold text-teal-800 dark:text-teal-300 mb-3">Register a tool</h3>
          <form onSubmit={handleRegisterTool} className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500 dark:text-gray-400">Tool name *</label>
              <input
                type="text"
                placeholder="e.g. search_web"
                value={newToolName}
                onChange={(e) => setNewToolName(e.target.value)}
                className={inputCls}
                required
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500 dark:text-gray-400">Policy</label>
              <select value={newToolPolicy} onChange={(e) => setNewToolPolicy(e.target.value)} className={inputCls}>
                <option value="audit">audit — log all calls</option>
                <option value="allow">allow — no restrictions</option>
                <option value="block">block — deny all calls</option>
                <option value="require_approval">require_approval — manual review</option>
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500 dark:text-gray-400">Description (optional)</label>
              <input
                type="text"
                placeholder="What does this tool do?"
                value={newToolDesc}
                onChange={(e) => setNewToolDesc(e.target.value)}
                className={inputCls}
              />
            </div>
            <div className="sm:col-span-3">
              <button
                type="submit"
                disabled={registeringTool || !newToolName.trim()}
                className="w-full rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50 transition-colors"
              >
                {registeringTool ? 'Registering…' : 'Register Tool'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Tool list */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        {tools.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Wrench className="h-8 w-8 text-slate-300 dark:text-slate-600" />
            <div className="text-center">
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">No tools registered yet</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Register tools to enable governance and audit logging.</p>
            </div>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Tool Name</th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Description</th>
                <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Policy</th>
                <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Registered</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
              {tools.map((tool) => (
                <tr key={tool.tool_name} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                  <td className="px-4 py-2.5 font-mono text-sm font-semibold dark:text-slate-200">{tool.tool_name}</td>
                  <td className="px-4 py-2.5 text-xs text-slate-500 dark:text-slate-400 max-w-[280px] truncate">
                    {tool.description ?? <span className="italic text-slate-300 dark:text-slate-600">—</span>}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${POLICY_COLORS[tool.policy] ?? 'bg-slate-100 text-slate-500'}`}>
                      {tool.policy}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right text-xs text-slate-400 whitespace-nowrap">
                    {new Date(tool.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <button
                      onClick={() => handleDeleteTool(tool.tool_name)}
                      className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      title="Remove tool"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Info box */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4">
        <div className="flex items-start gap-2">
          <ShieldCheck className="h-4 w-4 text-teal-600 dark:text-teal-400 mt-0.5 shrink-0" />
          <div className="text-sm text-slate-600 dark:text-slate-300">
            <p className="font-medium mb-1">Policy enforcement</p>
            <ul className="space-y-1 text-xs text-slate-500 dark:text-slate-400 list-disc list-inside">
              <li><strong>audit</strong> — calls are logged and visible in run traces, no restriction.</li>
              <li><strong>allow</strong> — calls proceed without any logging overhead.</li>
              <li><strong>block</strong> — calls are rejected and a security event is recorded.</li>
              <li><strong>require_approval</strong> — calls are held pending manual review (not yet enforced at runtime).</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
