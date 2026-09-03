'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import { listEvalExperiments, createEvalExperiment, deleteEvalExperiment, runEvalExperiment, listPrompts, listEvalDatasets, getBudgetDetailBuildPosture, getBudgetControlBuildPosture, getEvalReplayOrgGatewayPosture, getEvalReplayObservePosture, getBuildInternalPosture, getExperimentsComparisonPosture } from '@/lib/api'
import type { EvalExperiment, PromptResponse, EvalDataset, BudgetDetailBuildPosture, BudgetControlBuildPosture, EvalReplayOrgGatewayPosture, EvalReplayObservePosture, BuildInternalPosture, ExperimentsComparisonPosture } from '@/types/api'
import { toast } from 'sonner'
import { Play, Trash2, Plus, X, FlaskConical, CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'

const inputCls =
  'w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'

function StatusBadge({ status }: { status: EvalExperiment['status'] }) {
  const map = {
    pending: { label: 'Pending', cls: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300', Icon: Clock },
    running: { label: 'Running', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300', Icon: Loader2 },
    completed: { label: 'Completed', cls: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300', Icon: CheckCircle2 },
    failed: { label: 'Failed', cls: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300', Icon: XCircle },
  }
  const { label, cls, Icon } = map[status] ?? map.pending
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      <Icon className="h-3 w-3" />
      {label}
    </span>
  )
}

export default function ExperimentsPage() {
  const { data: session } = useSession()
  const { canWrite } = useRole()
  const [experiments, setExperiments] = useState<EvalExperiment[]>([])
  const [prompts, setPrompts] = useState<PromptResponse[]>([])
  const [datasets, setDatasets] = useState<EvalDataset[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [selected, setSelected] = useState<EvalExperiment | null>(null)

  // Form
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [datasetId, setDatasetId] = useState('')
  const [promptName, setPromptName] = useState('')
  const [promptVersion, setPromptVersion] = useState('')
  const [modelStr, setModelStr] = useState('gpt-4o')
  const [provider, setProvider] = useState('openai')
  const [creating, setCreating] = useState(false)
  const [budgetBuildPosture, setBudgetBuildPosture] = useState<BudgetDetailBuildPosture | null>(null)
  const [budgetControlBuildPosture, setBudgetControlBuildPosture] = useState<BudgetControlBuildPosture | null>(null)
  const [orgGatewayPosture, setOrgGatewayPosture] = useState<EvalReplayOrgGatewayPosture | null>(null)
  const [observePosture, setObservePosture] = useState<EvalReplayObservePosture | null>(null)
  const [buildPosture, setBuildPosture] = useState<BuildInternalPosture | null>(null)
  const [comparisonPosture, setComparisonPosture] = useState<ExperimentsComparisonPosture | null>(null)

  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  async function load() {
    if (!apiKey) return
    setLoading(true)
    try {
      const [exps, prms, dsets] = await Promise.all([
        listEvalExperiments(apiKey),
        listPrompts(apiKey),
        listEvalDatasets(apiKey),
      ])
      setExperiments(exps.items)
      setPrompts(prms.items)
      setDatasets(dsets.items)
    } catch (e: unknown) {
      toast.error('Failed to load experiments')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { if (apiKey) { load(); getBudgetDetailBuildPosture(apiKey).then(setBudgetBuildPosture).catch(() => {}); getBudgetControlBuildPosture(apiKey).then(setBudgetControlBuildPosture).catch(() => {}); getEvalReplayOrgGatewayPosture(apiKey).then(setOrgGatewayPosture).catch(() => {}); getEvalReplayObservePosture(apiKey).then(setObservePosture).catch(() => {}); getBuildInternalPosture(apiKey).then(setBuildPosture).catch(() => {}); getExperimentsComparisonPosture(apiKey).then(setComparisonPosture).catch(() => {}) } }, [apiKey])

  async function handleCreate() {
    if (!name.trim()) { toast.error('Name is required'); return }
    setCreating(true)
    try {
      const exp = await createEvalExperiment(apiKey, {
        name: name.trim(),
        description: description.trim() || undefined,
        dataset_id: datasetId || undefined,
        prompt_name: promptName || undefined,
        prompt_version: promptVersion ? parseInt(promptVersion) : undefined,
        models: modelStr ? [{ model: modelStr, provider, label: null }] : [],
      })
      setExperiments(prev => [exp, ...prev])
      setShowCreate(false)
      setName(''); setDescription(''); setDatasetId(''); setPromptName(''); setPromptVersion(''); setModelStr('gpt-4o')
      toast.success('Experiment created')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Create failed')
    } finally {
      setCreating(false)
    }
  }

  async function handleRun(id: string) {
    try {
      const updated = await runEvalExperiment(apiKey, id)
      setExperiments(prev => prev.map(e => e.id === id ? updated : e))
      if (selected?.id === id) setSelected(updated)
      toast.success('Experiment completed')
    } catch (e: unknown) {
      toast.error('Run failed')
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this experiment?')) return
    try {
      await deleteEvalExperiment(apiKey, id)
      setExperiments(prev => prev.filter(e => e.id !== id))
      if (selected?.id === id) setSelected(null)
      toast.success('Deleted')
    } catch {
      toast.error('Delete failed')
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <FlaskConical className="h-6 w-6 text-indigo-500" />
            Experiments
          </h1>
          <p className="mt-1 text-sm text-gray-500">Run prompts against datasets and evaluate model performance.</p>
        </div>
        {canWrite && (
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" /> New Experiment
          </button>
        )}
      </div>

      {budgetBuildPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Budget &amp; Build Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetBuildPosture.budget_context.active_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">30d Spend</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">${budgetBuildPosture.spend_context.total_spend_30d.toFixed(2)}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Models Used</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetBuildPosture.spend_context.distinct_models_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Breached</p>
              <p className={`mt-1 text-lg font-semibold ${budgetBuildPosture.budget_context.breach_count > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{budgetBuildPosture.budget_context.breach_count}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
            <Link href="/budgets" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
            <Link href="/budgets?scope=feature_tag" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Feature Budgets</Link>
            <Link href="/analytics?tab=economics" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Economics</Link>
            <Link href="/model-scorecards" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Model Scorecards</Link>
          </div>
        </div>
      )}

      {budgetControlBuildPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="flex items-center gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Budget Control — Build Posture</p>
          </div>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetControlBuildPosture.budget_policy.active_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Breached</p>
              <p className={`mt-1 text-lg font-semibold ${budgetControlBuildPosture.budget_policy.breached_budgets > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{budgetControlBuildPosture.budget_policy.breached_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Avg Utilization</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">{budgetControlBuildPosture.budget_policy.avg_utilization_pct.toFixed(1)}%</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Scope Types</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{Object.keys(budgetControlBuildPosture.scope_context).length}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
            <Link href="/budgets" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
            <Link href="/budgets?tab=overrides" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Overrides</Link>
            <Link href="/billing" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Billing</Link>
          </div>
        </div>
      )}

      {orgGatewayPosture && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50/50 p-5 shadow-sm dark:border-blue-900 dark:bg-blue-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">Organization &amp; Access Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Workspace</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.workspace_context.workspace_name}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Access Groups</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.access_group_context.access_groups}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">API Keys</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.api_key_context.api_keys}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Hub Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.ai_hub_context.hub_models}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-blue-200 dark:border-blue-800">
            <Link href="/organization" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Organization</Link>
            <Link href="/access-groups" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Access Groups</Link>
            <Link href="/api-keys" className="text-xs text-blue-600 hover:underline dark:text-blue-400">API Keys</Link>
            <Link href="/ai-hub" className="text-xs text-blue-600 hover:underline dark:text-blue-400">AI Hub</Link>
          </div>
        </div>
      )}

      {orgGatewayPosture && (
        <div className="rounded-2xl border border-violet-200 bg-violet-50/50 p-5 shadow-sm dark:border-violet-900 dark:bg-violet-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400">Gateway &amp; Routing Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Providers</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.provider_context.distinct_providers}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Routes</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.provider_context.active_routes}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Guardrails</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.guardrail_context.guardrail_rules}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Cache Configs</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.gateway_context.cache_configs}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-violet-200 dark:border-violet-800">
            <Link href="/gateway" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Model Gateway</Link>
            <Link href="/routes" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Routes</Link>
            <Link href="/guardrails" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Guardrails</Link>
            <Link href="/response-cache" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Response Cache</Link>
          </div>
        </div>
      )}

      {observePosture && (
        <div className="rounded-2xl border border-cyan-200 bg-cyan-50/50 p-5 shadow-sm dark:border-cyan-900 dark:bg-cyan-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">Observe &amp; Runtime Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Runs 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.runs_context.runs_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Provider Calls 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.request_flow_context.provider_calls_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Distinct Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.model_usage_context.distinct_models_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Total Cost 30d</p>
              <p className="mt-1 text-lg font-semibold text-cyan-600 dark:text-cyan-400">${observePosture.cost_savings_context.total_cost_30d.toFixed(2)}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-cyan-200 dark:border-cyan-800">
            <Link href="/analytics" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Analytics Overview</Link>
            <Link href="/runs" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Runs</Link>
            <Link href="/analytics?tab=requests" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Request Flow</Link>
            <Link href="/request-explorer" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Request Explorer</Link>
            <Link href="/analytics?tab=models" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Model Usage</Link>
            <Link href="/analytics?tab=economics" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Cost &amp; Savings</Link>
          </div>
        </div>
      )}

      {buildPosture && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50/50 p-5 shadow-sm dark:border-rose-900 dark:bg-rose-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-rose-600 dark:text-rose-400">Build &amp; Improve Loop</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-6">
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Playground 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.playground_context.sessions_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Workflows</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.workflows_context.definitions}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Eval Datasets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.evaluation_context.datasets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Hub Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.optimization_context.hub_models}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Score Events 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.scorecards_context.score_events_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Replay Experiments</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.replay_context.experiments}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-rose-200 dark:border-rose-800">
            <Link href="/playground" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Playground</Link>
            <Link href="/workflows" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Workflows</Link>
            <Link href="/evaluation?tab=scores" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Evaluation Studio</Link>
            <Link href="/optimization-opportunities" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Optimization</Link>
            <Link href="/optimization-simulator" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Simulator</Link>
            <Link href="/model-scorecards" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Model Scorecards</Link>
          </div>
        </div>
      )}

      {comparisonPosture && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm dark:border-amber-900 dark:bg-amber-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">Billing &amp; Chargeback Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-5">
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Billing Periods</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{comparisonPosture.billing_context.billing_periods}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Open Periods</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{comparisonPosture.billing_context.open_periods}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Chargeback Rules</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{comparisonPosture.chargeback_context.chargeback_rules}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Cost 30d</p>
              <p className="mt-1 text-lg font-semibold text-amber-600 dark:text-amber-400">${comparisonPosture.chargeback_context.cost_30d.toFixed(2)}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Comparison Assets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{comparisonPosture.comparison_context.eval_experiments + comparisonPosture.comparison_context.replay_experiments}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-amber-200 dark:border-amber-800">
            <Link href="/billing" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Billing Periods</Link>
            <Link href="/chargeback" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Chargeback Rules</Link>
            <Link href="/analytics?tab=economics" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Cost &amp; Savings</Link>
            <Link href="/replay" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Replay Lab</Link>
            <Link href="/optimization-opportunities" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Optimization</Link>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && canWrite && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-xl bg-white dark:bg-gray-900 p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">New Experiment</h2>
              <button onClick={() => setShowCreate(false)}><X className="h-5 w-5 text-gray-400" /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Name *</label>
                <input className={inputCls} value={name} onChange={e => setName(e.target.value)} placeholder="e.g. GPT-4o vs Claude 3.5" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Description</label>
                <input className={inputCls} value={description} onChange={e => setDescription(e.target.value)} placeholder="Optional description" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Dataset</label>
                <select className={inputCls} value={datasetId} onChange={e => setDatasetId(e.target.value)}>
                  <option value="">— None —</option>
                  {datasets.map(d => <option key={d.id} value={d.id}>{d.name} ({d.item_count} items)</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Prompt</label>
                <select className={inputCls} value={promptName} onChange={e => setPromptName(e.target.value)}>
                  <option value="">— None —</option>
                  {prompts.map(p => <option key={p.id} value={p.name}>{p.name}</option>)}
                </select>
              </div>
              {promptName && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Prompt Version (blank = latest)</label>
                  <input className={inputCls} value={promptVersion} onChange={e => setPromptVersion(e.target.value)} placeholder="e.g. 3" type="number" min="1" />
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Model</label>
                  <input className={inputCls} value={modelStr} onChange={e => setModelStr(e.target.value)} placeholder="gpt-4o" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Provider</label>
                  <select className={inputCls} value={provider} onChange={e => setProvider(e.target.value)}>
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="google">Google</option>
                    <option value="mistral">Mistral</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => setShowCreate(false)} className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">Cancel</button>
              <button onClick={handleCreate} disabled={creating} className="flex-1 rounded-lg bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                {creating ? 'Creating…' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* List */}
        <div className="lg:col-span-1 space-y-2">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-20 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800" />
            ))
          ) : experiments.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-600 p-8 text-center">
              <FlaskConical className="mx-auto h-8 w-8 text-gray-300 dark:text-gray-600" />
              <p className="mt-2 text-sm text-gray-500">No experiments yet</p>
            </div>
          ) : (
            experiments.map(exp => (
              <div
                key={exp.id}
                onClick={() => setSelected(exp)}
                className={`cursor-pointer rounded-xl border p-4 hover:border-indigo-500 transition-colors ${
                  selected?.id === exp.id
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/30'
                    : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">{exp.name}</p>
                    {exp.prompt_name && (
                      <p className="text-xs text-gray-500 mt-0.5">
                        {exp.prompt_name}{exp.prompt_version ? ` v${exp.prompt_version}` : ''}
                      </p>
                    )}
                  </div>
                  <StatusBadge status={exp.status} />
                </div>
                <div className="mt-2 flex items-center gap-3">
                  {canWrite && (
                    <button
                      onClick={e => { e.stopPropagation(); handleRun(exp.id) }}
                      disabled={exp.status === 'running'}
                      className="flex items-center gap-1 rounded-md bg-green-600 px-2 py-1 text-xs text-white hover:bg-green-700 disabled:opacity-40"
                      title="Run experiment"
                    >
                      <Play className="h-3 w-3" /> Run
                    </button>
                  )}
                  {canWrite && (
                    <button
                      onClick={e => { e.stopPropagation(); handleDelete(exp.id) }}
                      className="flex items-center gap-1 rounded-md text-xs text-red-500 hover:text-red-700"
                      title="Delete"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  )}
                  <span className="ml-auto text-xs text-gray-400">{exp.run_count} runs</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Detail */}
        <div className="lg:col-span-2">
          {selected ? (
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 space-y-6">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{selected.name}</h2>
                  {selected.description && <p className="mt-1 text-sm text-gray-500">{selected.description}</p>}
                </div>
                <StatusBadge status={selected.status} />
              </div>

              {/* Meta */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                {selected.prompt_name && (
                  <div>
                    <p className="text-xs text-gray-400">Prompt</p>
                    <p className="font-medium text-gray-900 dark:text-gray-100">
                      {selected.prompt_name}{selected.prompt_version ? ` (v${selected.prompt_version})` : ''}
                    </p>
                  </div>
                )}
                {selected.dataset_id && (
                  <div>
                    <p className="text-xs text-gray-400">Dataset</p>
                    <p className="font-medium text-gray-900 dark:text-gray-100">
                      {datasets.find(d => d.id === selected.dataset_id)?.name ?? selected.dataset_id.slice(0, 8)}
                    </p>
                  </div>
                )}
                <div>
                  <p className="text-xs text-gray-400">Total Runs</p>
                  <p className="font-medium text-gray-900 dark:text-gray-100">{selected.run_count}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Scores Created</p>
                  <p className="font-medium text-gray-900 dark:text-gray-100">{selected.scores_created}</p>
                </div>
              </div>

              {/* Models */}
              {selected.models.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Models</p>
                  <div className="flex flex-wrap gap-2">
                    {selected.models.map((m, i) => (
                      <span key={i} className="rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 text-xs px-3 py-1">
                        {m.model} ({m.provider})
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Results */}
              {selected.results && Object.keys(selected.results).length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Results</p>
                  {selected.results.error ? (
                    <div className="rounded-lg bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-600 dark:text-red-400">
                      {String(selected.results.error)}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {!!selected.results.prompt_preview && (
                        <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                          <p className="text-xs text-gray-400 mb-1">Prompt Preview</p>
                          <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono">
                            {String(selected.results.prompt_preview)}…
                          </p>
                        </div>
                      )}
                      {Array.isArray(selected.results.models) && selected.results.models.length > 0 && (
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-gray-200 dark:border-gray-700 text-xs text-gray-400">
                              <th className="text-left py-2">Model</th>
                              <th className="text-right py-2">Items Run</th>
                              <th className="text-right py-2">Avg Score</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(selected.results.models as { model: string; items_run: number; avg_score: number | null }[]).map((m, i) => (
                              <tr key={i} className="border-b border-gray-100 dark:border-gray-800">
                                <td className="py-2 text-gray-900 dark:text-gray-100">{m.model}</td>
                                <td className="py-2 text-right text-gray-500">{m.items_run}</td>
                                <td className="py-2 text-right font-medium text-gray-900 dark:text-gray-100">
                                  {m.avg_score != null ? m.avg_score.toFixed(3) : '—'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  )}
                </div>
              )}

              {selected.completed_at && (
                <p className="text-xs text-gray-400">
                  Completed {new Date(selected.completed_at).toLocaleString()}
                </p>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-600 p-12 flex flex-col items-center justify-center text-center">
              <FlaskConical className="h-10 w-10 text-gray-200 dark:text-gray-700" />
              <p className="mt-3 text-sm text-gray-400">Select an experiment to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
