import type { RunListItem } from '@/types/api'
import { formatCost } from '@/lib/utils'

type FlowNode = {
  id: string
  label: string
  layer: number
  value: number
  cost: number
}

type FlowLink = {
  source: string
  target: string
  value: number
  cost: number
}

const COLORS = [
  '#0f766e',
  '#0e7490',
  '#2563eb',
  '#16a34a',
  '#ca8a04',
  '#dc2626',
  '#64748b',
]

function cleanLabel(value: string | null | undefined, fallback: string) {
  const label = value?.trim()
  return label && label.length > 0 ? label : fallback
}

function money(value: string | null | undefined) {
  const parsed = parseFloat(value ?? '0')
  return Number.isFinite(parsed) ? parsed : 0
}

function nodeId(layer: string, label: string) {
  return `${layer}:${label}`
}

function addNode(nodes: Map<string, FlowNode>, id: string, label: string, layer: number, cost: number) {
  const existing = nodes.get(id)
  if (existing) {
    existing.value += 1
    existing.cost += cost
    return
  }
  nodes.set(id, { id, label, layer, value: 1, cost })
}

function addLink(links: Map<string, FlowLink>, source: string, target: string, cost: number) {
  const key = `${source}->${target}`
  const existing = links.get(key)
  if (existing) {
    existing.value += 1
    existing.cost += cost
    return
  }
  links.set(key, { source, target, value: 1, cost })
}

function buildFlow(runs: RunListItem[]) {
  const nodes = new Map<string, FlowNode>()
  const links = new Map<string, FlowLink>()

  for (const run of runs) {
    const cost = money(run.total_cost_usd)
    const source = nodeId('source', 'Incoming Requests')
    const intent = nodeId('intent', cleanLabel(run.feature_tag, 'General / Untagged'))
    const model = nodeId('model', cleanLabel(run.primary_model, 'Model Unknown'))
    const result = nodeId('result', run.status.charAt(0).toUpperCase() + run.status.slice(1))

    addNode(nodes, source, 'Incoming Requests', 0, cost)
    addNode(nodes, intent, intent.split(':')[1], 1, cost)
    addNode(nodes, model, model.split(':')[1], 2, cost)
    addNode(nodes, result, result.split(':')[1], 3, cost)

    addLink(links, source, intent, cost)
    addLink(links, intent, model, cost)
    addLink(links, model, result, cost)
  }

  return {
    nodes: Array.from(nodes.values()),
    links: Array.from(links.values()),
  }
}

function truncate(label: string, max = 24) {
  return label.length > max ? `${label.slice(0, max - 1)}...` : label
}

export default function RequestFlowSankey({ runs }: { runs: RunListItem[] }) {
  const sample = runs.slice(0, 200)
  const { nodes, links } = buildFlow(sample)

  if (sample.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white/70 p-10 text-center dark:border-slate-300 dark:bg-[#f2f6fb]/80">
        <p className="text-sm font-semibold text-slate-900 dark:text-white">No request flow yet</p>
        <p className="mx-auto mt-2 max-w-md text-sm text-slate-500 dark:text-slate-400">
          Send traffic through the SDK, OTLP, or Gateway and this view will map requests into intent, model, and result paths.
        </p>
      </div>
    )
  }

  const layerGroups = [0, 1, 2, 3].map((layer) =>
    nodes.filter((node) => node.layer === layer).sort((a, b) => b.value - a.value).slice(0, 8)
  )
  const visibleNodeIds = new Set(layerGroups.flat().map((node) => node.id))
  const visibleLinks = links.filter((link) => visibleNodeIds.has(link.source) && visibleNodeIds.has(link.target))
  const maxLink = Math.max(...visibleLinks.map((link) => link.value), 1)
  const positions = new Map<string, { x: number; y: number; color: string }>()
  const layerX = [80, 340, 610, 860]

  layerGroups.forEach((group, layer) => {
    const gap = 300 / Math.max(group.length, 1)
    group.forEach((node, index) => {
      positions.set(node.id, {
        x: layerX[layer],
        y: 70 + gap * index + gap / 2,
        color: COLORS[index % COLORS.length],
      })
    })
  })

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-300 dark:bg-[#f2f6fb]/90">
      <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-300">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-950 dark:text-white">AI Request Flow</h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Recent runs grouped as Request to Intent to Model to Result. Rich Skill, Agent, and Tool layers arrive with the next analytics contract.
            </p>
          </div>
          <span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-100 dark:text-blue-700">
            {sample.length.toLocaleString()} runs sampled
          </span>
        </div>
      </div>
      <svg viewBox="0 0 1000 420" className="h-[420px] w-full">
        <defs>
          <filter id="flow-shadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="8" stdDeviation="10" floodColor="#020617" floodOpacity="0.18" />
          </filter>
        </defs>

        {visibleLinks.map((link, index) => {
          const source = positions.get(link.source)
          const target = positions.get(link.target)
          if (!source || !target) return null
          const width = 2 + (link.value / maxLink) * 22
          const color = target.color
          const d = `M ${source.x + 130} ${source.y} C ${source.x + 215} ${source.y}, ${target.x - 85} ${target.y}, ${target.x} ${target.y}`
          return (
            <path
              key={`${link.source}-${link.target}-${index}`}
              d={d}
              fill="none"
              stroke={color}
              strokeOpacity="0.28"
              strokeWidth={width}
              strokeLinecap="round"
            >
              <title>{`${link.value} requests, ${formatCost(String(link.cost))}`}</title>
            </path>
          )
        })}

        {['Requests', 'Intent', 'Model', 'Result'].map((label, index) => (
          <text key={label} x={layerX[index]} y="36" className="fill-slate-500 text-[12px] font-bold uppercase tracking-[0.18em]">
            {label}
          </text>
        ))}

        {layerGroups.flat().map((node) => {
          const pos = positions.get(node.id)
          if (!pos) return null
          return (
            <g key={node.id} transform={`translate(${pos.x}, ${pos.y - 24})`} filter="url(#flow-shadow)">
              <rect width="158" height="48" rx="14" className="fill-slate-50 stroke-slate-200 dark:fill-slate-900 dark:stroke-slate-700" />
              <rect x="0" width="5" height="48" rx="2.5" fill={pos.color} />
              <text x="16" y="20" className="fill-slate-950 text-[13px] font-semibold dark:fill-white">
                {truncate(node.label)}
              </text>
              <text x="16" y="36" className="fill-slate-500 text-[11px] dark:fill-slate-400">
                {node.value} reqs · {formatCost(String(node.cost))}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
