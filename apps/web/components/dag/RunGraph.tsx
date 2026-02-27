'use client'

import { useCallback, useMemo, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from '@xyflow/react'
import dagre from 'dagre'
import '@xyflow/react/dist/style.css'
import type { GraphNode, GraphEdge } from '@/types/api'
import { SpanNode } from './SpanNode'
import SpanDetailPanel from './SpanDetailPanel'

const nodeTypes = { span: SpanNode }

const NODE_WIDTH = 200
const NODE_HEIGHT = 80

function applyDagreLayout(
  nodes: Node[],
  edges: Edge[],
): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 40, ranksep: 60 })

  nodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }))
  edges.forEach((e) => g.setEdge(e.source, e.target))
  dagre.layout(g)

  return {
    nodes: nodes.map((n) => {
      const pos = g.node(n.id)
      return {
        ...n,
        position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
      }
    }),
    edges,
  }
}

export default function RunGraph({
  graphNodes,
  graphEdges,
}: {
  graphNodes: GraphNode[]
  graphEdges: GraphEdge[]
}) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)

  const { nodes: layoutNodes, edges: layoutEdges } = useMemo(() => {
    const rawNodes: Node[] = graphNodes.map((n) => ({
      id: n.id,
      type: 'span',
      data: { ...n.data, label: n.label },
      position: { x: 0, y: 0 },
    }))
    const rawEdges: Edge[] = graphEdges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: 'smoothstep',
      style: { stroke: '#d1d5db' },
    }))
    return applyDagreLayout(rawNodes, rawEdges)
  }, [graphNodes, graphEdges])

  const [nodes, , onNodesChange] = useNodesState(layoutNodes)
  const [edges, , onEdgesChange] = useEdgesState(layoutEdges)

  const nodeById = useMemo(
    () => Object.fromEntries(graphNodes.map((n) => [n.id, n])),
    [graphNodes],
  )

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNode(nodeById[node.id] ?? null)
    },
    [nodeById],
  )

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={2}
        className="bg-gray-50"
      >
        <Background color="#e5e7eb" gap={20} />
        <Controls />
        <MiniMap nodeColor="#e5e7eb" maskColor="rgba(255,255,255,0.6)" />
      </ReactFlow>
      <SpanDetailPanel
        node={selectedNode}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  )
}
