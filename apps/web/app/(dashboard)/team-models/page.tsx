'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import {
  listTeamModels,
  addTeamModel,
  deleteTeamModel,
} from '@/lib/api'
import type { TeamModelResponse } from '@/types/api'

export default function TeamModelsPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey

  const [models, setModels] = useState<TeamModelResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [filterTeam, setFilterTeam] = useState('')
  const [showForm, setShowForm] = useState(false)

  const [teamName, setTeamName] = useState('')
  const [modelName, setModelName] = useState('')
  const [provider, setProvider] = useState('')
  const [apiBaseUrl, setApiBaseUrl] = useState('')
  const [description, setDescription] = useState('')
  const [budgetUsd, setBudgetUsd] = useState<number | ''>('')
  const [budgetPeriod, setBudgetPeriod] = useState('monthly')

  async function load() {
    if (!apiKey) return
    setLoading(true)
    try {
      const res = await listTeamModels(apiKey, { team_name: filterTeam || undefined })
      setModels(res.items)
    } catch {
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [apiKey, filterTeam])

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !teamName || !modelName || !provider) return
    await addTeamModel(apiKey, {
      team_name: teamName,
      model_name: modelName,
      provider,
      api_base_url: apiBaseUrl || undefined,
      description: description || undefined,
      budget_usd: budgetUsd !== '' ? budgetUsd : undefined,
      budget_period: budgetPeriod,
    })
    setTeamName('')
    setModelName('')
    setProvider('')
    setApiBaseUrl('')
    setDescription('')
    setBudgetUsd('')
    setShowForm(false)
    load()
  }

  async function handleDelete(id: string) {
    if (!apiKey) return
    await deleteTeamModel(apiKey, id)
    load()
  }

  const teams = Array.from(new Set(models.map(m => m.team_name)))

  if (!apiKey) return <div className="p-6 text-slate-400">Please sign in.</div>

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Team Models</h1>
          <p className="text-sm text-slate-500">Manage per-team model assignments, budgets, and health.</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
          {showForm ? 'Cancel' : 'Add Team Model'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleAdd} className="rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5 space-y-3">
          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Team Name *</label>
              <input value={teamName} onChange={e => setTeamName(e.target.value)} required className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Model *</label>
              <input value={modelName} onChange={e => setModelName(e.target.value)} required placeholder="gpt-4o, claude-sonnet-5, ..." className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Provider *</label>
              <input value={provider} onChange={e => setProvider(e.target.value)} required placeholder="openai, anthropic, ..." className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">API Base URL</label>
              <input value={apiBaseUrl} onChange={e => setApiBaseUrl(e.target.value)} placeholder="https://..." className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Budget USD</label>
              <input type="number" step="0.01" value={budgetUsd} onChange={e => setBudgetUsd(e.target.value ? Number(e.target.value) : '')} className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Budget Period</label>
              <select value={budgetPeriod} onChange={e => setBudgetPeriod(e.target.value)} className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white">
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Description</label>
            <input value={description} onChange={e => setDescription(e.target.value)} className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white" />
          </div>
          <button type="submit" className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">Add</button>
        </form>
      )}

      <div className="flex gap-3 items-center">
        <select value={filterTeam} onChange={e => setFilterTeam(e.target.value)} className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-white/20 dark:bg-white/5 dark:text-white">
          <option value="">All Teams</option>
          {teams.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      {loading && <p className="text-sm text-slate-400">Loading...</p>}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-slate-200 text-left text-xs font-medium uppercase text-slate-500 dark:border-white/10">
            <th className="py-2 pr-4">Team</th><th className="py-2 pr-4">Model</th><th className="py-2 pr-4">Provider</th>
            <th className="py-2 pr-4">Health</th><th className="py-2 pr-4">Calls</th><th className="py-2 pr-4">Cost</th>
            <th className="py-2 pr-4">Budget</th><th className="py-2">Actions</th>
          </tr></thead>
          <tbody>
            {models.map(m => (
              <tr key={m.id} className="border-b border-slate-100 dark:border-white/5">
                <td className="py-2 pr-4 font-medium text-slate-900 dark:text-white">{m.team_name}</td>
                <td className="py-2 pr-4 text-slate-700 dark:text-slate-300">{m.model_name}</td>
                <td className="py-2 pr-4 text-slate-500">{m.provider}</td>
                <td className="py-2 pr-4">
                  <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${m.health_status === 'healthy' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : m.health_status === 'degraded' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' : 'bg-slate-100 text-slate-500 dark:bg-white/10'}`}>
                    {m.health_status}
                  </span>
                </td>
                <td className="py-2 pr-4 text-slate-500">{m.total_calls.toLocaleString()}</td>
                <td className="py-2 pr-4 text-slate-500">${m.total_cost_usd.toFixed(2)}</td>
                <td className="py-2 pr-4 text-slate-500">{m.budget_usd != null ? `$${m.budget_usd} / ${m.budget_period}` : '—'}</td>
                <td className="py-2">
                  <button onClick={() => handleDelete(m.id)} className="text-xs text-red-500 hover:text-red-700">Remove</button>
                </td>
              </tr>
            ))}
            {models.length === 0 && !loading && <tr><td colSpan={8} className="py-8 text-center text-slate-400">No team models configured.</td></tr>}
          </tbody>
        </table>
      </div>

      {models.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Cost by Team</h2>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            {Array.from(new Set(models.map(m => m.team_name))).map(team => {
              const teamModels = models.filter(m => m.team_name === team)
              const totalCost = teamModels.reduce((sum, m) => sum + m.total_cost_usd, 0)
              const totalCalls = teamModels.reduce((sum, m) => sum + m.total_calls, 0)
              return (
                <div key={team} className="rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
                  <h3 className="font-semibold text-slate-900 dark:text-white">{team}</h3>
                  <div className="mt-2 flex justify-between text-sm">
                    <span className="text-slate-500">{teamModels.length} models</span>
                    <span className="text-slate-500">{totalCalls.toLocaleString()} calls</span>
                  </div>
                  <p className="mt-1 text-lg font-bold text-indigo-600 dark:text-indigo-400">${totalCost.toFixed(2)}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
