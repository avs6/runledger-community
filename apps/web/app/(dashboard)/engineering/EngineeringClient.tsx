'use client'

import { useState } from 'react'
import {
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  Cpu,
  Database,
  GitBranch,
  MessageSquareText,
  Route,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  Wrench,
  X,
} from 'lucide-react'
import type { LifecycleStage } from '@/types/api'
import { num } from '@/lib/utils'

interface PipelineStageConfig {
  icon: React.ElementType
  label: string
  bg: string
  text: string
  border: string
  expandBg: string
  description: string
}

const pipelineStages: PipelineStageConfig[] = [
  { icon: MessageSquareText, label: 'Received', bg: 'bg-blue-500/10 dark:bg-blue-500/20', text: 'text-blue-700 dark:text-blue-300', border: 'border-blue-200 dark:border-blue-800', expandBg: 'bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800', description: 'Total requests received by the platform. This is the entry point — every SDK call, gateway proxy, and OTLP-originated request starts here.' },
  { icon: Route, label: 'Routed', bg: 'bg-purple-500/10 dark:bg-purple-500/20', text: 'text-purple-700 dark:text-purple-300', border: 'border-purple-200 dark:border-purple-800', expandBg: 'bg-purple-50 dark:bg-purple-950/30 border-purple-200 dark:border-purple-800', description: 'Requests matched to a gateway route and dispatched to a provider. Unrouted requests were served by the default model or rejected by policy.' },
  { icon: Sparkles, label: 'Cached', bg: 'bg-amber-500/10 dark:bg-amber-500/20', text: 'text-amber-700 dark:text-amber-300', border: 'border-amber-200 dark:border-amber-800', expandBg: 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800', description: 'Requests served from the response cache without hitting a provider. Higher cache rates reduce cost and latency. Tune cache TTL and key strategy to improve this.' },
  { icon: CheckCircle2, label: 'Completed', bg: 'bg-emerald-500/10 dark:bg-emerald-500/20', text: 'text-emerald-700 dark:text-emerald-300', border: 'border-emerald-200 dark:border-emerald-800', expandBg: 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800', description: 'Requests that returned a successful response (2xx from the provider). The gap between Received and Completed is your error + timeout rate.' },
  { icon: ShieldCheck, label: 'With outcome', bg: 'bg-cyan-500/10 dark:bg-cyan-500/20', text: 'text-cyan-700 dark:text-cyan-300', border: 'border-cyan-200 dark:border-cyan-800', expandBg: 'bg-cyan-50 dark:bg-cyan-950/30 border-cyan-200 dark:border-cyan-800', description: 'Completed requests that received an explicit outcome label (positive, negative, neutral). Outcome coverage drives quality scoring and value-based routing decisions.' },
  { icon: TrendingDown, label: 'Positive', bg: 'bg-green-500/10 dark:bg-green-500/20', text: 'text-green-700 dark:text-green-300', border: 'border-green-200 dark:border-green-800', expandBg: 'bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800', description: 'Requests with a positive outcome. This is the ultimate quality signal — the ratio of Positive to With outcome is your effective quality rate.' },
]

export function InteractivePipeline({ stages }: { stages: LifecycleStage[] }) {
  const [expandedStage, setExpandedStage] = useState<string | null>(null)

  const totalReceived = stages.find(s => s.stage === 'Received')?.count ?? 1

  return (
    <div className="space-y-3">
      {/* Pipeline row */}
      <div className="flex flex-wrap items-center gap-1.5">
        {pipelineStages.map((ps, i) => {
          const match = stages.find(s => s.stage === ps.label)
          const Icon = ps.icon
          const isExpanded = expandedStage === ps.label
          const count = match?.count ?? 0
          const pct = totalReceived > 0 ? (count / totalReceived) * 100 : 0
          return (
            <div key={ps.label} className="flex items-center gap-1.5">
              <button
                onClick={() => setExpandedStage(isExpanded ? null : ps.label)}
                className={`flex items-center gap-2 rounded-lg border ${ps.border} ${ps.bg} px-3 py-2 transition-all hover:shadow-md ${isExpanded ? 'ring-2 ring-blue-400/50 shadow-md' : ''}`}
              >
                <Icon className={`h-4 w-4 ${ps.text}`} />
                <div className="text-left">
                  <p className={`text-[11px] font-semibold ${ps.text}`}>{ps.label}</p>
                  <p className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                    {count.toLocaleString()} <span className="text-slate-400 dark:text-slate-500">({num(pct).toFixed(1)}%)</span>
                  </p>
                </div>
                <ChevronDown className={`h-3 w-3 ${ps.text} transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
              </button>
              {i < pipelineStages.length - 1 && (
                <ArrowRight className="h-3 w-3 flex-shrink-0 text-slate-300 dark:text-slate-600" />
              )}
            </div>
          )
        })}
      </div>

      {/* Expanded detail panel */}
      {expandedStage && (() => {
        const ps = pipelineStages.find(s => s.label === expandedStage)!
        const match = stages.find(s => s.stage === expandedStage)
        const count = match?.count ?? 0
        const pct = totalReceived > 0 ? (count / totalReceived) * 100 : 0
        const Icon = ps.icon
        const prevIdx = pipelineStages.findIndex(s => s.label === expandedStage) - 1
        const prevStage = prevIdx >= 0 ? pipelineStages[prevIdx] : null
        const prevMatch = prevStage ? stages.find(s => s.stage === prevStage.label) : null
        const prevCount = prevMatch?.count ?? totalReceived
        const dropoff = prevCount > 0 ? ((prevCount - count) / prevCount) * 100 : 0
        const nextIdx = pipelineStages.findIndex(s => s.label === expandedStage) + 1
        const nextStage = nextIdx < pipelineStages.length ? pipelineStages[nextIdx] : null
        const nextMatch = nextStage ? stages.find(s => s.stage === nextStage.label) : null
        const nextCount = nextMatch?.count ?? 0
        const conversionToNext = count > 0 ? (nextCount / count) * 100 : 0

        return (
          <div className={`rounded-xl border ${ps.expandBg} p-4 transition-all`}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className={`rounded-lg ${ps.bg} p-2`}>
                  <Icon className={`h-5 w-5 ${ps.text}`} />
                </div>
                <div>
                  <h3 className={`text-sm font-bold ${ps.text}`}>{ps.label}</h3>
                  <p className="mt-1 max-w-xl text-xs text-slate-600 dark:text-slate-400">{ps.description}</p>
                </div>
              </div>
              <button onClick={() => setExpandedStage(null)} className="rounded-lg p-1 text-slate-400 hover:bg-slate-200/50 hover:text-slate-600 dark:hover:bg-slate-700/50">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <div className="rounded-lg border border-slate-200/60 bg-white/60 p-2.5 dark:border-slate-700/60 dark:bg-slate-800/40">
                <p className="text-[9px] font-semibold uppercase tracking-widest text-slate-400">Count</p>
                <p className={`mt-0.5 text-lg font-bold ${ps.text}`}>{count.toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-slate-200/60 bg-white/60 p-2.5 dark:border-slate-700/60 dark:bg-slate-800/40">
                <p className="text-[9px] font-semibold uppercase tracking-widest text-slate-400">% of Total</p>
                <p className="mt-0.5 text-lg font-bold text-slate-800 dark:text-white">{num(pct).toFixed(1)}%</p>
              </div>
              {prevStage && (
                <div className="rounded-lg border border-slate-200/60 bg-white/60 p-2.5 dark:border-slate-700/60 dark:bg-slate-800/40">
                  <p className="text-[9px] font-semibold uppercase tracking-widest text-slate-400">Drop-off from {prevStage.label}</p>
                  <p className={`mt-0.5 text-lg font-bold ${dropoff > 20 ? 'text-red-600 dark:text-red-400' : dropoff > 5 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                    {num(dropoff).toFixed(1)}%
                  </p>
                </div>
              )}
              {nextStage && (
                <div className="rounded-lg border border-slate-200/60 bg-white/60 p-2.5 dark:border-slate-700/60 dark:bg-slate-800/40">
                  <p className="text-[9px] font-semibold uppercase tracking-widest text-slate-400">Conversion to {nextStage.label}</p>
                  <p className={`mt-0.5 text-lg font-bold ${conversionToNext > 80 ? 'text-emerald-600 dark:text-emerald-400' : conversionToNext > 50 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'}`}>
                    {num(conversionToNext).toFixed(1)}%
                  </p>
                </div>
              )}
            </div>
            {/* Progress bar showing this stage relative to total */}
            <div className="mt-3">
              <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800">
                <div className={`h-2 rounded-full transition-all ${
                  ps.label === 'Received' ? 'bg-blue-500' :
                  ps.label === 'Routed' ? 'bg-purple-500' :
                  ps.label === 'Cached' ? 'bg-amber-500' :
                  ps.label === 'Completed' ? 'bg-emerald-500' :
                  ps.label === 'With outcome' ? 'bg-cyan-500' :
                  'bg-green-500'
                }`} style={{ width: `${Math.max(pct, 0.5)}%` }} />
              </div>
              <p className="mt-1 text-[10px] text-slate-400">{count.toLocaleString()} of {totalReceived.toLocaleString()} total requests</p>
            </div>
          </div>
        )
      })()}
    </div>
  )
}

interface AgentNode {
  id: string
  label: string
  description: string
  icon: React.ElementType
  cx: number
  cy: number
  fill: string
  stroke: string
  text: string
  iconBg: string
  darkFill: string
  darkStroke: string
  darkText: string
}

const agentNodes: AgentNode[] = [
  { id: 'agent',    label: 'Agent',         description: 'The top-level orchestrator that receives user requests, delegates to sub-agents, queries memory, enforces policy, selects models, invokes tools, and assembles the final response.', icon: BrainCircuit,     cx: 350, cy: 42,  fill: '#dbeafe', stroke: '#93c5fd', text: '#1e40af', iconBg: '#3b82f6', darkFill: '#1e3a5f', darkStroke: '#3b82f6', darkText: '#93c5fd' },
  { id: 'subagent', label: 'Sub-Agent',     description: 'A delegated agent that handles a specialized subtask (e.g. code generation, search, analysis). Sub-agents inherit policy context and can invoke their own model calls.', icon: GitBranch,        cx: 112, cy: 140, fill: '#ede9fe', stroke: '#c4b5fd', text: '#5b21b6', iconBg: '#8b5cf6', darkFill: '#2e1065', darkStroke: '#8b5cf6', darkText: '#c4b5fd' },
  { id: 'memory',   label: 'Memory',        description: 'Persistent context store (vector DB, session history, knowledge graph). Memory retrieval augments prompts with relevant prior context without re-processing.', icon: Database,         cx: 350, cy: 140, fill: '#cffafe', stroke: '#67e8f9', text: '#155e75', iconBg: '#06b6d4', darkFill: '#164e63', darkStroke: '#06b6d4', darkText: '#67e8f9' },
  { id: 'policy',   label: 'Policy Engine', description: 'Enforces guardrails, budget limits, rate limits, content filters, and routing rules. Every request passes through policy before and after model execution.', icon: ShieldCheck,      cx: 588, cy: 140, fill: '#fef3c7', stroke: '#fcd34d', text: '#92400e', iconBg: '#f59e0b', darkFill: '#451a03', darkStroke: '#f59e0b', darkText: '#fcd34d' },
  { id: 'model',    label: 'Model',         description: 'The LLM provider endpoint. The gateway routes to the best model based on cost, latency, quality, and policy. Supports fallback, load balancing, and A/B routing.', icon: Cpu,              cx: 112, cy: 240, fill: '#d1fae5', stroke: '#6ee7b7', text: '#065f46', iconBg: '#10b981', darkFill: '#064e3b', darkStroke: '#10b981', darkText: '#6ee7b7' },
  { id: 'tool',     label: 'Tool',          description: 'External tool or function call (API, database query, code execution). Tools extend the agent\'s capabilities beyond text generation.', icon: Wrench,           cx: 350, cy: 240, fill: '#ffedd5', stroke: '#fdba74', text: '#9a3412', iconBg: '#f97316', darkFill: '#431407', darkStroke: '#f97316', darkText: '#fdba74' },
  { id: 'response', label: 'Response',      description: 'The final assembled response returned to the caller. Includes the model output, tool results, metadata, and telemetry. Outcome labels are attached here for quality tracking.', icon: MessageSquareText,cx: 588, cy: 240, fill: '#dcfce7', stroke: '#86efac', text: '#14532d', iconBg: '#22c55e', darkFill: '#14532d', darkStroke: '#22c55e', darkText: '#86efac' },
]

const agentEdges = [
  { from: 'agent', to: 'subagent' },
  { from: 'agent', to: 'memory' },
  { from: 'agent', to: 'policy' },
  { from: 'subagent', to: 'model' },
  { from: 'agent', to: 'tool' },
  { from: 'model', to: 'response' },
  { from: 'tool', to: 'response' },
  { from: 'policy', to: 'response' },
]

export function InteractiveAgentGraph() {
  const [selectedNode, setSelectedNode] = useState<string | null>(null)

  const W = 700, H = 280
  const nodeW = 120, nodeH = 36

  const byId = (id: string) => agentNodes.find(n => n.id === id)!

  function edgePath(from: AgentNode, to: AgentNode) {
    const x1 = from.cx, y1 = from.cy + nodeH / 2
    const x2 = to.cx, y2 = to.cy - nodeH / 2
    const dy = (y2 - y1) * 0.5
    return `M${x1},${y1} C${x1},${y1 + dy} ${x2},${y2 - dy} ${x2},${y2}`
  }

  const selected = selectedNode ? agentNodes.find(n => n.id === selectedNode) : null
  const connectedEdges = selectedNode
    ? agentEdges.filter(e => e.from === selectedNode || e.to === selectedNode)
    : []
  const connectedNodes = new Set(connectedEdges.flatMap(e => [e.from, e.to]))

  return (
    <div className="space-y-3">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 280 }} role="img" aria-label="Agent dependency graph">
        <defs>
          <linearGradient id="edgeGrad2" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#94a3b8" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#94a3b8" stopOpacity="0.2" />
          </linearGradient>
          <linearGradient id="edgeActive" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.4" />
          </linearGradient>
          <filter id="nodeShadow2" x="-8%" y="-8%" width="116%" height="130%">
            <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#0f172a" floodOpacity="0.08" />
          </filter>
          <filter id="nodeGlow" x="-20%" y="-20%" width="140%" height="160%">
            <feDropShadow dx="0" dy="0" stdDeviation="6" floodColor="#3b82f6" floodOpacity="0.3" />
          </filter>
          <marker id="arrowHead2" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
            <path d="M0,0 L7,2.5 L0,5" fill="none" stroke="#94a3b8" strokeWidth="1" />
          </marker>
          <marker id="arrowActive" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
            <path d="M0,0 L7,2.5 L0,5" fill="none" stroke="#3b82f6" strokeWidth="1" />
          </marker>
        </defs>
        {agentEdges.map(e => {
          const from = byId(e.from), to = byId(e.to)
          const isActive = selectedNode && (e.from === selectedNode || e.to === selectedNode)
          const isDimmed = selectedNode && !isActive
          return (
            <path
              key={`${e.from}-${e.to}`}
              d={edgePath(from, to)}
              fill="none"
              stroke={isActive ? 'url(#edgeActive)' : 'url(#edgeGrad2)'}
              strokeWidth={isActive ? 2.5 : 1.5}
              strokeLinecap="round"
              markerEnd={isActive ? 'url(#arrowActive)' : 'url(#arrowHead2)'}
              opacity={isDimmed ? 0.15 : 1}
              className="transition-all duration-200"
            />
          )
        })}
        {agentNodes.map(n => {
          const Icon = n.icon
          const rx = nodeW / 2, ry = nodeH / 2
          const isSelected = selectedNode === n.id
          const isConnected = connectedNodes.has(n.id)
          const isDimmed = selectedNode && !isSelected && !isConnected
          return (
            <g
              key={n.id}
              onClick={() => setSelectedNode(isSelected ? null : n.id)}
              className="cursor-pointer transition-all duration-200"
              opacity={isDimmed ? 0.25 : 1}
            >
              <rect x={n.cx - rx} y={n.cy - ry} width={nodeW} height={nodeH} rx={10} ry={10} fill={n.fill} stroke={isSelected ? '#3b82f6' : n.stroke} strokeWidth={isSelected ? 2 : 1.2} filter={isSelected ? 'url(#nodeGlow)' : 'url(#nodeShadow2)'} className="dark:hidden" />
              <rect x={n.cx - rx} y={n.cy - ry} width={nodeW} height={nodeH} rx={10} ry={10} fill={n.darkFill} stroke={isSelected ? '#60a5fa' : n.darkStroke} strokeWidth={isSelected ? 2 : 1.2} filter={isSelected ? 'url(#nodeGlow)' : 'url(#nodeShadow2)'} className="hidden dark:block" />
              <circle cx={n.cx - rx + 22} cy={n.cy} r={12} fill={n.iconBg} opacity="0.15" />
              <foreignObject x={n.cx - rx + 22 - 7} y={n.cy - 7} width="14" height="14">
                <Icon className="h-3.5 w-3.5" style={{ color: n.iconBg }} />
              </foreignObject>
              <text x={n.cx + 8} y={n.cy + 1} textAnchor="middle" dominantBaseline="middle" fill={n.text} fontSize="11" fontWeight="600" fontFamily="ui-sans-serif, system-ui, sans-serif" className="pointer-events-none dark:hidden">
                {n.label}
              </text>
              <text x={n.cx + 8} y={n.cy + 1} textAnchor="middle" dominantBaseline="middle" fill={n.darkText} fontSize="11" fontWeight="600" fontFamily="ui-sans-serif, system-ui, sans-serif" className="pointer-events-none hidden dark:block">
                {n.label}
              </text>
            </g>
          )
        })}
      </svg>

      {/* Detail panel */}
      {selected && (
        <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3 dark:border-slate-700 dark:bg-slate-800/40">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2.5">
              <div className="rounded-lg p-1.5" style={{ backgroundColor: `${selected.iconBg}15` }}>
                <selected.icon className="h-4 w-4" style={{ color: selected.iconBg }} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-800 dark:text-white">{selected.label}</h3>
                <p className="mt-0.5 max-w-2xl text-xs text-slate-600 dark:text-slate-400">{selected.description}</p>
              </div>
            </div>
            <button onClick={() => setSelectedNode(null)} className="rounded-lg p-1 text-slate-400 hover:bg-slate-200/50 hover:text-slate-600 dark:hover:bg-slate-700/50">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <span className="text-[10px] font-medium text-slate-400">Connections:</span>
            {connectedEdges.map(e => {
              const other = e.from === selectedNode ? byId(e.to) : byId(e.from)
              const direction = e.from === selectedNode ? 'to' : 'from'
              return (
                <button
                  key={`${e.from}-${e.to}`}
                  onClick={() => setSelectedNode(other.id)}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-medium text-slate-600 transition-colors hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                >
                  <span className="text-[9px] text-slate-400">{direction === 'to' ? '→' : '←'}</span>
                  {other.label}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {!selected && (
        <p className="text-center text-[10px] text-slate-400">Click any node to see details and connections</p>
      )}
    </div>
  )
}
