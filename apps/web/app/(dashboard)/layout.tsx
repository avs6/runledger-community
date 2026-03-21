import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import { authOptions } from '@/lib/auth'
import Sidebar from '@/components/layout/Sidebar'
import TopBar from '@/components/layout/TopBar'
import SessionProvider from '@/components/layout/SessionProvider'
import { ThemeProvider } from '@/components/providers/ThemeProvider'
import { Toaster } from 'sonner'

const API_URL =
  process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

/**
 * Lightweight API key probe. Returns false if the key is invalid (401),
 * true on success or any non-401 error (fail-open so a network blip
 * doesn't log everyone out).
 */
async function isApiKeyValid(apiKey: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/settings/api-keys?limit=1`, {
      headers: { Authorization: `Bearer ${apiKey}` },
      cache: 'no-store',
    })
    return res.status !== 401
  } catch {
    return true // network error — don't force sign-out
  }
}

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/login')

  // If the stored API key is stale (DB was wiped / key was revoked),
  // clear the session cookie by signing out and send to login.
  const valid = await isApiKeyValid(session.apiKey)
  if (!valid) redirect('/api/auth/signout?callbackUrl=/login')

  return (
    <ThemeProvider>
      <SessionProvider session={session}>
        <div className="flex h-screen overflow-hidden bg-transparent">
          <Sidebar />
          <div className="flex flex-1 flex-col overflow-hidden">
            <TopBar />
            <main className="flex-1 overflow-auto p-4 sm:p-6">
              <div className="mx-auto w-full max-w-[1600px]">{children}</div>
            </main>
          </div>
        </div>
        <Toaster position="top-right" richColors />
      </SessionProvider>
    </ThemeProvider>
  )
}
