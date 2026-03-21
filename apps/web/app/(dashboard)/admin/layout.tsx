import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import { authOptions } from '@/lib/auth'

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions)
  const s = session as Record<string, unknown> | null

  if (!s?.isPlatformAdmin) {
    redirect('/runs')
  }

  return <>{children}</>
}
