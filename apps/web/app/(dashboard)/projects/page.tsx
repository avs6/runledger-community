'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { FolderKanban, Plus, Trash2, Key, Users, Layers, Cpu, Building2 } from 'lucide-react'
import {
  listProjects,
  createProject,
  deleteProject,
  assignProjectKey,
  listProjectKeys,
  removeProjectKey,
  listOrgWorkspaces,
  listTeamModels,
  getAccessGroups,
  listApiKeys,
} from '@/lib/api'
import type {
  ProjectResponse,
  ProjectKeyResponse,
  TeamModelResponse,
  AccessGroupResponse,
  ApiKeyResponse,
} from '@/types/api'

const inputCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'

export default function ProjectsPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey

  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedProject, setSelectedProject] = useState<string | null>(null)
  const [projectKeys, setProjectKeys] = useState<ProjectKeyResponse[]>([])

  // Dropdown reference data
  const [workspaces, setWorkspaces] = useState<{ id: string; name: string }[]>([])
  const [teamModels, setTeamModels] = useState<TeamModelResponse[]>([])
  const [accessGroups, setAccessGroups] = useState<AccessGroupResponse[]>([])
  const [apiKeys, setApiKeys] = useState<ApiKeyResponse[]>([])

  // Form State
  const [name, setName] = useState('')
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState('')
  const [customOwner, setCustomOwner] = useState('')
  const [budget, setBudget] = useState<number | ''>('')
  const [budgetPeriod, setBudgetPeriod] = useState('monthly')
  const [description, setDescription] = useState('')
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([])
  const [selectedGroupIds, setSelectedGroupIds] = useState<string[]>([])

  const [newKeyId, setNewKeyId] = useState('')
  const [creating, setCreating] = useState(false)

  const loadData = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [projRes, wsRes, tmRes, agRes, keysRes] = await Promise.all([
        listProjects(apiKey),
        listOrgWorkspaces(apiKey).catch(() => []),
        listTeamModels(apiKey).catch(() => ({ items: [], total: 0 })),
        getAccessGroups(apiKey).catch(() => ({ items: [], total: 0 })),
        listApiKeys(apiKey).catch(() => ({ items: [] })),
      ])
      setProjects(projRes.items)
      setWorkspaces(wsRes)
      setTeamModels(tmRes.items || [])
      setAccessGroups(agRes.items || [])
      setApiKeys(Array.isArray(keysRes) ? keysRes : [])
    } catch (err) {
      console.error(err)
      toast.error('Failed to load project configuration')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !name.trim()) return
    setCreating(true)

    const wsName = workspaces.find((w) => w.id === selectedWorkspaceId)?.name
    const ownerName = wsName || customOwner.trim() || undefined

    try {
      await createProject(apiKey, {
        name: name.trim(),
        owner: ownerName,
        budget_usd: budget !== '' ? budget : undefined,
        budget_period: budgetPeriod,
        description: description.trim() || undefined,
        config: {
          workspace_id: selectedWorkspaceId || undefined,
          team_model_ids: selectedModelIds,
          access_group_ids: selectedGroupIds,
        },
      })
      toast.success(`Project '${name}' created successfully`)
      setName('')
      setSelectedWorkspaceId('')
      setCustomOwner('')
      setBudget('')
      setDescription('')
      setSelectedModelIds([])
      setSelectedGroupIds([])
      loadData()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete(id: string) {
    if (!apiKey) return
    try {
      await deleteProject(apiKey, id)
      if (selectedProject === id) {
        setSelectedProject(null)
        setProjectKeys([])
      }
      toast.success('Project archived')
      loadData()
    } catch (err) {
      toast.error('Failed to archive project')
    }
  }

  async function selectProject(id: string) {
    if (!apiKey) return
    setSelectedProject(id)
    try {
      const res = await listProjectKeys(apiKey, id)
      setProjectKeys(res.items)
    } catch {
      setProjectKeys([])
    }
  }

  async function handleAssignKey(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !selectedProject || !newKeyId) return
    try {
      await assignProjectKey(apiKey, selectedProject, { api_key_id: newKeyId })
      setNewKeyId('')
      toast.success('API Key assigned to project')
      selectProject(selectedProject)
      loadData()
    } catch (err) {
      toast.error('Failed to assign API Key')
    }
  }

  async function handleRemoveKey(keyId: string) {
    if (!apiKey || !selectedProject) return
    try {
      await removeProjectKey(apiKey, selectedProject, keyId)
      toast.success('Key unassigned from project')
      selectProject(selectedProject)
      loadData()
    } catch (err) {
      toast.error('Failed to remove key')
    }
  }

  if (!apiKey) return <div className="p-6 text-slate-400">Please sign in.</div>

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm lg:flex-row lg:items-center lg:justify-between dark:border-slate-800 dark:bg-slate-900/80">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-blue-700 dark:text-blue-400">
            Workload Isolation & Governance
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 dark:text-white">
            Projects & Workspace Governance
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Organize teams, workspaces, AI models, and access groups under dedicated budgetary caps.
          </p>
        </div>
      </div>

      {/* Creation Card */}
      <form
        onSubmit={handleCreate}
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4"
      >
        <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
          <Plus className="h-4 w-4 text-blue-600" /> Create New Project
        </h2>

        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Project Name *
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="e.g., Customer Support Bot v2"
              className={inputCls}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Team / Workspace *
            </label>
            <select
              value={selectedWorkspaceId}
              onChange={(e) => setSelectedWorkspaceId(e.target.value)}
              className={inputCls}
            >
              <option value="">-- Select Team / Workspace --</option>
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Owner / Lead (Optional)
            </label>
            <input
              value={customOwner}
              onChange={(e) => setCustomOwner(e.target.value)}
              placeholder="e.g., Engineering / Alice"
              className={inputCls}
            />
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Budget USD Cap
            </label>
            <input
              type="number"
              step="0.01"
              value={budget}
              onChange={(e) => setBudget(e.target.value ? Number(e.target.value) : '')}
              placeholder="500.00"
              className={inputCls}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Budget Period
            </label>
            <select
              value={budgetPeriod}
              onChange={(e) => setBudgetPeriod(e.target.value)}
              className={inputCls}
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Description
            </label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Workload details..."
              className={inputCls}
            />
          </div>
        </div>

        {/* Access & Resource Associations */}
        <div className="grid gap-4 md:grid-cols-2 pt-2">
          {/* Team Models Association */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1.5">
              <Cpu className="h-3.5 w-3.5 text-blue-600" /> Assign Team Models
            </label>
            <div className="max-h-28 overflow-y-auto space-y-1.5 rounded-xl border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-800 dark:bg-slate-950">
              {teamModels.length === 0 ? (
                <p className="text-xs text-slate-400">No team models found in workspace.</p>
              ) : (
                teamModels.map((tm) => {
                  const checked = selectedModelIds.includes(tm.id)
                  return (
                    <label key={tm.id} className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedModelIds((prev) => [...prev, tm.id])
                          else setSelectedModelIds((prev) => prev.filter((id) => id !== tm.id))
                        }}
                        className="h-3.5 w-3.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span>{tm.model_name} <span className="text-slate-400">({tm.team_name})</span></span>
                    </label>
                  )
                })
              )}
            </div>
          </div>

          {/* Access Groups Association */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-indigo-600" /> Enforce Access Groups
            </label>
            <div className="max-h-28 overflow-y-auto space-y-1.5 rounded-xl border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-800 dark:bg-slate-950">
              {accessGroups.length === 0 ? (
                <p className="text-xs text-slate-400">No access groups created yet.</p>
              ) : (
                accessGroups.map((ag) => {
                  const checked = selectedGroupIds.includes(ag.id)
                  return (
                    <label key={ag.id} className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedGroupIds((prev) => [...prev, ag.id])
                          else setSelectedGroupIds((prev) => prev.filter((id) => id !== ag.id))
                        }}
                        className="h-3.5 w-3.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span>{ag.name} <span className="text-slate-400">({ag.guardrail_profile || 'default'})</span></span>
                    </label>
                  )
                })
              )}
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={creating || !name.trim()}
            className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {creating ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </form>

      {loading && <p className="text-sm text-slate-400">Loading projects...</p>}

      {/* Projects Grid/Table */}
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <table className="w-full text-sm">
          <thead className="bg-slate-50/80 dark:bg-slate-950/50 text-xs uppercase tracking-wider text-slate-500 font-semibold border-b border-slate-200 dark:border-slate-800">
            <tr>
              <th className="py-3 px-4 text-left">Project</th>
              <th className="py-3 px-4 text-left">Team / Workspace</th>
              <th className="py-3 px-4 text-left">Budget Cap</th>
              <th className="py-3 px-4 text-left">API Keys</th>
              <th className="py-3 px-4 text-left">Status</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {projects.map((p) => {
              const isSelected = selectedProject === p.id
              const config = (p.config || {}) as Record<string, any>
              const assignedModelCount = (config.team_model_ids || []).length
              const assignedGroupCount = (config.access_group_ids || []).length

              return (
                <tr
                  key={p.id}
                  onClick={() => selectProject(p.id)}
                  className={`cursor-pointer transition hover:bg-blue-50/50 dark:hover:bg-blue-950/20 ${
                    isSelected ? 'bg-blue-50/80 dark:bg-blue-950/40' : ''
                  }`}
                >
                  <td className="py-3.5 px-4">
                    <div className="font-semibold text-slate-900 dark:text-white">{p.name}</div>
                    {p.description && <div className="text-xs text-slate-500">{p.description}</div>}
                    <div className="mt-1 flex items-center gap-2">
                      {assignedModelCount > 0 && (
                        <span className="inline-flex items-center gap-1 rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                          <Cpu className="h-3 w-3" /> {assignedModelCount} Model(s)
                        </span>
                      )}
                      {assignedGroupCount > 0 && (
                        <span className="inline-flex items-center gap-1 rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                          <Layers className="h-3 w-3" /> {assignedGroupCount} Group(s)
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-slate-600 dark:text-slate-300">
                    <span className="inline-flex items-center gap-1">
                      <Building2 className="h-3.5 w-3.5 text-slate-400" />
                      {p.owner || 'Global Workspace'}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-xs text-slate-700 dark:text-slate-300">
                    {p.budget_usd != null ? `$${p.budget_usd.toFixed(2)} / ${p.budget_period || 'monthly'}` : 'Uncapped'}
                  </td>
                  <td className="py-3.5 px-4 font-semibold text-slate-700 dark:text-slate-300">
                    {p.key_count}
                  </td>
                  <td className="py-3.5 px-4">
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        p.is_active
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400'
                          : 'bg-slate-100 text-slate-500 dark:bg-slate-800'
                      }`}
                    >
                      {p.is_active ? 'Active' : 'Archived'}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDelete(p.id)
                      }}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      Archive
                    </button>
                  </td>
                </tr>
              )
            })}
            {projects.length === 0 && !loading && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-400">
                  No projects yet. Create one above to organize API keys and budgets.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Selected Project Key Management */}
      {selectedProject && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <Key className="h-4 w-4 text-blue-600" /> Assigned API Keys —{' '}
            {projects.find((p) => p.id === selectedProject)?.name}
          </h2>

          <form onSubmit={handleAssignKey} className="flex gap-3 items-end max-w-xl">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-500 mb-1">
                Select API Key
              </label>
              {apiKeys.length > 0 ? (
                <select
                  value={newKeyId}
                  onChange={(e) => setNewKeyId(e.target.value)}
                  required
                  className={inputCls}
                >
                  <option value="">-- Pick an API Key --</option>
                  {apiKeys.map((k) => (
                    <option key={k.id} value={k.id}>
                      {k.name || k.key_prefix} ({k.key_prefix}...)
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  value={newKeyId}
                  onChange={(e) => setNewKeyId(e.target.value)}
                  required
                  placeholder="Paste API Key UUID"
                  className={inputCls}
                />
              )}
            </div>
            <button
              type="submit"
              disabled={!newKeyId}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
            >
              Assign Key
            </button>
          </form>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs font-medium uppercase text-slate-500 dark:border-slate-800">
                  <th className="py-2 pr-4">Key ID</th>
                  <th className="py-2 pr-4">Assigned At</th>
                  <th className="py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {projectKeys.map((k) => (
                  <tr key={k.id} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="py-2 pr-4 font-mono text-xs text-slate-900 dark:text-white">
                      {k.api_key_id}
                    </td>
                    <td className="py-2 pr-4 text-xs text-slate-500">
                      {new Date(k.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2 text-right">
                      <button
                        onClick={() => handleRemoveKey(k.api_key_id)}
                        className="text-xs text-red-500 hover:text-red-700"
                      >
                        Unassign
                      </button>
                    </td>
                  </tr>
                ))}
                {projectKeys.length === 0 && (
                  <tr>
                    <td colSpan={3} className="py-4 text-center text-slate-400">
                      No API keys assigned to this project yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
