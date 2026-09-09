import { getServerSession } from 'next-auth'
import Link from 'next/link'
import {
  ArrowRight, Bot, BrainCircuit, Cpu, DollarSign, FlaskConical,
  GitBranch, Layers, Network, Plus, Route, Shield, Sparkles,
  Terminal, Wrench, Zap,
} from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { num } from '@/lib/utils'
import { getWorkflows, getBudgetDetailBuildPosture, getBudgetControlBuildPosture, getWorkflowsListPosture } from '@/lib/api'
import type { WorkflowDefinitionResponse } from '@/types/api'

const statusDot: Record<string, string> = {
  active: 'bg-emerald-400 shadow-emerald-400/50',
  archived: 'bg-slate-400 shadow-slate-400/30',
}

const stepTypeConfig: Record<string, { color: string; icon: typeof Bot }> = {
  model: { color: 'from-blue-500 to-cyan-400', icon: Cpu },
  agent: { color: 'from-violet-500 to-purple-400', icon: BrainCircuit },
  tool: { color: 'from-orange-500 to-amber-400', icon: Wrench },
  conditional: { color: 'from-pink-500 to-rose-400', icon: GitBranch },
  transform: { color: 'from-teal-500 to-emerald-400', icon: Sparkles },
}

function WorkflowCard({ wf }: { wf: WorkflowDefinitionResponse }) {
  const steps = wf.steps_schema ?? []
  const stepCount = steps.length

  return (
    <Link
      href={`/workflows/${wf.id}`}
      className="group relative flex flex-col rounded-xl border border-slate-200/80 bg-white/90 p-4 shadow-sm transition-all hover:shadow-lg hover:shadow-cyan-500/10 dark:border-slate-700/60 dark:bg-slate-900/80 dark:hover:border-slate-600"
    >
      {/* Gradient accent */}
      <div className="absolute inset-x-0 top-0 h-0.5 rounded-t-xl bg-gradient-to-r from-cyan-500 via-blue-500 to-violet-500" />

      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/20">
          <Route className="h-4.5 w-4.5 text-white" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-bold text-slate-950 dark:text-white">{wf.name}</h3>
            <span className={`h-2 w-2 shrink-0 rounded-full shadow-sm ${statusDot[wf.status] ?? statusDot.active}`} title={wf.status} />
          </div>
          {wf.description && (
            <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">{wf.description}</p>
          )}
        </div>
      </div>

      {/* Step pipeline visualization */}
      {stepCount > 0 && (
        <div className="mt-3 flex items-center gap-0.5 overflow-hidden">
          {steps.slice(0, 6).map((step: { name?: string; type?: string; step_type?: string }, i: number) => {
            const st = stepTypeConfig[(step.type ?? step.step_type ?? 'model')] ?? stepTypeConfig.model
            const StepIcon = st.icon
            return (
              <div key={i} className="flex items-center gap-0.5">
                <div className={`flex items-center gap-1 rounded-md bg-gradient-to-r ${st.color} px-1.5 py-0.5 shadow-sm`} title={step.name ?? `Step ${i + 1}`}>
                  <StepIcon className="h-2.5 w-2.5 text-white" />
                  <span className="max-w-[60px] truncate text-[9px] font-semibold text-white">{step.name ?? `Step ${i + 1}`}</span>
                </div>
                {i < Math.min(steps.length, 6) - 1 && <ArrowRight className="h-2.5 w-2.5 text-slate-300 dark:text-slate-600" />}
              </div>
            )
          })}
          {stepCount > 6 && <span className="text-[9px] font-semibold text-slate-400">+{stepCount - 6}</span>}
        </div>
      )}

      <div className="mt-3 flex items-center gap-3 border-t border-slate-100 pt-2.5 text-[10px] text-slate-500 dark:border-slate-800">
        <span className="flex items-center gap-0.5">
          <Layers className="h-2.5 w-2.5 text-cyan-500" />
          {stepCount} step{stepCount !== 1 ? 's' : ''}
        </span>
        <span className={`rounded-full px-1.5 py-px text-[9px] font-semibold ${
          wf.status === 'active'
            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
            : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
        }`}>{wf.status}</span>
        <span className="ml-auto text-slate-400">
          {new Date(wf.created_at).toLocaleDateString()}
        </span>
      </div>
    </Link>
  )
}

export default async function WorkflowsPage() {
  const session = await getServerSession(authOptions)
  if (!session) return null

  let workflows: WorkflowDefinitionResponse[] = []
  let total = 0
  try {
    const data = await getWorkflows(session.apiKey, { limit: 100 })
    workflows = data.workflows
    total = data.total
  } catch { /* API may not be reachable */ }

  const budgetBuildPosture = await getBudgetDetailBuildPosture(session.apiKey).catch(() => null)
  const budgetControlPosture = await getBudgetControlBuildPosture(session.apiKey).catch(() => null)
  const workflowsPosture = await getWorkflowsListPosture(session.apiKey).catch(() => null)

  const activeCount = workflows.filter(w => w.status === 'active').length
  const archivedCount = workflows.filter(w => w.status === 'archived').length
  const totalSteps = workflows.reduce((s, w) => s + (w.steps_schema?.length ?? 0), 0)

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/25">
            <Route className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-950 dark:text-white">Workflows</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Define multi-step pipelines, orchestrate agents and models.</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { href: '/agents', label: 'Agents', icon: BrainCircuit },
            { href: '/runs', label: 'Runs', icon: Zap },
            { href: '/evaluation', label: 'Eval Studio', icon: FlaskConical },
            { href: '/gateway', label: 'Gateway', icon: Network },
          ].map(nav => (
            <Link key={nav.label} href={nav.href} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              <nav.icon className="h-3 w-3" /> {nav.label}
            </Link>
          ))}
        </div>
      </div>

      {/* KPI hero strip */}
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-8">
        {[
          { label: 'Total', value: total, icon: Route, color: 'text-cyan-600 dark:text-cyan-400' },
          { label: 'Active', value: activeCount, icon: Zap, color: 'text-emerald-600 dark:text-emerald-400' },
          { label: 'Archived', value: archivedCount, icon: Shield, color: 'text-slate-500 dark:text-slate-400' },
          { label: 'Total Steps', value: totalSteps, icon: Layers, color: 'text-blue-600 dark:text-blue-400' },
          { label: 'Runs 30d', value: workflowsPosture?.observe_context.runs_30d ?? 0, icon: Terminal, color: 'text-blue-600 dark:text-blue-400' },
          { label: '30d Spend', value: workflowsPosture ? `$${num(workflowsPosture.observe_context.spend_30d).toFixed(2)}` : '$0', icon: DollarSign, color: 'text-emerald-600 dark:text-emerald-400' },
          { label: 'GW Routes', value: workflowsPosture?.gateway_context.gateway_routes ?? 0, icon: Network, color: 'text-violet-600 dark:text-violet-400' },
          { label: 'Routing', value: workflowsPosture?.gateway_context.routing_policies ?? 0, icon: GitBranch, color: 'text-violet-600 dark:text-violet-400' },
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
        {budgetBuildPosture && (
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
                { l: 'Budgets', v: budgetBuildPosture.budget_context.active_budgets },
                { l: 'Workflows', v: budgetBuildPosture.build_context.workflows },
                { l: 'Spend', v: `$${num(budgetBuildPosture.spend_context.total_spend_30d).toFixed(2)}` },
                { l: 'Breached', v: budgetBuildPosture.budget_context.breach_count },
              ].map(c => (
                <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] dark:border-emerald-800 dark:bg-emerald-950/40">
                  <span className="font-medium text-emerald-500 dark:text-emerald-400">{c.l}</span>
                  <span className="font-bold text-emerald-700 dark:text-emerald-300">{c.v}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {workflowsPosture && (
          <div className="rounded-xl border border-blue-200/60 bg-blue-50/30 p-3 dark:border-blue-800/40 dark:bg-blue-950/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Network className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
                <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">Org & Models</span>
              </div>
              <Link href="/ai-hub" className="text-[10px] font-semibold text-blue-600 hover:underline dark:text-blue-400">AI Hub</Link>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {[
                { l: 'Hub Models', v: workflowsPosture.org_context.hub_models },
                { l: 'Active', v: workflowsPosture.org_context.active_models },
              ].map(c => (
                <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] dark:border-blue-800 dark:bg-blue-950/40">
                  <span className="font-medium text-blue-500 dark:text-blue-400">{c.l}</span>
                  <span className="font-bold text-blue-700 dark:text-blue-300">{c.v}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {workflowsPosture && (
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
                { l: 'Datasets', v: workflowsPosture.eval_context.datasets },
                { l: 'Experiments', v: workflowsPosture.eval_context.experiments },
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

      {/* Workflow grid */}
      {workflows.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {workflows.map(wf => <WorkflowCard key={wf.id} wf={wf} />)}
        </div>
      )}

      {/* Registration guide — always visible */}
      <div className="rounded-xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center gap-2 mb-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600">
            <Plus className="h-3.5 w-3.5 text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-slate-900 dark:text-white">Create a Workflow</p>
            <p className="text-[10px] text-slate-500">Define step-by-step pipelines and track every execution</p>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <div>
            <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-400">1. Define the Workflow</p>
            <pre className="overflow-x-auto rounded-lg bg-slate-950 p-3 text-[11px] font-mono leading-relaxed text-green-400">{`curl -X POST /api/v1/workflows \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{
    "name": "customer-support",
    "description": "Classify, route, respond",
    "steps_schema": [
      {"name": "classify", "step_type": "model",
       "config": {"model": "gpt-4o-mini"}},
      {"name": "route", "step_type": "conditional"},
      {"name": "respond", "step_type": "agent",
       "config": {"agent_id": "AGENT_ID"}}
    ]
  }'`}</pre>
          </div>

          <div>
            <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-400">2. Start a Run</p>
            <pre className="overflow-x-auto rounded-lg bg-slate-950 p-3 text-[11px] font-mono leading-relaxed text-green-400">{`curl -X POST /api/v1/workflows/{id}/runs \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{
    "trigger": "api",
    "input_data": {
      "message": "I need help with billing",
      "customer_id": "cust_123"
    }
  }'

# Each step reports back:
POST /api/v1/workflows/{id}/runs/{run_id}/steps
  {"step_index": 0, "status": "completed",
   "output_data": {"category": "billing"}}`}</pre>
          </div>
        </div>

        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
          {[
            { type: 'model', desc: 'LLM inference — classify, summarize, generate.', icon: Cpu, color: 'from-blue-500 to-cyan-400' },
            { type: 'agent', desc: 'Delegate to a registered agent.', icon: BrainCircuit, color: 'from-violet-500 to-purple-400' },
            { type: 'tool', desc: 'Execute a tool — API call, search, code.', icon: Wrench, color: 'from-orange-500 to-amber-400' },
            { type: 'conditional', desc: 'Branch logic — route by output.', icon: GitBranch, color: 'from-pink-500 to-rose-400' },
            { type: 'transform', desc: 'Map, filter, reshape data between steps.', icon: Sparkles, color: 'from-teal-500 to-emerald-400' },
          ].map(t => (
            <div key={t.type} className="rounded-lg border border-slate-100 bg-slate-50/60 p-2.5 dark:border-slate-700 dark:bg-slate-800/60">
              <div className="flex items-center gap-1.5">
                <div className={`flex h-5 w-5 items-center justify-center rounded bg-gradient-to-br ${t.color}`}>
                  <t.icon className="h-3 w-3 text-white" />
                </div>
                <span className="text-[11px] font-bold text-slate-800 dark:text-white">{t.type}</span>
              </div>
              <p className="mt-1 text-[10px] leading-relaxed text-slate-500 dark:text-slate-400">{t.desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5 border-t border-slate-100 pt-3 text-[10px] dark:border-slate-800">
          <span className="font-semibold text-slate-500">After defining:</span>
          {[
            { l: 'Track runs', href: '/runs' },
            { l: 'View cost/step', href: '#' },
            { l: 'Set budgets', href: '/budgets' },
            { l: 'Evaluate quality', href: '/evaluation' },
          ].map(tip => (
            <Link key={tip.l} href={tip.href} className="rounded-md border border-slate-200 bg-white px-2 py-0.5 font-medium text-blue-600 hover:border-blue-300 dark:border-slate-700 dark:bg-slate-800 dark:text-blue-400">
              {tip.l}
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
