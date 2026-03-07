'use client'

import { useSession } from 'next-auth/react'
import { useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Download } from 'lucide-react'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export default function RunsExportButton() {
  const { data: session } = useSession()
  const params = useSearchParams()

  async function handleExport() {
    const apiKey = (session as { apiKey?: string })?.apiKey
    if (!apiKey) return

    const exportParams = new URLSearchParams()
    for (const key of ['status', 'feature_tag', 'end_user_id', 'search', 'from', 'to', 'model', 'min_cost', 'max_cost']) {
      const v = params.get(key)
      if (v) exportParams.set(key, v)
    }

    const res = await fetch(`${BASE_URL}/runs/export?${exportParams.toString()}`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    })
    if (!res.ok) return

    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'runs.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Button variant="outline" size="sm" className="h-8 gap-1 text-sm" onClick={handleExport}>
      <Download className="h-3.5 w-3.5" />
      Export CSV
    </Button>
  )
}
