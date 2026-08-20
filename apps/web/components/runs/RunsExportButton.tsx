'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Download, FileText, ChevronDown } from 'lucide-react'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export default function RunsExportButton() {
  const { data: session } = useSession()
  const params = useSearchParams()
  const [open, setOpen] = useState(false)

  async function handleCsvExport() {
    const apiKey = (session as { apiKey?: string })?.apiKey
    if (!apiKey) return
    setOpen(false)

    const exportParams = new URLSearchParams()
    for (const key of ['status', 'feature_tag', 'end_user_id', 'search', 'from', 'to', 'model', 'min_cost', 'max_cost', 'access_group_id']) {
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
    a.download = `runs-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function handlePdfExport() {
    const apiKey = (session as { apiKey?: string })?.apiKey
    if (!apiKey) return
    setOpen(false)

    const exportParams = new URLSearchParams()
    for (const key of ['status', 'feature_tag', 'end_user_id', 'search', 'from', 'to', 'model', 'min_cost', 'max_cost', 'access_group_id']) {
      const v = params.get(key)
      if (v) exportParams.set(key, v)
    }

    const res = await fetch(`${BASE_URL}/runs/export?${exportParams.toString()}`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    })
    if (!res.ok) return

    const csvText = await res.text()
    const lines = csvText.trim().split('\n')
    if (lines.length < 2) return

    const headers = lines[0].split(',').map(h => h.trim())
    const rows = lines.slice(1).map(line => {
      // Handle quoted fields with commas inside
      const result: string[] = []
      let cur = ''
      let inQuotes = false
      for (let i = 0; i < line.length; i++) {
        if (line[i] === '"') { inQuotes = !inQuotes }
        else if (line[i] === ',' && !inQuotes) { result.push(cur); cur = '' }
        else { cur += line[i] }
      }
      result.push(cur)
      return result
    })

    const filterParts: string[] = []
    for (const [key, label] of [
      ['status', 'Status'], ['model', 'Model'],
      ['feature_tag', 'Tag'], ['end_user_id', 'User'],
      ['search', 'Run ID'], ['min_cost', 'Min $'], ['max_cost', 'Max $'], ['access_group_id', 'Access group'],
    ] as [string, string][]) {
      const v = params.get(key)
      if (v) filterParts.push(`${label}: ${v}`)
    }
    const filterSummary = filterParts.length ? filterParts.join(' · ') : 'All runs'

    // Dynamically import jsPDF to avoid SSR issues
    const { default: jsPDF } = await import('jspdf')
    const { default: autoTable } = await import('jspdf-autotable')

    const doc = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' })

    doc.setFontSize(16)
    doc.setFont('helvetica', 'bold')
    doc.text('RunLedger — Agent Runs', 40, 40)

    doc.setFontSize(9)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(100)
    doc.text(`Exported: ${new Date().toLocaleString()}   ·   Filters: ${filterSummary}`, 40, 58)
    doc.setTextColor(0)

    autoTable(doc, {
      head: [headers],
      body: rows,
      startY: 72,
      styles: { fontSize: 8, cellPadding: 4 },
      headStyles: { fillColor: [37, 99, 235], textColor: 255, fontStyle: 'bold' },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      margin: { left: 40, right: 40 },
    })

    doc.save(`runs-${new Date().toISOString().slice(0, 10)}.pdf`)
  }

  return (
    <div className="relative">
      <div className="flex h-8 overflow-hidden rounded-lg border border-input bg-background shadow-sm">
        <button
          onClick={handleCsvExport}
          className="flex items-center gap-1.5 px-3 text-sm font-medium text-foreground hover:bg-accent transition-colors"
        >
          <Download className="h-3.5 w-3.5" />
          Export CSV
        </button>
        <div className="w-px bg-border" />
        <button
          onClick={() => setOpen(o => !o)}
          className="flex items-center px-2 hover:bg-accent transition-colors"
          aria-label="More export options"
        >
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        </button>
      </div>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full z-20 mt-1 w-44 overflow-hidden rounded-xl border border-border bg-popover shadow-lg">
            <button
              onClick={handleCsvExport}
              className="flex w-full items-center gap-2.5 px-3 py-2.5 text-sm text-foreground hover:bg-accent transition-colors"
            >
              <Download className="h-4 w-4 text-muted-foreground" />
              Download CSV
            </button>
            <div className="mx-3 border-t border-border" />
            <button
              onClick={handlePdfExport}
              className="flex w-full items-center gap-2.5 px-3 py-2.5 text-sm text-foreground hover:bg-accent transition-colors"
            >
              <FileText className="h-4 w-4 text-muted-foreground" />
              Download PDF
            </button>
          </div>
        </>
      )}
    </div>
  )
}
