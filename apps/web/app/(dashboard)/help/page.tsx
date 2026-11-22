'use client'

import Link from 'next/link'
import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  HelpCircle, RefreshCw, Activity, Wrench, Network, Shield,
  PiggyBank, Building2, Settings, BookOpen, Zap, GitBranch,
  Search, Bot, BarChart2, FileText,
} from 'lucide-react'

const sectionIcons: Record<string, typeof Activity> = {
  observe: Activity,
  build: Bot,
  gateway: Network,
  governance: Shield,
  finops: PiggyBank,
  org_access: Building2,
  platform: Settings,
}

const sectionColors: Record<string, string> = {
  observe: 'border-blue-200 dark:border-blue-800 text-blue-600 dark:text-blue-400',
  build: 'border-violet-200 dark:border-violet-800 text-violet-600 dark:text-violet-400',
  gateway: 'border-emerald-200 dark:border-emerald-800 text-emerald-600 dark:text-emerald-400',
  governance: 'border-amber-200 dark:border-amber-800 text-amber-600 dark:text-amber-400',
  finops: 'border-rose-200 dark:border-rose-800 text-rose-600 dark:text-rose-400',
  org_access: 'border-indigo-200 dark:border-indigo-800 text-indigo-600 dark:text-indigo-400',
  platform: 'border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-400',
}

const sectionRoutes: Record<string, string> = {
  observe: '/analytics',
  build: '/agents',
  gateway: '/gateway',
  governance: '/tool-registry',
  finops: '/cost-savings',
  org_access: '/organization',
  platform: '/settings',
}

export default function HelpHubPage() {
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
            <HelpCircle className="h-6 w-6 text-sky-500" />
            Help Hub
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Contextual help, feature guides, and quick links to every RunLedger surface. Start here to find your way around.
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
            API Reference
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
