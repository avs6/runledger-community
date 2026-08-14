'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Wrench, Plus, Trash2, RefreshCw, ShieldCheck, Search, Pencil, X } from 'lucide-react'
import {
  createSearchTool,
  deleteSearchTool,
  deleteToolRegistry,
  getSearchTools,
  listToolRegistry,
  updateSearchTool,
  updateToolRegistry,
  upsertToolRegistry,
} from '@/lib/api'
import type { SearchToolResponse, ToolRegistryResponse } from '@/types/api'

const inputCls =
  'rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500'

type Tab = 'registry' | 'search'

function parseTab(value: string | null): Tab {
  return value === 'search' ? 'search' : 'registry'
}

export default function ToolRegistryPage() {
  const { data: session } = useSession()
  const searchParams = useSearchParams()
  const router = useRouter()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const [tab, setTab] = useState<Tab>(parseTab(searchParams.get('tab')))

  const [tools, setTools] = useState<ToolRegistryResponse[]>([])
  const [searchTools, setSearchTools] = useState<SearchToolResponse[]>([])
  const [loading, setLoading] = useState(true)

  const [showRegistryForm, setShowRegistryForm] = useState(false)
  const [showSearchForm, setShowSearchForm] = useState(false)
  const [editingToolName, setEditingToolName] = useState<string | null>(null)
  const [editingSearchId, setEditingSearchId] = useState<string | null>(null)

  const [registryForm, setRegistryForm] = useState({
    tool_name: '',
    policy: 'audit',
    runtime_enforcement: false,
    description: '',
  })
  const [searchForm, setSearchForm] = useState({
    name: '',
    description: '',
    tool_type: 'web_search',
    endpoint_url: '',
    auth_type: '',
    rate_limit_rpm: '',
    cost_per_query: '0',
    is_active: true,
  })
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [registry, providers] = await Promise.all([
        listToolRegistry(apiKey),
        getSearchTools(apiKey, { include_inactive: true }),
      ])
      setTools(registry.items)
      setSearchTools(providers.items)
    } catch {
      toast.error('Failed to load tool governance data')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { void load() }, [load])
  useEffect(() => { setTab(parseTab(searchParams.get('tab'))) }, [searchParams])

  function startEditRegistry(tool: ToolRegistryResponse) {
    setEditingToolName(tool.tool_name)
    setRegistryForm({
      tool_name: tool.tool_name,
      policy: tool.policy,
      runtime_enforcement: tool.runtime_enforcement,
      description: tool.description ?? '',
    })
    setShowRegistryForm(true)
    setTab('registry')
  }

  function startEditSearch(tool: SearchToolResponse) {
    setEditingSearchId(tool.id)
    setSearchForm({
      name: tool.name,
      description: tool.description ?? '',
      tool_type: tool.tool_type,
      endpoint_url: tool.endpoint_url ?? '',
      auth_type: tool.auth_type ?? '',
      rate_limit_rpm: tool.rate_limit_rpm != null ? String(tool.rate_limit_rpm) : '',
      cost_per_query: String(tool.cost_per_query ?? 0),
      is_active: tool.is_active,
    })
    setShowSearchForm(true)
    setTab('search')
  }

  function resetRegistryForm() {
    setEditingToolName(null)
    setRegistryForm({ tool_name: '', policy: 'audit', runtime_enforcement: false, description: '' })
    setShowRegistryForm(false)
  }

  function resetSearchForm() {
    setEditingSearchId(null)
    setSearchForm({
      name: '',
      description: '',
      tool_type: 'web_search',
      endpoint_url: '',
      auth_type: '',
      rate_limit_rpm: '',
      cost_per_query: '0',
      is_active: true,
    })
    setShowSearchForm(false)
  }

  async function handleSaveRegistry(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !registryForm.tool_name.trim()) return
    setSaving(true)
    try {
      if (editingToolName) {
        await updateToolRegistry(apiKey, editingToolName, {
          policy: registryForm.policy,
          runtime_enforcement: registryForm.runtime_enforcement,
          description: registryForm.description.trim() || null,
        })
        toast.success('Tool registry entry updated')
      } else {
        await upsertToolRegistry(apiKey, {
          tool_name: registryForm.tool_name.trim(),
          policy: registryForm.policy,
          runtime_enforcement: registryForm.runtime_enforcement,
          description: registryForm.description.trim() || null,
        })
        toast.success('Tool registered')
      }
      resetRegistryForm()
      await load()
    } catch {
      toast.error('Failed to save tool registry entry')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteRegistry(toolName: string) {
    if (!apiKey || !confirm(`Remove "${toolName}" from the registry?`)) return
    try {
      await deleteToolRegistry(apiKey, toolName)
      toast.success('Tool removed')
      await load()
    } catch {
      toast.error('Failed to remove tool')
    }
  }

  async function handleSaveSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !searchForm.name.trim()) return
    setSaving(true)
    try {
      const payload = {
        name: searchForm.name.trim(),
        description: searchForm.description.trim() || null,
        tool_type: searchForm.tool_type.trim(),
        endpoint_url: searchForm.endpoint_url.trim() || null,
        auth_type: searchForm.auth_type.trim() || null,
        auth_config: {},
        rate_limit_rpm: searchForm.rate_limit_rpm ? Number(searchForm.rate_limit_rpm) : null,
        cost_per_query: Number(searchForm.cost_per_query || '0'),
        is_active: searchForm.is_active,
      }
      if (editingSearchId) {
        await updateSearchTool(apiKey, editingSearchId, payload)
        toast.success('Search provider updated')
      } else {
        await createSearchTool(apiKey, payload)
        toast.success('Search provider created')
      }
      resetSearchForm()
      await load()
    } catch {
      toast.error('Failed to save search provider')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteSearch(toolId: string) {
    if (!apiKey || !confirm('Deactivate this search provider?')) return
    try {
      await deleteSearchTool(apiKey, toolId)
      toast.success('Search provider deactivated')
      await load()
    } catch {
      toast.error('Failed to deactivate search provider')
    }
  }

  const activeRegistry = tools.filter((tool) => tool.runtime_enforcement).length
  const activeSearch = searchTools.filter((tool) => tool.is_active).length

  return (
    <div className="space-y-8 max-w-6xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <Wrench className="h-5 w-5 text-violet-600 dark:text-violet-400" />
            <h1 className="text-2xl font-bold tracking-tight dark:text-white">Tool Registry</h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Manage runtime tool registrations and search providers from one governance surface. Policy simulation and dry-run testing live in{' '}
            <Link href="/tool-policies" className="font-medium text-violet-600 hover:text-violet-700 dark:text-violet-400">
              Tool Policies
            </Link>.
          </p>
        </div>
        <button
          onClick={() => void load()}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Registered Tools</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{tools.length}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Runtime Enforced</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{activeRegistry}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Search Providers</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{searchTools.length}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Active Search Providers</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{activeSearch}</p>
        </div>
      </div>

      <div className="flex gap-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-1">
        {([
          { id: 'registry' as Tab, label: 'Runtime Registry', icon: Wrench },
          { id: 'search' as Tab, label: 'Search Providers', icon: Search },
        ]).map((item) => (
          <button
            key={item.id}
            onClick={() => {
              setTab(item.id)
              router.replace(`/tool-registry?tab=${item.id}`)
            }}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
              tab === item.id
                ? 'bg-white dark:bg-slate-900 text-violet-700 dark:text-violet-300 shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'registry' && (
        <div className="space-y-6">
          <div className="flex justify-end">
            <button
              onClick={() => {
                if (showRegistryForm && !editingToolName) resetRegistryForm()
                else setShowRegistryForm(true)
              }}
              className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
            >
              {showRegistryForm ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
              {showRegistryForm && !editingToolName ? 'Cancel' : editingToolName ? 'Editing Tool' : 'Register Tool'}
            </button>
          </div>

          {showRegistryForm && (
            <form onSubmit={handleSaveRegistry} className="rounded-xl border border-violet-200 dark:border-violet-800 bg-violet-50/50 dark:bg-violet-900/10 p-5 space-y-4">
              <h3 className="text-sm font-semibold text-violet-800 dark:text-violet-300">
                {editingToolName ? `Edit ${editingToolName}` : 'Register a runtime tool'}
              </h3>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-500">Tool name *</label>
                  <input
                    value={registryForm.tool_name}
                    onChange={(e) => setRegistryForm((prev) => ({ ...prev, tool_name: e.target.value }))}
                    className={inputCls}
                    disabled={Boolean(editingToolName)}
                    required
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-500">Policy</label>
                  <select
                    value={registryForm.policy}
                    onChange={(e) => setRegistryForm((prev) => ({ ...prev, policy: e.target.value }))}
                    className={inputCls}
                  >
                    <option value="audit">audit</option>
                    <option value="allow">allow</option>
                    <option value="block">block</option>
                  </select>
                </div>
                <div className="md:col-span-2 flex flex-col gap-1">
                  <label className="text-xs text-slate-500">Description</label>
                  <input
                    value={registryForm.description}
                    onChange={(e) => setRegistryForm((prev) => ({ ...prev, description: e.target.value }))}
                    className={inputCls}
                    placeholder="What this tool does and why it is governed"
                  />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={registryForm.runtime_enforcement}
                  onChange={(e) => setRegistryForm((prev) => ({ ...prev, runtime_enforcement: e.target.checked }))}
                />
                Enable live runtime enforcement
              </label>
              <div className="flex gap-2">
                <button type="submit" disabled={saving} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50">
                  {saving ? 'Saving...' : editingToolName ? 'Save Changes' : 'Register Tool'}
                </button>
                <button type="button" onClick={resetRegistryForm} className="rounded-lg border border-slate-200 dark:border-slate-700 px-4 py-2 text-sm text-slate-600 dark:text-slate-300">
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-20"><RefreshCw className="h-5 w-5 animate-spin text-slate-400" /></div>
            ) : tools.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <Wrench className="h-8 w-8 text-slate-300 dark:text-slate-600" />
                <div className="text-center">
                  <p className="text-sm font-medium text-slate-500 dark:text-slate-400">No tools registered yet</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Register tools to enable runtime governance and audit logging.</p>
                </div>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Tool</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Policy</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Enforced</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Description</th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                  {tools.map((tool) => (
                    <tr key={tool.tool_name} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <td className="px-4 py-3 font-mono text-sm font-semibold dark:text-slate-200">{tool.tool_name}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{tool.policy}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${tool.runtime_enforcement ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300'}`}>
                          {tool.runtime_enforcement ? 'live' : 'off'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 max-w-[280px] truncate">
                        {tool.description || '-'}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          <button onClick={() => startEditRegistry(tool)} className="rounded-lg p-1.5 text-slate-400 hover:text-violet-600 hover:bg-violet-50 dark:hover:bg-violet-900/20" title="Edit tool">
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={() => void handleDeleteRegistry(tool.tool_name)} className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20" title="Remove tool">
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {tab === 'search' && (
        <div className="space-y-6">
          <div className="flex justify-end">
            <button
              onClick={() => {
                if (showSearchForm && !editingSearchId) resetSearchForm()
                else setShowSearchForm(true)
              }}
              className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
            >
              {showSearchForm ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
              {showSearchForm && !editingSearchId ? 'Cancel' : editingSearchId ? 'Editing Provider' : 'Add Search Provider'}
            </button>
          </div>

          {showSearchForm && (
            <form onSubmit={handleSaveSearch} className="rounded-xl border border-violet-200 dark:border-violet-800 bg-violet-50/50 dark:bg-violet-900/10 p-5 space-y-4">
              <h3 className="text-sm font-semibold text-violet-800 dark:text-violet-300">
                {editingSearchId ? 'Edit search provider' : 'Create search provider'}
              </h3>
              <div className="grid gap-4 md:grid-cols-2">
                <input value={searchForm.name} onChange={(e) => setSearchForm((prev) => ({ ...prev, name: e.target.value }))} className={inputCls} placeholder="Provider name" required />
                <input value={searchForm.tool_type} onChange={(e) => setSearchForm((prev) => ({ ...prev, tool_type: e.target.value }))} className={inputCls} placeholder="Tool type" required />
                <input value={searchForm.endpoint_url} onChange={(e) => setSearchForm((prev) => ({ ...prev, endpoint_url: e.target.value }))} className={inputCls} placeholder="Endpoint URL" />
                <input value={searchForm.auth_type} onChange={(e) => setSearchForm((prev) => ({ ...prev, auth_type: e.target.value }))} className={inputCls} placeholder="Auth type" />
                <input value={searchForm.rate_limit_rpm} onChange={(e) => setSearchForm((prev) => ({ ...prev, rate_limit_rpm: e.target.value }))} className={inputCls} placeholder="Rate limit RPM" />
                <input value={searchForm.cost_per_query} onChange={(e) => setSearchForm((prev) => ({ ...prev, cost_per_query: e.target.value }))} className={inputCls} placeholder="Cost per query" />
                <div className="md:col-span-2">
                  <input value={searchForm.description} onChange={(e) => setSearchForm((prev) => ({ ...prev, description: e.target.value }))} className={inputCls} placeholder="Description" />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                <input type="checkbox" checked={searchForm.is_active} onChange={(e) => setSearchForm((prev) => ({ ...prev, is_active: e.target.checked }))} />
                Provider active
              </label>
              <div className="flex gap-2">
                <button type="submit" disabled={saving} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50">
                  {saving ? 'Saving...' : editingSearchId ? 'Save Changes' : 'Create Provider'}
                </button>
                <button type="button" onClick={resetSearchForm} className="rounded-lg border border-slate-200 dark:border-slate-700 px-4 py-2 text-sm text-slate-600 dark:text-slate-300">
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-20"><RefreshCw className="h-5 w-5 animate-spin text-slate-400" /></div>
            ) : searchTools.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <Search className="h-8 w-8 text-slate-300 dark:text-slate-600" />
                <div className="text-center">
                  <p className="text-sm font-medium text-slate-500 dark:text-slate-400">No search providers yet</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Add providers here instead of maintaining a separate Search Tools page.</p>
                </div>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Provider</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Type</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Queries</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Policies</th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                  {searchTools.map((tool) => (
                    <tr key={tool.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{tool.name}</div>
                        <div className="text-xs text-slate-500">{tool.endpoint_url || 'managed internally'}</div>
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{tool.tool_type}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{tool.total_queries}</td>
                      <td className="px-4 py-3">
                        <Link href={`/tool-policies?tool=${encodeURIComponent(tool.name)}`} className="text-violet-600 hover:text-violet-700 dark:text-violet-400 text-xs font-medium">
                          {tool.policy_count} policies
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          <button onClick={() => startEditSearch(tool)} className="rounded-lg p-1.5 text-slate-400 hover:text-violet-600 hover:bg-violet-50 dark:hover:bg-violet-900/20" title="Edit provider">
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={() => void handleDeleteSearch(tool.id)} className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20" title="Deactivate provider">
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4">
            <div className="flex items-start gap-2">
              <ShieldCheck className="h-4 w-4 text-violet-600 dark:text-violet-400 mt-0.5 shrink-0" />
              <div className="text-sm text-slate-600 dark:text-slate-300">
                <p className="font-medium mb-1">Collapse note</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Search providers are now managed here instead of a separate Search Tools landing page. Their attached governance rules remain visible and editable from Tool Policies.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
