'use client'

import Link from 'next/link'
import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { BookOpen, RefreshCw, Server, Code2, Shield, Eye, GitBranch, Zap } from 'lucide-react'

const ownershipColors: Record<string, string> = {
  control_plane: 'border-indigo-200 dark:border-indigo-800 text-indigo-600 dark:text-indigo-400',
  data_plane: 'border-teal-200 dark:border-teal-800 text-teal-600 dark:text-teal-400',
  observability: 'border-amber-200 dark:border-amber-800 text-amber-600 dark:text-amber-400',
  admin: 'border-red-200 dark:border-red-800 text-red-600 dark:text-red-400',
}

const ownershipLabels: Record<string, string> = {
  control_plane: 'Control Plane',
  data_plane: 'Data Plane',
  observability: 'Observability',
  admin: 'Admin',
}

const ownershipIcons: Record<string, typeof Server> = {
  control_plane: Server,
  data_plane: Code2,
  observability: Eye,
  admin: Shield,
}

export default function ApiDocsPage() {
  const { data: session } = useSession()
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!session?.apiKey) return
    setLoading(true)
    setLoading(false)
  }, [session?.apiKey])

  useEffect(() => { refresh() }, [refresh])

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8201'

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold dark:text-white flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-purple-500" />
            API Explorer
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Interactive API reference generated from OpenAPI. Try endpoints, view ownership, and generate SDK snippets.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={`${apiBase}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded-lg border border-blue-200 bg-white px-3 py-1.5 text-sm font-medium text-blue-700 shadow-sm hover:bg-blue-50 dark:border-blue-700 dark:bg-slate-800 dark:text-blue-300 dark:hover:bg-slate-700"
          >
            <Code2 className="h-3.5 w-3.5" />
            Swagger UI
          </a>
          <a
            href={`${apiBase}/reference`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded-lg border border-purple-200 bg-white px-3 py-1.5 text-sm font-medium text-purple-700 shadow-sm hover:bg-purple-50 dark:border-purple-700 dark:bg-slate-800 dark:text-purple-300 dark:hover:bg-slate-700"
          >
            <BookOpen className="h-3.5 w-3.5" />
            Scalar Reference
          </a>
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

    </div>
  )
}
