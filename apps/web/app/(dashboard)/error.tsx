'use client'

import { useEffect } from 'react'
import Link from 'next/link'

/** Error boundary for dashboard pages: a page that throws shows this instead of a blank screen. */
export default function DashboardError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error)
  }, [error])
  return (
    <div className="mx-auto max-w-xl rounded-2xl border border-rose-200 bg-white p-8 text-center shadow-sm dark:border-rose-900/50 dark:bg-slate-900">
      <h1 className="text-lg font-semibold text-slate-900 dark:text-white">This page hit an error</h1>
      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
        Something went wrong while loading it. Try again, or go back to the overview.
      </p>
      {error.digest ? <p className="mt-2 font-mono text-[11px] text-slate-400">Reference: {error.digest}</p> : null}
      <div className="mt-5 flex justify-center gap-2">
        <button
          type="button"
          onClick={reset}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900"
        >
          Try again
        </button>
        <Link href="/analytics" className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 dark:border-slate-700 dark:text-slate-200">
          Overview
        </Link>
      </div>
    </div>
  )
}
