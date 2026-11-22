import Link from 'next/link'

/** 404 for any unknown route. */
export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f3f6fa] p-6 dark:bg-[#0a0e1a]">
      <div className="max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">404</p>
        <h1 className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">Page not found</h1>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">The page you asked for doesn&apos;t exist or has moved.</p>
        <Link href="/analytics" className="mt-5 inline-block rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white dark:bg-slate-100 dark:text-slate-900">
          Go to the overview
        </Link>
      </div>
    </main>
  )
}
