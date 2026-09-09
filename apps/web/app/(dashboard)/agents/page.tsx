'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import {
  BrainCircuit, Bot, Cpu, DollarSign, FlaskConical, GitBranch,
  Layers, Network, Plus, Rocket, Shield, Sparkles,
  Terminal, Wrench, Zap, X,
} from 'lucide-react'
import { getAgents, createAgent, getBudgetDetailBuildPosture, getBudgetControlBuildPosture, getAgentsListPosture } from '@/lib/api'
import type { AgentResponse } from '@/types/api'
import { num } from '@/lib/utils'

const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500'

function money(v: number | string | null | undefined) {
  const n = num(v)
  if (n >= 1) return `$${n.toFixed(2)}`
  if (n >= 0.001) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

const typeConfig: Record<string, { label: string; color: string; glow: string; icon: typeof Bot }> = {
  autonomous: { label: 'Autonomous', color: 'from-blue-500 to-cyan-400', glow: 'shadow-blue-500/20', icon: Rocket },
  semi_autonomous: { label: 'Semi-Auto', color: 'from-violet-500 to-purple-400', glow: 'shadow-violet-500/20', icon: GitBranch },
  workflow: { label: 'Workflow', color: 'from-cyan-500 to-teal-400', glow: 'shadow-cyan-500/20', icon: Layers },
  chat: { label: 'Chat', color: 'from-pink-500 to-rose-400', glow: 'shadow-pink-500/20', icon: Sparkles },
}

const statusDot: Record<string, string> = {
  active: 'bg-emerald-400 shadow-emerald-400/50',
  paused: 'bg-amber-400 shadow-amber-400/50',
  retired: 'bg-slate-400 shadow-slate-400/30',
}

function AgentCard({ agent }: { agent: AgentResponse }) {
  const tc = typeConfig[agent.agent_type] ?? typeConfig.autonomous
  const TypeIcon = tc.icon

  return (
    <Link
      href={`/agents/${agent.id}`}
      className="group relative flex flex-col rounded-xl border border-slate-200/80 bg-white/90 p-4 shadow-sm transition-all hover:shadow-lg dark:border-slate-700/60 dark:bg-slate-900/80 dark:hover:border-slate-600"
    >
      <div className={`absolute inset-x-0 top-0 h-0.5 rounded-t-xl bg-gradient-to-r ${tc.color}`} />

      <div className="flex items-start gap-3">
        <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${tc.color} shadow-lg ${tc.glow}`}>
          <TypeIcon className="h-4.5 w-4.5 text-white" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-bold text-slate-950 dark:text-white">{agent.name}</h3>
            <span className={`h-2 w-2 shrink-0 rounded-full shadow-sm ${statusDot[agent.status] ?? statusDot.active}`} title={agent.status} />
          </div>
          {agent.description && (
            <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">{agent.description}</p>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <span className={`inline-flex items-center gap-1 rounded-md bg-gradient-to-r ${tc.color} px-2 py-0.5 text-[10px] font-bold text-white shadow-sm`}>
          <TypeIcon className="h-2.5 w-2.5" />
          {tc.label}
        </span>
        {agent.default_model && (
          <span className="rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-mono font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
            {agent.default_model}
          </span>
        )}
        {agent.owner && (
          <span className="text-[10px] text-slate-400">by {agent.owner}</span>
        )}
      </div>

      <div className="mt-3 flex items-center gap-3 border-t border-slate-100 pt-2.5 text-[10px] text-slate-500 dark:border-slate-800">
        {agent.budget_envelope != null && (
          <span className="flex items-center gap-0.5">
            <DollarSign className="h-2.5 w-2.5 text-emerald-500" />
            {money(agent.budget_envelope)}
          </span>
        )}
        <span className="flex items-center gap-0.5">
          <Wrench className="h-2.5 w-2.5 text-blue-400" />
          {agent.default_tools.length} tools
        </span>
        <span className="ml-auto text-slate-400">
          {new Date(agent.created_at).toLocaleDateString()}
        </span>
      </div>
    </Link>
  )
}

export default function AgentsPage() {
  const { data: session } = useSession()
  const apiKey = (session as Record<string, unknown> | null)?.apiKey as string | undefined
  const router = useRouter()

  const [agents, setAgents] = useState<AgentResponse[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  const [budgetBuildPosture, setBudgetBuildPosture] = useState<Record<string, unknown> | null>(null)
  const [agentsPosture, setAgentsPosture] = useState<Record<string, unknown> | null>(null)

  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    agent_type: 'autonomous',
    owner: '',
    default_model: '',
    default_tools: '',
    budget_envelope: '',
    policy_profile: '',
  })

  const fetchAgents = useCallback(() => {
    if (!apiKey) return
    setLoading(true)
    getAgents(apiKey, { limit: 100 })
      .then(data => { setAgents(data.agents); setTotal(data.total) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [apiKey])

  useEffect(() => {
    fetchAgents()
    if (apiKey) {
      getBudgetDetailBuildPosture(apiKey).then((p) => setBudgetBuildPosture(p as unknown as Record<string, unknown>)).catch(() => {})
      getAgentsListPosture(apiKey).then((p) => setAgentsPosture(p as unknown as Record<string, unknown>)).catch(() => {})
    }
  }, [fetchAgents, apiKey])

  async function handleRegister() {
    if (!apiKey || !formData.name.trim()) {
      toast.error('Agent name is required')
      return
    }
    setSaving(true)
    try {
      const tools = formData.default_tools.split(',').map(t => t.trim()).filter(Boolean)
      await createAgent(apiKey, {
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        agent_type: formData.agent_type,
        owner: formData.owner.trim() || undefined,
        default_model: formData.default_model.trim() || undefined,
        default_tools: tools.length > 0 ? tools : undefined,
        budget_envelope: formData.budget_envelope ? Number(formData.budget_envelope) : undefined,
        policy_profile: formData.policy_profile.trim() || undefined,
      })
      toast.success(`Agent "${formData.name}" registered`)
      setFormData({ name: '', description: '', agent_type: 'autonomous', owner: '', default_model: '', default_tools: '', budget_envelope: '', policy_profile: '' })
      setShowForm(false)
      fetchAgents()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to register agent')
    } finally {
      setSaving(false)
    }
  }

  if (!apiKey) return <div className="p-8 text-xs text-slate-500">Sign in to view agents.</div>

  const activeCount = agents.filter(a => a.status === 'active').length
  const pausedCount = agents.filter(a => a.status === 'paused').length
  const typeCounts = agents.reduce((acc, a) => { acc[a.agent_type] = (acc[a.agent_type] || 0) + 1; return acc }, {} as Record<string, number>)
  const bp = budgetBuildPosture as Record<string, Record<string, Record<string, number>>> | null
  const ap = agentsPosture as Record<string, Record<string, number>> | null

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 shadow-lg shadow-blue-500/25">
            <BrainCircuit className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-950 dark:text-white">Agent Registry</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Register, monitor, and govern your AI agents.</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-1 rounded-lg bg-gradient-to-r from-blue-600 to-cyan-500 px-3 py-1.5 text-[11px] font-semibold text-white shadow-sm hover:from-blue-700 hover:to-cyan-600 transition-colors"
          >
            <Plus className="h-3 w-3" /> Register Agent
          </button>
          {[
            { href: '/workflows', label: 'Workflows', icon: GitBranch },
            { href: '/runs', label: 'Runs', icon: Zap },
            { href: '/evaluation', label: 'Eval Studio', icon: FlaskConical },
            { href: '/ai-hub', label: 'AI Hub', icon: Cpu },
          ].map(nav => (
            <Link key={nav.label} href={nav.href} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              <nav.icon className="h-3 w-3" /> {nav.label}
            </Link>
          ))}
        </div>
      </div>

      {/* ── Registration Modal ────────────────────── */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setShowForm(false)}>
          <div className="w-full max-w-lg rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-2xl" onClick={e => e.stopPropagation()}>
            {/* Modal header */}
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 px-4 py-3">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500">
                  <Plus className="h-3.5 w-3.5 text-white" />
                </div>
                <h2 className="text-sm font-bold text-slate-900 dark:text-white">Register New Agent</h2>
              </div>
              <button onClick={() => setShowForm(false)} className="rounded-lg p-1 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                <X className="h-4 w-4 text-slate-400" />
              </button>
            </div>

            {/* Modal body */}
            <div className="px-4 py-3 space-y-3">
              {/* Row 1: Name + Type */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5 block">Name *</label>
                  <input
                    value={formData.name}
                    onChange={e => setFormData(p => ({ ...p, name: e.target.value }))}
                    placeholder="my-research-agent"
                    className={inputCls}
                    autoFocus
                  />
                </div>
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5 block">Type</label>
                  <select
                    value={formData.agent_type}
                    onChange={e => setFormData(p => ({ ...p, agent_type: e.target.value }))}
                    className={inputCls}
                  >
                    <option value="autonomous">Autonomous</option>
                    <option value="semi_autonomous">Semi-Autonomous</option>
                    <option value="workflow">Workflow</option>
                    <option value="chat">Chat</option>
                  </select>
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5 block">Description</label>
                <input
                  value={formData.description}
                  onChange={e => setFormData(p => ({ ...p, description: e.target.value }))}
                  placeholder="What does this agent do?"
                  className={inputCls}
                />
              </div>

              {/* Row 2: Model + Owner */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5 block">Default Model</label>
                  <input
                    value={formData.default_model}
                    onChange={e => setFormData(p => ({ ...p, default_model: e.target.value }))}
                    placeholder="gpt-4o"
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5 block">Owner</label>
                  <input
                    value={formData.owner}
                    onChange={e => setFormData(p => ({ ...p, owner: e.target.value }))}
                    placeholder="ml-team"
                    className={inputCls}
                  />
                </div>
              </div>

              {/* Row 3: Tools + Budget */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5 block">Tools (comma-separated)</label>
                  <input
                    value={formData.default_tools}
                    onChange={e => setFormData(p => ({ ...p, default_tools: e.target.value }))}
                    placeholder="web_search, code_exec"
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5 block">Budget (USD)</label>
                  <input
                    value={formData.budget_envelope}
                    onChange={e => setFormData(p => ({ ...p, budget_envelope: e.target.value }))}
                    placeholder="50.00"
                    type="number"
                    step="0.01"
                    min="0"
                    className={inputCls}
                  />
                </div>
              </div>

              {/* Policy profile */}
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-0.5 block">Policy Profile</label>
                <input
                  value={formData.policy_profile}
                  onChange={e => setFormData(p => ({ ...p, policy_profile: e.target.value }))}
                  placeholder="standard"
                  className={inputCls}
                />
              </div>

              {/* Agent type guide chips */}
              <div className="flex flex-wrap gap-1.5 pt-1 border-t border-slate-100 dark:border-slate-800">
                {[
                  { type: 'autonomous', desc: 'Self-directed, picks tools, iterates', icon: Rocket, color: 'from-blue-500 to-cyan-400' },
                  { type: 'semi_autonomous', desc: 'Proposes actions, human approves', icon: GitBranch, color: 'from-violet-500 to-purple-400' },
                  { type: 'workflow', desc: 'Follows defined step sequence', icon: Layers, color: 'from-cyan-500 to-teal-400' },
                  { type: 'chat', desc: 'Conversational interface', icon: Sparkles, color: 'from-pink-500 to-rose-400' },
                ].map(t => (
                  <button
                    key={t.type}
                    type="button"
                    onClick={() => setFormData(p => ({ ...p, agent_type: t.type }))}
                    className={`inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-medium transition-colors ${formData.agent_type === t.type ? `bg-gradient-to-r ${t.color} text-white shadow-sm` : 'border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                    title={t.desc}
                  >
                    <t.icon className="h-2.5 w-2.5" />
                    {t.type.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            {/* Modal footer */}
            <div className="flex items-center justify-end gap-2 border-t border-slate-100 dark:border-slate-800 px-4 py-3">
              <button onClick={() => setShowForm(false)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">Cancel</button>
              <button
                onClick={handleRegister}
                disabled={saving || !formData.name.trim()}
                className="rounded-lg bg-gradient-to-r from-blue-600 to-cyan-500 px-4 py-1.5 text-xs font-semibold text-white shadow-sm hover:from-blue-700 hover:to-cyan-600 disabled:opacity-50 transition-colors"
              >
                {saving ? 'Registering...' : 'Register Agent'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* KPI hero strip */}
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-8">
        {[
          { label: 'Total', value: total, icon: Bot, color: 'text-blue-600 dark:text-blue-400' },
          { label: 'Active', value: activeCount, icon: Zap, color: 'text-emerald-600 dark:text-emerald-400' },
          { label: 'Paused', value: pausedCount, icon: Shield, color: 'text-amber-600 dark:text-amber-400' },
          { label: 'Autonomous', value: typeCounts.autonomous ?? 0, icon: Rocket, color: 'text-blue-600 dark:text-blue-400' },
          { label: 'Semi-Auto', value: typeCounts.semi_autonomous ?? 0, icon: GitBranch, color: 'text-violet-600 dark:text-violet-400' },
          { label: 'Workflow', value: typeCounts.workflow ?? 0, icon: Layers, color: 'text-cyan-600 dark:text-cyan-400' },
          { label: 'Runs 30d', value: ap?.observe_context?.runs_30d ?? 0, icon: Terminal, color: 'text-blue-600 dark:text-blue-400' },
          { label: '30d Spend', value: bp?.spend_context?.total_spend_30d != null ? `$${num(bp.spend_context.total_spend_30d).toFixed(2)}` : '$0', icon: DollarSign, color: 'text-emerald-600 dark:text-emerald-400' },
        ].map(kpi => (
          <div key={kpi.label} className="rounded-xl border border-slate-200 bg-white/90 p-2.5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center gap-1">
              <kpi.icon className={`h-3 w-3 ${kpi.color}`} />
              <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-400">{kpi.label}</span>
            </div>
            <p className="mt-1 text-base font-bold text-slate-950 dark:text-white">{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Posture chips — condensed */}
      <div className="grid gap-2 lg:grid-cols-3">
        {bp && (
          <div className="rounded-xl border border-emerald-200/60 bg-emerald-50/30 p-3 dark:border-emerald-800/40 dark:bg-emerald-950/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <DollarSign className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">FinOps</span>
              </div>
              <Link href="/budgets" className="text-[10px] font-semibold text-emerald-600 hover:underline dark:text-emerald-400">Manage</Link>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {[
                { l: 'Budgets', v: bp.budget_context?.active_budgets ?? 0 },
                { l: 'Agents', v: bp.build_context?.agents ?? 0 },
                { l: 'Breached', v: bp.budget_context?.breach_count ?? 0 },
              ].map(c => (
                <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] dark:border-emerald-800 dark:bg-emerald-950/40">
                  <span className="font-medium text-emerald-500 dark:text-emerald-400">{c.l}</span>
                  <span className="font-bold text-emerald-700 dark:text-emerald-300">{c.v}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {ap && (
          <div className="rounded-xl border border-blue-200/60 bg-blue-50/30 p-3 dark:border-blue-800/40 dark:bg-blue-950/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Network className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
                <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">Org & Providers</span>
              </div>
              <Link href="/providers" className="text-[10px] font-semibold text-blue-600 hover:underline dark:text-blue-400">Providers</Link>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {[
                { l: 'Hub Models', v: ap.org_context?.hub_models ?? 0 },
                { l: 'Active', v: ap.org_context?.active_models ?? 0 },
                { l: 'Providers', v: ap.provider_context?.distinct_providers ?? 0 },
                { l: 'Chargeback', v: ap.finops_context?.chargeback_rules ?? 0 },
              ].map(c => (
                <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] dark:border-blue-800 dark:bg-blue-950/40">
                  <span className="font-medium text-blue-500 dark:text-blue-400">{c.l}</span>
                  <span className="font-bold text-blue-700 dark:text-blue-300">{c.v}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {ap && (
          <div className="rounded-xl border border-rose-200/60 bg-rose-50/30 p-3 dark:border-rose-800/40 dark:bg-rose-950/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <FlaskConical className="h-3.5 w-3.5 text-rose-600 dark:text-rose-400" />
                <span className="text-xs font-semibold text-rose-700 dark:text-rose-300">Build & Improve</span>
              </div>
              <Link href="/evaluation" className="text-[10px] font-semibold text-rose-600 hover:underline dark:text-rose-400">Eval Studio</Link>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {[
                { l: 'Datasets', v: ap.eval_context?.datasets ?? 0 },
                { l: 'Experiments', v: ap.eval_context?.experiments ?? 0 },
              ].map(c => (
                <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-rose-200 bg-rose-50 px-2 py-0.5 text-[11px] dark:border-rose-800 dark:bg-rose-950/40">
                  <span className="font-medium text-rose-500 dark:text-rose-400">{c.l}</span>
                  <span className="font-bold text-rose-700 dark:text-rose-300">{c.v}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Agent grid */}
      {loading ? (
        <div className="py-12 text-center text-xs text-slate-400">Loading agents...</div>
      ) : agents.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map(agent => <AgentCard key={agent.id} agent={agent} />)}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/60 dark:bg-slate-900/60 px-6 py-14 text-center">
          <BrainCircuit className="h-8 w-8 text-slate-400" />
          <h2 className="mt-3 text-sm font-bold text-slate-700 dark:text-slate-200">No agents registered</h2>
          <p className="mt-1 max-w-md text-xs text-slate-500">Click &ldquo;Register Agent&rdquo; above to create your first agent, or use the API.</p>
          <button onClick={() => setShowForm(true)} className="mt-3 rounded-lg bg-gradient-to-r from-blue-600 to-cyan-500 px-4 py-1.5 text-xs font-semibold text-white shadow-sm hover:from-blue-700 hover:to-cyan-600 transition-colors">
            <Plus className="mr-1 inline h-3 w-3" /> Register Agent
          </button>
        </div>
      )}

      {/* Registration guide — always visible */}
      <div className="rounded-xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center gap-2 mb-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500">
            <Terminal className="h-3.5 w-3.5 text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-slate-900 dark:text-white">API Registration</p>
            <p className="text-[10px] text-slate-500">You can also register agents via the API</p>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <div>
            <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-400">Minimal — Quick Start</p>
            <pre className="overflow-x-auto rounded-lg bg-slate-950 p-3 text-[11px] font-mono leading-relaxed text-green-400">{`curl -X POST /api/v1/agents \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{
    "name": "my-agent",
    "agent_type": "autonomous",
    "default_model": "gpt-4o"
  }'`}</pre>
          </div>
          <div>
            <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-400">Full — With Budget & Tools</p>
            <pre className="overflow-x-auto rounded-lg bg-slate-950 p-3 text-[11px] font-mono leading-relaxed text-green-400">{`curl -X POST /api/v1/agents \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{
    "name": "research-agent",
    "description": "Autonomous research assistant",
    "agent_type": "autonomous",
    "owner": "ml-team",
    "default_model": "gpt-4o",
    "default_tools": ["web_search", "code_exec"],
    "budget_envelope": 50.00,
    "policy_profile": "standard"
  }'`}</pre>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5 border-t border-slate-100 pt-3 text-[10px] dark:border-slate-800">
          <span className="font-semibold text-slate-500">After registering:</span>
          {[
            { l: 'Add memory', href: '#', desc: 'POST /agents/{id}/memory' },
            { l: 'Run workflows', href: '/workflows', desc: 'Link to workflow steps' },
            { l: 'Set budgets', href: '/budgets', desc: 'Control spend per agent' },
            { l: 'View runs', href: '/runs', desc: 'Track agent executions' },
          ].map(tip => (
            <Link key={tip.l} href={tip.href} className="rounded-md border border-slate-200 bg-white px-2 py-0.5 font-medium text-blue-600 hover:border-blue-300 dark:border-slate-700 dark:bg-slate-800 dark:text-blue-400" title={tip.desc}>
              {tip.l}
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
