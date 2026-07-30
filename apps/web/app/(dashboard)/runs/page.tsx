import { getServerSession } from 'next-auth'
import { Suspense } from 'react'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getRuns } from '@/lib/api'
import RunsTable from '@/components/runs/RunsTable'
import RunFilters from '@/components/runs/RunFilters'
import RunsExportButton from '@/components/runs/RunsExportButton'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

interface PageProps {
  searchParams: {
    status?: string
    feature_tag?: string
    end_user_id?: string
    search?: string
    from?: string
    to?: string
    cursor?: string
    preset?: string
    model?: string
    min_cost?: string
    max_cost?: string
  }
}

async function RunsContent({ searchParams }: PageProps) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 3_600_000).toISOString()

  const data = await getRuns(session.apiKey, {
    limit: 50,
    status: searchParams.status,
    feature_tag: searchParams.feature_tag,
    end_user_id: searchParams.end_user_id,
    search: searchParams.search,
    from: searchParams.from ?? sevenDaysAgo,
    to: searchParams.to,
    cursor: searchParams.cursor,
    model: searchParams.model,
    min_cost: searchParams.min_cost,
    max_cost: searchParams.max_cost,
  })

  const nextHref = data.next_cursor
    ? `/runs?${new URLSearchParams({
        ...Object.fromEntries(
          Object.entries(searchParams).filter(([, v]) => v !== undefined) as [
            string,
            string,
          ][],
        ),
        cursor: data.next_cursor,
      }).toString()}`
    : null

  return (
    <>
      <RunsTable items={data.items} />
      {nextHref && (
        <div className="mt-4 flex justify-center">
          <Button variant="outline" size="sm" asChild>
            <Link href={nextHref}>Load more</Link>
          </Button>
        </div>
      )}
    </>
  )
}

export default function RunsPage({ searchParams }: PageProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Runs</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href="/request-explorer">Request Explorer</Link>
          </Button>
          <Suspense fallback={null}>
            <RunsExportButton />
          </Suspense>
        </div>
      </div>
      <Suspense fallback={null}>
        <RunFilters />
      </Suspense>
      <Suspense
        fallback={
          <div className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        }
      >
        <RunsContent searchParams={searchParams} />
      </Suspense>
    </div>
  )
}
