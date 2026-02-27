'use client'

import { SessionProvider as NextAuthProvider } from 'next-auth/react'
import type { Session } from 'next-auth'

export default function SessionProvider({
  children,
  session,
}: {
  children: React.ReactNode
  session: Session | null
}) {
  return <NextAuthProvider session={session}>{children}</NextAuthProvider>
}
