'use client'

import { signOut, useSession } from 'next-auth/react'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import { LogOut, Moon, Sun } from 'lucide-react'

export default function TopBar() {
  const { data: session } = useSession()
  const { resolvedTheme, setTheme } = useTheme()

  return (
    <header className="flex h-12 items-center justify-between border-b border-gray-200 bg-white px-4 dark:border-gray-700 dark:bg-gray-900">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
        {session?.workspaceName ?? ''}
      </span>
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 text-gray-600 dark:text-gray-400"
          onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
          aria-label="Toggle theme"
        >
          {resolvedTheme === 'dark' ? (
            <Sun className="h-3.5 w-3.5" />
          ) : (
            <Moon className="h-3.5 w-3.5" />
          )}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 text-gray-600 dark:text-gray-400"
          onClick={() => signOut({ callbackUrl: '/login' })}
        >
          <LogOut className="h-3.5 w-3.5" />
          Sign out
        </Button>
      </div>
    </header>
  )
}
