'use client'

import Link from 'next/link'
import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { BookOpen, RefreshCw, Server, Code2, Shield, Eye } from 'lucide-react'
import { getApiExplorerPosture } from '@/lib/api'
import type { ApiExplorerPosture } from '@/types/api'

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
  const [posture, setPosture] = useState<ApiExplorerPosture | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!session?.apiKey) return
    setLoading(true)
    try {
      const data = await getApiExplorerPosture(session.apiKey)
      setPosture(data)
    } catch {
      toast.error('Failed to load API explorer posture')
    } finally {
      setLoading(false)
    }
  }, [session?.apiKey])

  useEffect(() => { refresh() }, [refresh])

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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
            href={`${apiBase}/reference`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded-lg border border-purple-200 bg-white px-3 py-1.5 text-sm font-medium text-purple-700 shadow-sm hover:bg-purple-50 dark:border-purple-700 dark:bg-slate-800 dark:text-purple-300 dark:hover:bg-slate-700"
          >
            <BookOpen className="h-3.5 w-3.5" />
            Open Scalar
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

      {posture && (
        <>
          <div className="rounded-xl border border-purple-200 dark:border-purple-800 bg-white dark:bg-slate-800/40 p-5 space-y-4">
            <h2 className="text-base font-semibold dark:text-white">OpenAPI Surface</h2>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-lg border border-purple-200 dark:border-purple-800 bg-white dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-purple-600 dark:text-purple-400">Spec Format</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{posture.openapi_surface.spec_format}</p>
                <p className="text-xs text-slate-400">Auto-generated</p>
              </div>
              <div className="rounded-lg border border-purple-200 dark:border-purple-800 bg-white dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-purple-600 dark:text-purple-400">Reference UI</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{posture.openapi_surface.reference_ui}</p>
                <p className="text-xs text-slate-400">Scalar API Reference</p>
              </div>
              <div className="rounded-lg border border-purple-200 dark:border-purple-800 bg-white dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-purple-600 dark:text-purple-400">SDK Languages</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{posture.sdk_support.languages.length}</p>
                <p className="text-xs text-slate-400">{posture.sdk_support.languages.join(', ')}</p>
              </div>
              <div className="rounded-lg border border-purple-200 dark:border-purple-800 bg-white dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-purple-600 dark:text-purple-400">Auth Model</p>
                <p className="mt-1 text-sm font-semibold dark:text-white">{posture.sdk_support.auth_model}</p>
                <p className="text-xs text-slate-400">{posture.sdk_support.api_keys} keys · {posture.sdk_support.active_routes} routes</p>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-5 space-y-4">
            <h2 className="text-base font-semibold dark:text-white">Endpoint Ownership</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {(Object.entries(posture.endpoint_ownership) as [string, { host: string; families: string[] }][]).map(([key, val]) => {
                const Icon = ownershipIcons[key] || Server
                return (
                  <div key={key} className={`rounded-lg border ${ownershipColors[key] || ''} bg-white dark:bg-slate-900/50 px-4 py-3`}>
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      <p className="text-[11px] uppercase tracking-wide font-semibold">{ownershipLabels[key] || key}</p>
                    </div>
                    <p className="mt-1 text-sm font-mono dark:text-white">{val.host}</p>
                    <p className="mt-1 text-xs text-slate-400">{val.families.length} families: {val.families.slice(0, 5).join(', ')}{val.families.length > 5 ? ` +${val.families.length - 5} more` : ''}</p>
                  </div>
                )
              })}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-5 space-y-3">
            <h2 className="text-base font-semibold dark:text-white">Observe Context (30d)</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-500">Requests</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{posture.observe_context.requests_30d}</p>
              </div>
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-500">Audit Events</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{posture.observe_context.audit_events_30d}</p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link href="/gateway" className="text-xs text-purple-600 hover:underline dark:text-purple-400">Model Gateway</Link>
            <Link href="/pipeline-studio" className="text-xs text-purple-600 hover:underline dark:text-purple-400">Pipeline Studio</Link>
            <Link href="/analytics" className="text-xs text-purple-600 hover:underline dark:text-purple-400">Analytics</Link>
            <Link href="/governance" className="text-xs text-purple-600 hover:underline dark:text-purple-400">Governance</Link>
            <Link href="/admin/settings" className="text-xs text-purple-600 hover:underline dark:text-purple-400">Platform Settings</Link>
          </div>
        </>
      )}
    </div>
  )
}
