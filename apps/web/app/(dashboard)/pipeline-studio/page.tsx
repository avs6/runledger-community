'use client'

import Link from 'next/link'
import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { GitBranch, RefreshCw, Activity, Shield, DollarSign, Cpu } from 'lucide-react'

const stageMeta: Record<string, { label: string; color: string; icon: string }> = {
  ingest: { label: 'Ingest', color: 'bg-blue-500', icon: '📥' },
  routing: { label: 'Routing', color: 'bg-indigo-500', icon: '🔀' },
  enforcement: { label: 'Enforcement', color: 'bg-red-500', icon: '🛡️' },
  execution: { label: 'Execution', color: 'bg-emerald-500', icon: '⚡' },
  reporting: { label: 'Reporting', color: 'bg-amber-500', icon: '📊' },
}

export default function PipelineStudioPage() {
  const { data: session } = useSession()
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!session?.apiKey) return
    setLoading(true)
    setLoading(false)
  }, [session?.apiKey])

  useEffect(() => { refresh() }, [refresh])

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold dark:text-white flex items-center gap-2">
            <GitBranch className="h-6 w-6 text-indigo-500" />
            Pipeline Studio
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Visualize and author ingest → routing → enforcement → execution → reporting flows.
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

    </div>
  )
}
