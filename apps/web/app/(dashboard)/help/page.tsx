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
import { getHelpHubPosture } from '@/lib/api'
import type { HelpHubPosture } from '@/types/api'

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
  const [posture, setPosture] = useState<HelpHubPosture | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!session?.apiKey) return
    setLoading(true)
    try {
      const data = await getHelpHubPosture(session.apiKey)
      setPosture(data)
    } catch {
      toast.error('Failed to load help hub posture')
    } finally {
      setLoading(false)
    }
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

      {posture && (
        <>
          <div className="rounded-xl border border-sky-200 dark:border-sky-800 bg-sky-50/30 dark:bg-sky-900/20 p-5 space-y-4">
            <h2 className="text-base font-semibold text-sky-900 dark:text-sky-100">Quick Start</h2>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <Link href="/request-flow/live" className="rounded-lg border border-sky-200 dark:border-sky-800 bg-white dark:bg-slate-900/50 px-4 py-3 hover:bg-sky-50 dark:hover:bg-slate-800/50 transition-colors">
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-sky-600 dark:text-sky-400" />
                  <p className="text-sm font-semibold dark:text-white">Live Pipeline</p>
                </div>
                <p className="mt-1 text-xs text-slate-400">Watch requests stream through your pipeline in real time</p>
              </Link>
              <Link href="/pipeline" className="rounded-lg border border-sky-200 dark:border-sky-800 bg-white dark:bg-slate-900/50 px-4 py-3 hover:bg-sky-50 dark:hover:bg-slate-800/50 transition-colors">
                <div className="flex items-center gap-2">
                  <GitBranch className="h-4 w-4 text-sky-600 dark:text-sky-400" />
                  <p className="text-sm font-semibold dark:text-white">Pipeline Designer</p>
                </div>
                <p className="mt-1 text-xs text-slate-400">Design and configure your request processing pipeline</p>
              </Link>
              <Link href="/api-docs" className="rounded-lg border border-sky-200 dark:border-sky-800 bg-white dark:bg-slate-900/50 px-4 py-3 hover:bg-sky-50 dark:hover:bg-slate-800/50 transition-colors">
                <div className="flex items-center gap-2">
                  <Search className="h-4 w-4 text-sky-600 dark:text-sky-400" />
                  <p className="text-sm font-semibold dark:text-white">API Explorer</p>
                </div>
                <p className="mt-1 text-xs text-slate-400">Browse endpoints, try requests, and generate SDK snippets</p>
              </Link>
              <Link href="/analytics" className="rounded-lg border border-sky-200 dark:border-sky-800 bg-white dark:bg-slate-900/50 px-4 py-3 hover:bg-sky-50 dark:hover:bg-slate-800/50 transition-colors">
                <div className="flex items-center gap-2">
                  <BarChart2 className="h-4 w-4 text-sky-600 dark:text-sky-400" />
                  <p className="text-sm font-semibold dark:text-white">Analytics</p>
                </div>
                <p className="mt-1 text-xs text-slate-400">Dashboards, cost analysis, and usage insights</p>
              </Link>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-5 space-y-4">
            <h2 className="text-base font-semibold dark:text-white">Feature Guides</h2>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {Object.entries(posture.contextual_links).map(([key, section]) => {
                const Icon = sectionIcons[key] || FileText
                const color = sectionColors[key] || 'border-slate-200 dark:border-slate-700 text-slate-600'
                const route = sectionRoutes[key] || '/'
                return (
                  <Link key={key} href={route} className={`rounded-lg border ${color} bg-white dark:bg-slate-900/50 px-4 py-3 hover:shadow-sm transition-shadow`}>
                    <div className="flex items-center gap-2 mb-2">
                      <Icon className="h-4 w-4" />
                      <p className="text-sm font-semibold">{section.label}</p>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">{section.pages.length} pages</p>
                    <div className="flex flex-wrap gap-1">
                      {section.help_topics.slice(0, 4).map(topic => (
                        <span key={topic} className="inline-block rounded-full bg-slate-100 dark:bg-slate-700 px-2 py-0.5 text-[10px] text-slate-600 dark:text-slate-300">
                          {topic.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  </Link>
                )
              })}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-5 space-y-4">
            <h2 className="text-base font-semibold dark:text-white">Platform Readiness</h2>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-500">API Keys</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{posture.platform_readiness.api_keys}</p>
                <p className="text-xs text-slate-400">Active workspace keys</p>
              </div>
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-500">SDK Languages</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{posture.platform_readiness.sdk_languages.length}</p>
                <p className="text-xs text-slate-400">{posture.platform_readiness.sdk_languages.join(', ')}</p>
              </div>
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-500">Content Coverage</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{Object.values(posture.content_coverage).filter(Boolean).length}</p>
                <p className="text-xs text-slate-400">{Object.keys(posture.content_coverage).length} guide areas</p>
              </div>
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-500">Requests (30d)</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{posture.observe_context.requests_30d}</p>
                <p className="text-xs text-slate-400">{posture.observe_context.audit_events_30d} audit events</p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link href="/api-docs" className="text-xs text-sky-600 hover:underline dark:text-sky-400">API Explorer</Link>
            <Link href="/gateway" className="text-xs text-sky-600 hover:underline dark:text-sky-400">Model Gateway</Link>
            <Link href="/pipeline-studio" className="text-xs text-sky-600 hover:underline dark:text-sky-400">Pipeline Studio</Link>
            <Link href="/analytics" className="text-xs text-sky-600 hover:underline dark:text-sky-400">Analytics</Link>
            <Link href="/onboarding" className="text-xs text-sky-600 hover:underline dark:text-sky-400">Onboarding</Link>
          </div>
        </>
      )}
    </div>
  )
}
