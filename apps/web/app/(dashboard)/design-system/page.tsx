'use client'

import Link from 'next/link'
import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Palette, RefreshCw, Sun, Moon, Layers, Gauge } from 'lucide-react'
import { getDesignSystemPosture } from '@/lib/api'
import type { DesignSystemPosture } from '@/types/api'

const scopeColorMap: Record<string, string> = {
  slate: 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-200 dark:text-slate-700',
  blue: 'bg-blue-100 text-blue-600 border-blue-200 dark:bg-blue-200 dark:text-blue-700',
  indigo: 'bg-indigo-100 text-indigo-600 border-indigo-200 dark:bg-indigo-200 dark:text-indigo-700',
  violet: 'bg-violet-100 text-violet-600 border-violet-200 dark:bg-violet-200 dark:text-violet-700',
  amber: 'bg-amber-100 text-amber-600 border-amber-200 dark:bg-amber-200 dark:text-amber-700',
}

const statusColorMap: Record<string, string> = {
  emerald: 'bg-emerald-500',
  amber: 'bg-amber-500',
  red: 'bg-red-500',
  blue: 'bg-blue-500',
  slate: 'bg-slate-500',
  orange: 'bg-orange-500',
}

export default function DesignSystemPage() {
  const { data: session } = useSession()
  const [posture, setPosture] = useState<DesignSystemPosture | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!session?.apiKey) return
    setLoading(true)
    try {
      const data = await getDesignSystemPosture(session.apiKey)
      setPosture(data)
    } catch {
      toast.error('Failed to load design system posture')
    } finally {
      setLoading(false)
    }
  }, [session?.apiKey])

  useEffect(() => { refresh() }, [refresh])

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold dark:text-white flex items-center gap-2">
            <Palette className="h-6 w-6 text-pink-500" />
            Design System
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Cross-app design tokens, scope visual language, dark mode, and density modes.
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

      {posture && (
        <>
          <div className="rounded-xl border border-pink-200 dark:border-pink-800 bg-white dark:bg-slate-800/40 p-5 space-y-4">
            <h2 className="text-base font-semibold dark:text-white flex items-center gap-2">
              <Layers className="h-4 w-4 text-pink-500" />
              Token System
            </h2>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-lg border border-pink-200 dark:border-pink-800 bg-white dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-pink-600 dark:text-pink-400">Color Tokens</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{posture.token_system.color_tokens}</p>
                <p className="text-xs text-slate-400">{posture.token_system.categories.join(', ')}</p>
              </div>
              <div className="rounded-lg border border-pink-200 dark:border-pink-800 bg-white dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-pink-600 dark:text-pink-400">Typography</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{posture.token_system.typography_stacks.length} stacks</p>
                <p className="text-xs text-slate-400">{posture.token_system.typography_stacks.map(s => s.split(' ')[0]).join(', ')}</p>
              </div>
              <div className="rounded-lg border border-pink-200 dark:border-pink-800 bg-white dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-pink-600 dark:text-pink-400">Elevation</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{posture.token_system.elevation_levels} levels</p>
                <p className="text-xs text-slate-400">sm, md, lg</p>
              </div>
              <div className="rounded-lg border border-pink-200 dark:border-pink-800 bg-white dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-pink-600 dark:text-pink-400">Chart Palette</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{posture.token_system.chart_palette_size} colors</p>
                <p className="text-xs text-slate-400">Radius: {posture.token_system.radius_default}</p>
              </div>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-5 space-y-4">
              <h2 className="text-base font-semibold dark:text-white flex items-center gap-2">
                <Sun className="h-4 w-4 text-amber-500" />
                <Moon className="h-4 w-4 text-blue-500" />
                Dark Mode
              </h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Strategy</span>
                  <span className="font-mono text-xs dark:text-white">{posture.dark_mode.strategy}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Palette</span>
                  <span className="dark:text-white">{posture.dark_mode.palette}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Contrast Target</span>
                  <span className="dark:text-white">{posture.dark_mode.contrast_ratio_target}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Legacy Overrides</span>
                  <span className={posture.dark_mode.legacy_overrides ? 'text-amber-600' : 'text-emerald-600'}>{posture.dark_mode.legacy_overrides ? 'Active (migrating)' : 'None'}</span>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-5 space-y-4">
              <h2 className="text-base font-semibold dark:text-white flex items-center gap-2">
                <Gauge className="h-4 w-4 text-teal-500" />
                Density Modes
              </h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Available</span>
                  <span className="dark:text-white">{posture.density_modes.available.join(', ')}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Default Row</span>
                  <span className="font-mono text-xs dark:text-white">{posture.density_modes.default_row_height}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Compact Row</span>
                  <span className="font-mono text-xs dark:text-white">{posture.density_modes.compact_row_height}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-xs">Compact surfaces:</span>
                  <p className="text-xs dark:text-white mt-0.5">{posture.density_modes.compact_surfaces.join(', ')}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-5 space-y-4">
            <h2 className="text-base font-semibold dark:text-white">Scope Visual Language</h2>
            <p className="text-xs text-slate-500">Each scope level has a distinct color so platform, org, workspace, access-group, and API-key contexts are instantly recognizable.</p>
            <div className="flex flex-wrap gap-2">
              {posture.scope_visual_language.scope_levels.map(level => {
                const color = posture.scope_visual_language.scope_colors[level] || 'slate'
                return (
                  <span key={level} className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium ${scopeColorMap[color] || scopeColorMap.slate}`}>
                    {level.replace(/_/g, ' ')}
                  </span>
                )
              })}
            </div>
            <div className="grid gap-3 sm:grid-cols-2 mt-2">
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-500">Access Groups</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{posture.scope_visual_language.access_groups}</p>
              </div>
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-500">API Keys</p>
                <p className="mt-1 text-lg font-semibold dark:text-white">{posture.scope_visual_language.api_keys}</p>
              </div>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-5 space-y-3">
              <h2 className="text-base font-semibold dark:text-white">Status Semantics</h2>
              <div className="space-y-1.5">
                {Object.entries(posture.status_semantics.operational_states).map(([state, color]) => (
                  <div key={state} className="flex items-center gap-2 text-sm">
                    <span className={`h-2.5 w-2.5 rounded-full ${statusColorMap[color] || 'bg-slate-500'}`} />
                    <span className="dark:text-white capitalize">{state}</span>
                    <span className="text-xs text-slate-400 ml-auto">{color}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-5 space-y-3">
              <h2 className="text-base font-semibold dark:text-white">Severity Levels</h2>
              <div className="space-y-1.5">
                {posture.status_semantics.severity_levels.map(level => {
                  const color = posture.status_semantics.severity_colors[level]
                  return (
                    <div key={level} className="flex items-center gap-2 text-sm">
                      <span className={`h-2.5 w-2.5 rounded-full ${statusColorMap[color] || 'bg-slate-500'}`} />
                      <span className="dark:text-white capitalize">{level}</span>
                      <span className="text-xs text-slate-400 ml-auto">{color}</span>
                    </div>
                  )
                })}
              </div>
              <div className="pt-2 border-t border-slate-100 dark:border-slate-700">
                <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-1.5">Runtime States</p>
                <div className="space-y-1.5">
                  {Object.entries(posture.status_semantics.runtime_states).map(([state, color]) => (
                    <div key={state} className="flex items-center gap-2 text-sm">
                      <span className={`h-2.5 w-2.5 rounded-full ${statusColorMap[color] || 'bg-slate-500'}`} />
                      <span className="dark:text-white capitalize">{state}</span>
                      <span className="text-xs text-slate-400 ml-auto">{color}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-5 space-y-3">
            <h2 className="text-base font-semibold dark:text-white">Layout Shells</h2>
            <div className="flex flex-wrap gap-2">
              {posture.layout_shells.shells.map(shell => (
                <span key={shell} className="inline-flex items-center rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 px-2.5 py-1 text-xs font-medium dark:text-white capitalize">
                  {shell.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
            <div className="grid gap-3 sm:grid-cols-3 text-sm mt-2">
              <div>
                <span className="text-slate-500">Sidebar</span>
                <p className="dark:text-white text-xs mt-0.5">{posture.layout_shells.sidebar_pattern}</p>
              </div>
              <div>
                <span className="text-slate-500">Max Width</span>
                <p className="font-mono text-xs dark:text-white mt-0.5">{posture.layout_shells.content_max_width}</p>
              </div>
              <div>
                <span className="text-slate-500">Breakpoints</span>
                <p className="dark:text-white text-xs mt-0.5">{posture.layout_shells.responsive_breakpoints.length} responsive</p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link href="/gateway" className="text-xs text-pink-600 hover:underline dark:text-pink-400">Model Gateway</Link>
            <Link href="/api-docs" className="text-xs text-pink-600 hover:underline dark:text-pink-400">API Explorer</Link>
            <Link href="/analytics" className="text-xs text-pink-600 hover:underline dark:text-pink-400">Analytics</Link>
            <Link href="/admin/settings" className="text-xs text-pink-600 hover:underline dark:text-pink-400">Platform Settings</Link>
          </div>
        </>
      )}
    </div>
  )
}
