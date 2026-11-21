import type { ReactNode } from 'react'
import RunLedgerLogo from '@/components/brand/RunLedgerLogo'

/** Minimal centered card used by the public account pages (reset, verify). */
export default function AuthCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12 dark:bg-[#0a0e1a]">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-700/60 dark:bg-slate-900/70">
        <RunLedgerLogo markSize={32} wordmarkClassName="text-sm text-slate-950 dark:text-slate-50" />
        <h1 className="mt-6 text-xl font-semibold text-slate-950 dark:text-slate-50">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
        <div className="mt-6">{children}</div>
      </div>
    </main>
  )
}
