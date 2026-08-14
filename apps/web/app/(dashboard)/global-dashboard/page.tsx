import { redirect } from 'next/navigation'

export default async function GlobalDashboardPage({
  searchParams,
}: {
  searchParams?: { range?: string }
}) {
  const params = new URLSearchParams()
  params.set('scope', 'platform')
  params.set('view', 'overview')
  if (searchParams?.range) params.set('range', searchParams.range)
  redirect(`/analytics?${params.toString()}`)
}
