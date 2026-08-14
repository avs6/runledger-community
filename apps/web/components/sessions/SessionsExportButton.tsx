'use client'

import { useSession } from 'next-auth/react'
import { Download } from 'lucide-react'
import { toast } from 'sonner'

export default function SessionsExportButton({
  queryString,
}: {
  queryString: string
}) {
  const { data: session } = useSession()

  async function handleExport() {
    const apiKey = (session as { apiKey?: string } | null)?.apiKey
    if (!apiKey) {
      toast.error('Missing session API key')
      return
    }
    const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
    const url = `${base}/sessions/export${queryString ? `?${queryString}` : ''}`
    try {
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${apiKey}` },
      })
      if (!response.ok) throw new Error(await response.text())
      const blob = await response.blob()
      const href = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = href
      link.download = 'sessions.csv'
      link.click()
      URL.revokeObjectURL(href)
      toast.success('Sessions export downloaded')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to export sessions'
      toast.error(message)
    }
  }

  return (
    <button
      type="button"
      onClick={handleExport}
      className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
    >
      <Download className="h-4 w-4" />
      Export
    </button>
  )
}
