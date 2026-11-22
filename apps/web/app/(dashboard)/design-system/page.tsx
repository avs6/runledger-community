'use client'

import Link from 'next/link'
import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Palette, RefreshCw, Sun, Moon, Layers, Gauge } from 'lucide-react'

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

    </div>
  )
}
