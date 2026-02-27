import { getServerSession } from 'next-auth'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getRun, getRunGraph } from '@/lib/api'
import RunSummaryBar from '@/components/runs/RunSummaryBar'
import RunGraph from '@/components/dag/RunGraph'
import { ChevronLeft } from 'lucide-react'

export default async function RunDetailPage({
  params,
}: {
  params: { run_id: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  let run, graph
  try {
    ;[run, graph] = await Promise.all([
      getRun(session.apiKey, params.run_id),
      getRunGraph(session.apiKey, params.run_id),
    ])
  } catch {
    notFound()
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-center gap-2">
        <Link
          href="/runs"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
        >
          <ChevronLeft className="h-4 w-4" />
          Runs
        </Link>
      </div>

      <RunSummaryBar run={run} />

      <div className="min-h-0 flex-1 rounded-lg border border-gray-200 overflow-hidden">
        <RunGraph graphNodes={graph.nodes} graphEdges={graph.edges} />
      </div>
    </div>
  )
}
