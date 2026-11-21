'use client'

import { Lock } from 'lucide-react'

/** Shown on pages a user can view but not change, so actions that would 403 are explained up front. */
export default function ReadOnlyNotice({ message }: { message?: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300">
      <Lock className="h-3.5 w-3.5 shrink-0" />
      <span>{message ?? 'Read-only: your role can view this page but not change it. Ask a workspace admin for edit access.'}</span>
    </div>
  )
}
