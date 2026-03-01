import { getServerSession } from 'next-auth'
import { Suspense } from 'react'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import {
  getAnalyticsSummary,
  getSpendByFeature,
  getSpendByModel,
  getSpendOverTime,
} from '@/lib/api'
import SummaryCards from '@/components/analytics/SummaryCards'
import SpendOverTimeChart from '@/components/analytics/SpendOverTimeChart'
import SpendByModelChart from '@/components/analytics/SpendByModelChart'
import SpendByFeatureChart from '@/components/analytics/SpendByFeatureChart'
import TimeWindowPicker from '@/components/analytics/TimeWindowPicker'
import ExportButton from '@/components/analytics/ExportButton'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChevronRight } from 'lucide-react'

interface PageProps {
  searchParams: {
    from?: string
    to?: string
    preset?: string
    granularity?: string
  }
}

function defaultWindow() {
  const to = new Date()
  const from = new Date(to.getTime() - 7 * 24 * 3_600_000)
  return { from: from.toISOString(), to: to.toISOString() }
}

async function AnalyticsContent({ searchParams }: PageProps) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const window = {
    from: searchParams.from ?? defaultWindow().from,
    to: searchParams.to ?? defaultWindow().to,
  }
  const granularity =
    (searchParams.granularity as 'hourly' | 'daily' | undefined) ?? 'daily'

  const [summary, spendOverTime, spendByModel, spendByFeature] = await Promise.all([
    getAnalyticsSummary(session.apiKey, window),
    getSpendOverTime(session.apiKey, granularity, window),
    getSpendByModel(session.apiKey, window),
    getSpendByFeature(session.apiKey, window),
  ])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-end">
        <ExportButton apiKey={session.apiKey} from={window.from} to={window.to} />
      </div>
      <SummaryCards summary={summary} />

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">Spend Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          <SpendOverTimeChart data={spendOverTime} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">Spend by Model</CardTitle>
          </CardHeader>
          <CardContent>
            <SpendByModelChart items={spendByModel.items} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">Spend by Feature</CardTitle>
          </CardHeader>
          <CardContent>
            <SpendByFeatureChart items={spendByFeature.items} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default function AnalyticsPage({ searchParams }: PageProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Analytics</h1>
        <div className="flex items-center gap-3">
          <Suspense>
            <TimeWindowPicker currentPreset={searchParams.preset ?? '7d'} />
          </Suspense>
          <Link
            href="/analytics/users"
            className="flex items-center gap-1 text-sm text-indigo-600 hover:underline"
          >
            Top Spenders <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
      </div>

      <Suspense
        fallback={
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-28 w-full rounded-xl" />
              ))}
            </div>
            <Skeleton className="h-64 w-full rounded-xl" />
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Skeleton className="h-64 w-full rounded-xl" />
              <Skeleton className="h-64 w-full rounded-xl" />
            </div>
          </div>
        }
      >
        <AnalyticsContent searchParams={searchParams} />
      </Suspense>
    </div>
  )
}
