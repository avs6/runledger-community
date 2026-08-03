'use client'

import { useCallback, useRef, useState } from 'react'
import { Download } from 'lucide-react'

interface ChartExportButtonProps {
  chartRef: React.RefObject<HTMLDivElement | null>
  filename?: string
  data?: Record<string, unknown>[]
}

export default function ChartExportButton({ chartRef, filename = 'chart', data }: ChartExportButtonProps) {
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const exportSvg = useCallback(() => {
    const svg = chartRef.current?.querySelector('svg')
    if (!svg) return
    const clone = svg.cloneNode(true) as SVGElement
    const blob = new Blob([clone.outerHTML], { type: 'image/svg+xml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${filename}.svg`
    a.click()
    URL.revokeObjectURL(url)
    setOpen(false)
  }, [chartRef, filename])

  const exportCsv = useCallback(() => {
    if (!data?.length) return
    const headers = Object.keys(data[0])
    const rows = data.map(row => headers.map(h => JSON.stringify(row[h] ?? '')).join(','))
    const csv = [headers.join(','), ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${filename}.csv`
    a.click()
    URL.revokeObjectURL(url)
    setOpen(false)
  }, [data, filename])

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-500 transition-colors hover:border-blue-300 hover:text-blue-600 dark:border-slate-300 dark:bg-white dark:text-slate-500 dark:hover:border-blue-300 dark:hover:text-blue-600"
      >
        <Download className="h-3 w-3" />
        Export
      </button>
      {open && (
        <div className="absolute right-0 top-full z-20 mt-1 flex flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-300 dark:bg-white">
          <button
            type="button"
            onClick={exportSvg}
            className="px-4 py-2 text-left text-xs text-slate-700 hover:bg-blue-50 dark:hover:bg-blue-50"
          >
            SVG
          </button>
          {data && (
            <button
              type="button"
              onClick={exportCsv}
              className="px-4 py-2 text-left text-xs text-slate-700 hover:bg-blue-50 dark:hover:bg-blue-50"
            >
              CSV
            </button>
          )}
        </div>
      )}
    </div>
  )
}
