'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import Link from 'next/link'
import { Rocket, CheckCircle2, Circle } from 'lucide-react'
import { getOnboardingStatus, triggerDemoSeed } from '@/lib/api'
import type { OnboardingStatus } from '@/types/api'

const STEPS: { key: keyof OnboardingStatus; label: string; description: string; href: string }[] = [
  { key: 'has_org', label: 'Create Organization', description: 'Set up your organization to manage teams and billing', href: '/organization' },
  { key: 'has_workspace', label: 'Set Up Workspace', description: 'Create a workspace to group your AI workloads', href: '/workspace' },
  { key: 'has_api_key', label: 'Generate API Key', description: 'Create an API key to authenticate your requests', href: '/api-keys' },
  { key: 'has_first_run', label: 'Send First Run', description: 'Log your first LLM inference run through RunLedger', href: '/runs' },
  { key: 'has_gateway_route', label: 'Configure Gateway Route', description: 'Route LLM traffic through the RunLedger gateway', href: '/gateway' },
  { key: 'has_budget', label: 'Set a Budget', description: 'Define spending limits for your AI operations', href: '/budgets' },
  { key: 'has_alert_rule', label: 'Create Alert Rule', description: 'Get notified when costs or usage cross a threshold', href: '/alert-rules' },
]

export default function OnboardingPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''
  const [status, setStatus] = useState<OnboardingStatus | null>(null)
  const [seeding, setSeeding] = useState(false)

  useEffect(() => {
    if (!apiKey) return
    getOnboardingStatus(apiKey).then(setStatus).catch(() => toast.error('Failed to load onboarding status'))
  }, [apiKey])

  const handleSeed = async () => {
    setSeeding(true)
    try {
      await triggerDemoSeed(apiKey)
      toast.success('Demo seed started in background')
      const updated = await getOnboardingStatus(apiKey)
      setStatus(updated)
    } catch {
      toast.error('Failed to trigger demo seed')
    } finally {
      setSeeding(false)
    }
  }

  if (!status) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 py-10">
      <div className="flex items-center gap-3">
        <Rocket className="h-8 w-8 text-blue-500" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Getting Started</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Complete these steps to get the most out of RunLedger</p>
        </div>
      </div>

      <div className="space-y-2">
        <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
          <div
            className="h-full rounded-full bg-blue-500 transition-all duration-500"
            style={{ width: `${status.pct}%` }}
          />
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {status.completed} of {status.total} steps completed
        </p>
      </div>

      {status.pct === 100 && (
        <div className="rounded-2xl border border-green-200 bg-green-50 p-4 text-center text-green-700 dark:border-green-800 dark:bg-green-900/30 dark:text-green-300">
          You&apos;re all set! RunLedger is fully configured.
        </div>
      )}

      <div className="space-y-3">
        {STEPS.map((step) => {
          const done = !!status[step.key]
          return (
            <Link key={step.key} href={step.href}>
              <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800">
                {done ? (
                  <CheckCircle2 className="h-6 w-6 shrink-0 text-green-500" />
                ) : (
                  <Circle className="h-6 w-6 shrink-0 text-slate-400" />
                )}
                <div className="min-w-0 flex-1">
                  <p className={`font-medium ${done ? 'text-slate-400 line-through dark:text-slate-500' : ''}`}>{step.label}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{step.description}</p>
                </div>
              </div>
            </Link>
          )
        })}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <h2 className="mb-1 font-semibold">Seed Demo Data</h2>
        <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">Populate your account with sample data to explore RunLedger features.</p>
        <button
          onClick={handleSeed}
          disabled={seeding}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium transition-colors hover:bg-slate-100 disabled:opacity-50 dark:border-slate-600 dark:hover:bg-slate-800"
        >
          {seeding ? 'Seeding…' : 'Seed Demo Data'}
        </button>
      </div>
    </div>
  )
}
