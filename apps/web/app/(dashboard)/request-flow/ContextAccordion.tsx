'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ChevronDown } from 'lucide-react'

interface ContextSection {
  color: string
  label: string
  summary: string
  links: { href: string; text: string }[]
}

const colorMap: Record<string, { border: string; bg: string; label: string; link: string; dot: string }> = {
  cyan: {
    border: 'border-cyan-200 dark:border-cyan-900/40',
    bg: 'bg-cyan-50/60 dark:bg-cyan-950/20',
    label: 'text-cyan-700 dark:text-cyan-200',
    link: 'text-cyan-700 hover:text-cyan-900 dark:text-cyan-200 dark:hover:text-cyan-50',
    dot: 'bg-cyan-500',
  },
  emerald: {
    border: 'border-emerald-200 dark:border-emerald-900/40',
    bg: 'bg-emerald-50/60 dark:bg-emerald-950/20',
    label: 'text-emerald-700 dark:text-emerald-200',
    link: 'text-emerald-700 hover:text-emerald-900 dark:text-emerald-200 dark:hover:text-emerald-50',
    dot: 'bg-emerald-500',
  },
  blue: {
    border: 'border-blue-200 dark:border-blue-900/40',
    bg: 'bg-blue-50/60 dark:bg-blue-950/20',
    label: 'text-blue-700 dark:text-blue-200',
    link: 'text-blue-700 hover:text-blue-900 dark:text-blue-200 dark:hover:text-blue-50',
    dot: 'bg-blue-500',
  },
  violet: {
    border: 'border-violet-200 dark:border-violet-900/40',
    bg: 'bg-violet-50/60 dark:bg-violet-950/20',
    label: 'text-violet-700 dark:text-violet-200',
    link: 'text-violet-700 hover:text-violet-900 dark:text-violet-200 dark:hover:text-violet-50',
    dot: 'bg-violet-500',
  },
}

export default function ContextAccordion({ sections }: { sections: ContextSection[] }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-xl border border-slate-200 bg-white/80 shadow-sm dark:border-slate-800 dark:bg-slate-950/45">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-2.5"
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500 dark:text-slate-400">
            Investigation Context
          </span>
          <div className="flex gap-1.5">
            {sections.map((s) => (
              <span
                key={s.label}
                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${colorMap[s.color]?.label ?? 'text-slate-600 dark:text-slate-300'} ${colorMap[s.color]?.bg ?? 'bg-slate-100 dark:bg-slate-800'}`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${colorMap[s.color]?.dot ?? 'bg-slate-400'}`} />
                {s.label}
              </span>
            ))}
          </div>
        </div>
        <ChevronDown className={`h-4 w-4 text-slate-400 transition-transform ${open ? '' : '-rotate-90'}`} />
      </button>

      {open && (
        <div className="space-y-0 border-t border-slate-100 dark:border-slate-800">
          {sections.map((s) => {
            const colors = colorMap[s.color] ?? colorMap.blue
            return (
              <div key={s.label} className={`border-b last:border-b-0 ${colors.border} ${colors.bg} px-4 py-3`}>
                <div className="flex flex-col gap-1.5 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0 flex-1">
                    <p className={`text-[10px] font-semibold uppercase tracking-[0.15em] ${colors.label}`}>{s.label} Context</p>
                    <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">{s.summary}</p>
                  </div>
                  <div className="flex flex-wrap gap-x-2 gap-y-1 text-[10px] font-semibold">
                    {s.links.map((l) => (
                      <Link key={l.href} href={l.href} className={`hover:underline ${colors.link}`}>{l.text}</Link>
                    ))}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
