import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import { authOptions } from '@/lib/auth'
import Sidebar from '@/components/layout/Sidebar'
import TopBar from '@/components/layout/TopBar'
import SessionProvider from '@/components/layout/SessionProvider'
import { ThemeProvider } from '@/components/providers/ThemeProvider'

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/login')

  return (
    <ThemeProvider>
      <SessionProvider session={session}>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <div className="flex flex-1 flex-col overflow-hidden">
            <TopBar />
            <main className="flex-1 overflow-auto bg-gray-50 p-6">{children}</main>
          </div>
        </div>
      </SessionProvider>
    </ThemeProvider>
  )
}
