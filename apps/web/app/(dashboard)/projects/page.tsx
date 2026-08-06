'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import {
  listProjects,
  createProject,
  deleteProject,
  assignProjectKey,
  listProjectKeys,
  removeProjectKey,
} from '@/lib/api'
import type { ProjectResponse, ProjectKeyResponse } from '@/types/api'

export default function ProjectsPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey

  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedProject, setSelectedProject] = useState<string | null>(null)
  const [projectKeys, setProjectKeys] = useState<ProjectKeyResponse[]>([])

  const [name, setName] = useState('')
  const [owner, setOwner] = useState('')
  const [budget, setBudget] = useState<number | ''>('')
  const [budgetPeriod, setBudgetPeriod] = useState('monthly')
  const [description, setDescription] = useState('')

  const [newKeyId, setNewKeyId] = useState('')

  async function load() {
    if (!apiKey) return
    setLoading(true)
    try {
      const res = await listProjects(apiKey)
      setProjects(res.items)
    } catch {
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [apiKey])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !name) return
    await createProject(apiKey, {
      name,
      owner: owner || undefined,
      budget_usd: budget !== '' ? budget : undefined,
      budget_period: budgetPeriod,
      description: description || undefined,
    })
    setName('')
    setOwner('')
    setBudget('')
    setDescription('')
    load()
  }

  async function handleDelete(id: string) {
    if (!apiKey) return
    await deleteProject(apiKey, id)
    if (selectedProject === id) { setSelectedProject(null); setProjectKeys([]) }
    load()
  }

  async function selectProject(id: string) {
    if (!apiKey) return
    setSelectedProject(id)
    const res = await listProjectKeys(apiKey, id)
    setProjectKeys(res.items)
  }

  async function handleAssignKey(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !selectedProject || !newKeyId) return
    await assignProjectKey(apiKey, selectedProject, { api_key_id: newKeyId })
    setNewKeyId('')
    selectProject(selectedProject)
    load()
  }

  async function handleRemoveKey(keyId: string) {
    if (!apiKey || !selectedProject) return
    await removeProjectKey(apiKey, selectedProject, keyId)
    selectProject(selectedProject)
    load()
  }

  if (!apiKey) return <div className="p-6 text-slate-400">Please sign in.</div>

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Projects</h1>
      <p className="text-sm text-slate-500">Organize API keys and budgets into logical projects.</p>

      <form onSubmit={handleCreate} className="flex flex-wrap gap-3 items-end rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Name *</label>
          <input value={name} onChange={e => setName(e.target.value)} required className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Owner</label>
          <input value={owner} onChange={e => setOwner(e.target.value)} placeholder="team or user" className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Budget USD</label>
          <input type="number" step="0.01" value={budget} onChange={e => setBudget(e.target.value ? Number(e.target.value) : '')} className="w-28 rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Period</label>
          <select value={budgetPeriod} onChange={e => setBudgetPeriod(e.target.value)} className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white">
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Description</label>
          <input value={description} onChange={e => setDescription(e.target.value)} className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
        </div>
        <button type="submit" className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">Create Project</button>
      </form>

      {loading && <p className="text-sm text-slate-400">Loading...</p>}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-slate-200 text-left text-xs font-medium uppercase text-slate-500 dark:border-white/10">
            <th className="py-2 pr-4">Name</th><th className="py-2 pr-4">Owner</th><th className="py-2 pr-4">Budget</th>
            <th className="py-2 pr-4">Keys</th><th className="py-2 pr-4">Status</th><th className="py-2">Actions</th>
          </tr></thead>
          <tbody>
            {projects.map(p => (
              <tr key={p.id} className={`border-b border-slate-100 dark:border-white/5 cursor-pointer hover:bg-slate-50 dark:hover:bg-white/5 ${selectedProject === p.id ? 'bg-indigo-50/50 dark:bg-indigo-900/10' : ''}`}
                onClick={() => selectProject(p.id)}>
                <td className="py-2 pr-4 font-medium text-slate-900 dark:text-white">{p.name}</td>
                <td className="py-2 pr-4 text-slate-500">{p.owner || '—'}</td>
                <td className="py-2 pr-4 text-slate-500">{p.budget_usd != null ? `$${p.budget_usd} / ${p.budget_period}` : '—'}</td>
                <td className="py-2 pr-4 text-slate-500">{p.key_count}</td>
                <td className="py-2 pr-4">
                  <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${p.is_active ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-slate-100 text-slate-500 dark:bg-white/10'}`}>
                    {p.is_active ? 'Active' : 'Archived'}
                  </span>
                </td>
                <td className="py-2">
                  <button onClick={e => { e.stopPropagation(); handleDelete(p.id) }} className="text-xs text-red-500 hover:text-red-700">Archive</button>
                </td>
              </tr>
            ))}
            {projects.length === 0 && !loading && <tr><td colSpan={6} className="py-8 text-center text-slate-400">No projects yet.</td></tr>}
          </tbody>
        </table>
      </div>

      {selectedProject && (
        <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5 space-y-4">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            API Keys — {projects.find(p => p.id === selectedProject)?.name}
          </h2>

          <form onSubmit={handleAssignKey} className="flex gap-3 items-end">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">API Key UUID</label>
              <input value={newKeyId} onChange={e => setNewKeyId(e.target.value)} required placeholder="paste key UUID" className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white w-72" />
            </div>
            <button type="submit" className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">Assign Key</button>
          </form>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-slate-200 text-left text-xs font-medium uppercase text-slate-500 dark:border-white/10">
                <th className="py-2 pr-4">Key ID</th><th className="py-2 pr-4">Assigned</th><th className="py-2">Actions</th>
              </tr></thead>
              <tbody>
                {projectKeys.map(k => (
                  <tr key={k.id} className="border-b border-slate-100 dark:border-white/5">
                    <td className="py-2 pr-4 font-mono text-sm text-slate-900 dark:text-white">{k.api_key_id}</td>
                    <td className="py-2 pr-4 text-slate-500">{new Date(k.created_at).toLocaleDateString()}</td>
                    <td className="py-2"><button onClick={() => handleRemoveKey(k.api_key_id)} className="text-xs text-red-500 hover:text-red-700">Remove</button></td>
                  </tr>
                ))}
                {projectKeys.length === 0 && <tr><td colSpan={3} className="py-4 text-center text-slate-400">No keys assigned.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
