'use client'

import { useState } from 'react'
import { Check, Copy } from 'lucide-react'

/** Small copy-to-clipboard button for run, span and trace ids. */
export default function CopyId({ value, label }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      aria-label={label ?? `Copy ${value}`}
      title={copied ? 'Copied' : 'Copy id'}
      onClick={async e => {
        e.preventDefault()
        e.stopPropagation()
        try {
          await navigator.clipboard.writeText(value)
          setCopied(true)
          setTimeout(() => setCopied(false), 1500)
        } catch {
          setCopied(false)
        }
      }}
      className="ml-1 inline-flex rounded p-0.5 align-middle text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
    >
      {copied ? <Check className="h-3 w-3 text-status-success" /> : <Copy className="h-3 w-3" />}
    </button>
  )
}
