'use client'

import { useState } from 'react'
import { Download } from 'lucide-react'
import { toast } from 'sonner'
import { exportAnalytics } from '@/lib/api'

interface Props {
  apiKey: string
  from: string
  to: string
}

export default function ExportButton({ apiKey, from, to }: Props) {
  const [exporting, setExporting] = useState(false)

  async function handleExport(format: 'csv' | 'json') {
    setExporting(true)
    try {
      const data = await exportAnalytics(apiKey, format, from, to)
      const content = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
      const mime = format === 'csv' ? 'text/csv' : 'application/json'
      const blob = new Blob([content], { type: mime })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `analytics-export.${format}`
      a.click()
      URL.revokeObjectURL(url)
      toast.success(`Exported as ${format.toUpperCase()}`)
    } catch (err) {
      console.error(err)
      toast.error('Export failed')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => handleExport('csv')}
        disabled={exporting}
        title="Export as CSV"
        className="flex items-center gap-1 rounded border border-gray-200 px-2.5 py-1.5 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-800"
      >
        <Download className="h-3 w-3" />
        CSV
      </button>
      <button
        onClick={() => handleExport('json')}
        disabled={exporting}
        title="Export as JSON"
        className="flex items-center gap-1 rounded border border-gray-200 px-2.5 py-1.5 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-800"
      >
        <Download className="h-3 w-3" />
        JSON
      </button>
    </div>
  )
}
