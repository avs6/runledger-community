import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import { authOptions } from '@/lib/auth'

export const dynamic = 'force-dynamic'

export default async function RootPage() {
  const session = await getServerSession(authOptions)
  // Workflows are the landing object: every run, cost and control hangs off one.
  if (session) redirect('/workflows')
  redirect('/login')
}
