import { getServerSession } from 'next-auth'
import { Suspense } from 'react'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getSpendByUser } from '@/lib/api'
import TopSpendersTable from '@/components/analytics/TopSpendersTable'
import TimeWindowPicker from '@/components/analytics/TimeWindowPicker'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChevronLeft } from 'lucide-react'

interface PageProps {
  searchParams: {
    from?: string
    to?: string
    preset?: string
  }
}

function defaultWindow() {
  const to = new Date()
  const from = new Date(to.getTime() - 7 * 24 * 3_600_000)
  return { from: from.toISOString(), to: to.toISOString() }
}

async function TopSpendersContent({ searchParams }: PageProps) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const window = {
    from: searchParams.from ?? defaultWindow().from,
    to: searchParams.to ?? defaultWindow().to,
  }

  const data = await getSpendByUser(session.apiKey, 50, window)

  return <TopSpendersTable items={data.items} />
}

export default function UsersPage({ searchParams }: PageProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Link
            href="/analytics"
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
          >
            <ChevronLeft className="h-4 w-4" />
            Analytics
          </Link>
          <span className="text-sm text-gray-400">/</span>
          <h1 className="text-xl font-semibold">Top Spenders</h1>
        </div>
        <Suspense>
          <TimeWindowPicker currentPreset={searchParams.preset ?? '7d'} />
        </Suspense>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">Users by Spend</CardTitle>
        </CardHeader>
        <CardContent>
          <Suspense
            fallback={
              <div className="space-y-2">
                {Array.from({ length: 10 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            }
          >
            <TopSpendersContent searchParams={searchParams} />
          </Suspense>
        </CardContent>
      </Card>
    </div>
  )
}
