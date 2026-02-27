'use client'

import { signOut, useSession } from 'next-auth/react'
import { Button } from '@/components/ui/button'
import { LogOut } from 'lucide-react'

export default function TopBar() {
  const { data: session } = useSession()

  return (
    <header className="flex h-12 items-center justify-between border-b border-gray-200 bg-white px-4">
      <span className="text-sm font-medium text-gray-700">
        {session?.workspaceName ?? ''}
      </span>
      <Button
        variant="ghost"
        size="sm"
        className="gap-1.5 text-gray-600"
        onClick={() => signOut({ callbackUrl: '/login' })}
      >
        <LogOut className="h-3.5 w-3.5" />
        Sign out
      </Button>
    </header>
  )
}
