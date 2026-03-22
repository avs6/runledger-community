'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { CreditCard, Zap, TrendingUp, Building2, CheckCircle2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { getSubscription, createCheckout } from '@/lib/api'
import type { SubscriptionResponse } from '@/types/api'

const PLANS = [
  {
    key: 'free',
    name: 'Free',
    price: '$0',
    period: 'forever',
    events: '10,000 events/mo',
    features: ['Full observability', 'Run explorer + DAG viewer', 'Basic analytics', '1 workspace'],
    highlight: false,
  },
  {
    key: 'starter',
    name: 'Starter',
    price: '$49',
    period: '/month',
    events: '500,000 events/mo',
    features: ['Everything in Free', 'Budget enforcement', 'Slack alerts', 'Prompt management', '5 workspaces'],
    highlight: true,
  },
  {
    key: 'growth',
    name: 'Growth',
    price: '$199',
    period: '/month',
    events: '5M events/mo',
    features: ['Everything in Starter', 'Chargeback + billing export', 'Replay harness', 'RBAC', 'Unlimited workspaces'],
    highlight: false,
  },
  {
    key: 'enterprise',
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    events: '100M+ events/mo',
    features: ['Everything in Growth', 'SSO / SAML', 'Custom data retention', 'Dedicated support', 'SLA'],
    highlight: false,
  },
]

const PLAN_ICON: Record<string, React.ElementType> = {
  free: Zap,
  starter: TrendingUp,
  growth: CreditCard,
  enterprise: Building2,
}

function UsageMeter({ used, limit, pct }: { used: number; limit: number; pct: number }) {
  const color = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-500' : 'bg-teal-500'
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-600 dark:text-slate-400">Events this month</span>
        <span className="font-mono font-semibold text-slate-900 dark:text-white">
          {used.toLocaleString()} / {limit.toLocaleString()}
        </span>
      </div>
      <div className="h-2.5 w-full rounded-full bg-slate-200 dark:bg-slate-700">
        <div
          className={`h-2.5 rounded-full transition-all ${color}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <div className="text-right text-xs text-slate-500 dark:text-slate-400">{pct.toFixed(1)}% used</div>
    </div>
  )
}

export default function SubscriptionPage() {
  const { data: session } = useSession()
  const [sub, setSub] = useState<SubscriptionResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [upgrading, setUpgrading] = useState<string | null>(null)

  useEffect(() => {
    if (!session?.apiKey) return
    getSubscription(session.apiKey)
      .then(setSub)
      .catch(() => toast.error('Failed to load subscription'))
      .finally(() => setLoading(false))
  }, [session?.apiKey])

  async function handleUpgrade(plan: string) {
    if (!session?.apiKey) return
    setUpgrading(plan)
    try {
      const origin = window.location.origin
      const { checkout_url } = await createCheckout(
        session.apiKey,
        plan,
        `${origin}/billing/subscription?upgraded=1`,
        `${origin}/billing/subscription`,
      )
      window.location.href = checkout_url
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to start checkout'
      toast.error(msg)
    } finally {
      setUpgrading(null)
    }
  }

  const currentPlan = sub?.plan ?? 'free'
  const isOverQuota = sub ? sub.usage_pct >= 90 : false

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Subscription</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Manage your plan and monitor monthly event usage.
        </p>
      </div>

      {/* Quota exceeded banner */}
      {isOverQuota && (
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-800/40 dark:bg-red-900/20 dark:text-red-300">
          <Zap className="h-4 w-4 shrink-0" />
          <span>
            You have used {sub!.usage_pct.toFixed(0)}% of your monthly quota.
            Upgrade your plan to avoid ingestion being blocked.
          </span>
        </div>
      )}

      {/* Current plan + usage */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            {(() => { const Icon = PLAN_ICON[currentPlan] ?? Zap; return <Icon className="h-4 w-4 text-teal-600" /> })()}
            Current plan:{' '}
            <span className="capitalize font-bold text-teal-700 dark:text-teal-400">{currentPlan}</span>
            <Badge variant={sub?.status === 'active' ? 'default' : 'secondary'} className="ml-2 capitalize">
              {sub?.status ?? 'active'}
            </Badge>
          </CardTitle>
          {sub?.current_period_end && (
            <CardDescription>
              Renews {new Date(sub.current_period_end).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="h-10 animate-pulse rounded-md bg-slate-200 dark:bg-slate-700" />
          ) : sub ? (
            <UsageMeter used={sub.events_used} limit={sub.events_limit} pct={sub.usage_pct} />
          ) : null}
        </CardContent>
      </Card>

      {/* Plan comparison */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {PLANS.map(plan => {
          const isCurrent = plan.key === currentPlan
          const isPaid = plan.key !== 'free' && plan.key !== 'enterprise'
          return (
            <Card
              key={plan.key}
              className={`relative flex flex-col ${plan.highlight ? 'border-teal-500 ring-1 ring-teal-500' : ''}`}
            >
              {plan.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-teal-600 px-3 py-0.5 text-xs font-semibold text-white">
                  Most popular
                </div>
              )}
              <CardHeader className="pb-3">
                <CardTitle className="text-base">{plan.name}</CardTitle>
                <CardDescription>
                  <span className="text-2xl font-bold text-slate-900 dark:text-white">{plan.price}</span>
                  <span className="text-sm text-slate-500">{plan.period}</span>
                </CardDescription>
                <p className="text-xs text-teal-700 dark:text-teal-400 font-medium">{plan.events}</p>
              </CardHeader>
              <CardContent className="flex flex-1 flex-col justify-between gap-4">
                <ul className="space-y-1.5">
                  {plan.features.map(f => (
                    <li key={f} className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-teal-500" />
                      {f}
                    </li>
                  ))}
                </ul>
                {isCurrent ? (
                  <Button variant="outline" disabled className="w-full">Current plan</Button>
                ) : plan.key === 'enterprise' ? (
                  <Button variant="outline" className="w-full" asChild>
                    <a href="mailto:sales@runledger.io">Contact sales</a>
                  </Button>
                ) : isPaid ? (
                  <Button
                    className="w-full bg-teal-600 hover:bg-teal-700 text-white"
                    disabled={upgrading === plan.key}
                    onClick={() => handleUpgrade(plan.key)}
                  >
                    {upgrading === plan.key ? 'Redirecting…' : `Upgrade to ${plan.name}`}
                  </Button>
                ) : null}
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
