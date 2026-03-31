'use client'

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  FileUp, RefreshCw, Trash2, ExternalLink, AlertTriangle,
  CheckCircle2, Clock, FileX, Download, ChevronDown, ChevronRight,
} from 'lucide-react'
import {
  listInvoices, uploadInvoice, reconcileInvoice, deleteInvoice,
  getInvoiceSummary, listInvoiceLines, disputeInvoiceLine,
} from '@/lib/api'
import type { InvoiceResponse, ReconciliationSummary, InvoiceLineResponse } from '@/types/api'

// ── Helpers ────────────────────────────────────────────────────────────────────

const PROVIDERS = ['openai', 'anthropic', 'google', 'other']

const STATUS_STYLES: Record<string, string> = {
  imported: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  reconciled: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300',
  flagged: 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300',
}

const MATCH_STYLES: Record<string, string> = {
  exact: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300',
  fuzzy: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  unmatched: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
  disputed: 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300',
}

function fmt(amount: string | number | null | undefined): string {
  if (amount == null) return '—'
  const n = Number(amount)
  return isNaN(n) ? '—' : `$${n.toFixed(4)}`
}

function fmtPct(pct: string | null | undefined): string {
  if (pct == null) return '—'
  const n = Number(pct)
  return isNaN(n) ? '—' : `${n > 0 ? '+' : ''}${n.toFixed(2)}%`
}

const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500'
const labelCls = 'block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1'

function SkeletonRows({ cols, rows = 3 }: { cols: number; rows?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i}>
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} className="px-4 py-3">
              <div className="h-4 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

// ── Upload form ────────────────────────────────────────────────────────────────

function UploadForm({ apiKey, onUploaded }: { apiKey: string; onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  const [provider, setProvider] = useState('')
  const [uploading, setUploading] = useState(false)
  const [showForm, setShowForm] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file || !periodStart || !periodEnd) return
    setUploading(true)
    try {
      await uploadInvoice(apiKey, file, periodStart, periodEnd, provider || undefined)
      toast.success(`Uploaded ${file.name} — ${(file.size / 1024).toFixed(0)} KB`)
      setFile(null); setPeriodStart(''); setPeriodEnd(''); setProvider('')
      setShowForm(false)
      onUploaded()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false) }
  }

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Provider Invoices</h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Upload OpenAI, Anthropic, or Google usage exports (CSV or JSON)
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700 transition-colors"
        >
          <FileUp className="h-3.5 w-3.5" />{showForm ? 'Cancel' : 'Upload Invoice'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mt-4 space-y-3 border-t border-slate-100 dark:border-slate-800 pt-4">
          <div>
            <label className={labelCls}>Invoice file (CSV or JSON)</label>
            <input
              type="file"
              accept=".csv,.json,text/csv,application/json"
              required
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="w-full cursor-pointer rounded-lg border border-dashed border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/50 px-3 py-2 text-sm text-slate-600 dark:text-slate-300 file:mr-3 file:rounded file:border-0 file:bg-violet-600 file:px-2 file:py-1 file:text-xs file:font-medium file:text-white hover:file:bg-violet-700"
            />
            {file && (
              <p className="mt-1 text-xs text-slate-500">{file.name} — {(file.size / 1024).toFixed(0)} KB</p>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={labelCls}>Period start</label>
              <input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} required className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Period end</label>
              <input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} required className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Provider (optional — auto-detected)</label>
              <select value={provider} onChange={(e) => setProvider(e.target.value)} className={inputCls}>
                <option value="">Auto-detect</option>
                {PROVIDERS.map((p) => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={uploading || !file || !periodStart || !periodEnd}
            className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50 transition-colors"
          >
            {uploading && <RefreshCw className="h-4 w-4 animate-spin" />}
            {uploading ? 'Uploading…' : 'Upload & Parse'}
          </button>
        </form>
      )}
    </div>
  )
}

// ── Summary card ───────────────────────────────────────────────────────────────

function SummaryPanel({
  summary,
  invoiceId,
  apiKey,
}: {
  summary: ReconciliationSummary
  invoiceId: string
  apiKey: string
}) {
  const matched = summary.matched_exact + summary.matched_fuzzy
  const matchedPct = Number(summary.matched_pct)

  const barColor =
    matchedPct >= 90 ? 'bg-emerald-500' : matchedPct >= 70 ? 'bg-amber-500' : 'bg-red-500'

  return (
    <div className="space-y-4">
      {/* KPI strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Invoice Total', value: fmt(summary.total_amount) },
          { label: 'RunLedger Total', value: fmt(summary.runledger_total) },
          { label: 'Delta', value: fmtPct(summary.delta_pct), sub: fmt(summary.delta_amount) },
          { label: 'Matched', value: `${matchedPct.toFixed(1)}%`, sub: `${matched} / ${summary.line_count} lines` },
        ].map((k) => (
          <div key={k.label} className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 px-4 py-3">
            <p className="text-xs text-slate-500 dark:text-slate-400">{k.label}</p>
            <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{k.value}</p>
            {k.sub && <p className="text-xs text-slate-400 dark:text-slate-500">{k.sub}</p>}
          </div>
        ))}
      </div>

      {/* Progress bar */}
      <div>
        <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
          <span>{matched} matched ({summary.matched_exact} exact · {summary.matched_fuzzy} fuzzy)</span>
          <span>{summary.unmatched} unmatched · {summary.disputed} disputed</span>
        </div>
        <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700">
          <div
            className={`h-2 rounded-full transition-all ${barColor}`}
            style={{ width: `${Math.min(matchedPct, 100)}%` }}
          />
        </div>
      </div>

      {/* Token mismatch buckets */}
      {summary.token_mismatch_buckets.some((b) => b.count > 0) && (
        <div>
          <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">Token mismatch (fuzzy matches)</p>
          <div className="flex gap-3">
            {summary.token_mismatch_buckets.map((b) => (
              <div key={b.bucket} className="flex-1 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-center">
                <p className="text-xs text-slate-500 dark:text-slate-400">{b.bucket}</p>
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{b.count}</p>
                <p className="text-xs text-slate-400">{fmt(b.amount)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Export link */}
      <div className="flex justify-end">
        <a
          href={`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/invoices/${invoiceId}/export`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs text-violet-600 dark:text-violet-400 hover:underline"
        >
          <Download className="h-3.5 w-3.5" />Export dispute package
        </a>
      </div>
    </div>
  )
}

// ── Lines table ────────────────────────────────────────────────────────────────

function LinesTable({
  lines,
  invoiceId,
  apiKey,
  onDisputed,
}: {
  lines: InvoiceLineResponse[]
  invoiceId: string
  apiKey: string
  onDisputed: (lineId: string, note: string) => void
}) {
  const [disputing, setDisputing] = useState<string | null>(null)
  const [disputeNote, setDisputeNote] = useState('')

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
            <th className="pb-2 text-left font-medium px-2">Model</th>
            <th className="pb-2 text-left font-medium px-2">Timestamp</th>
            <th className="pb-2 text-right font-medium px-2">Input Tok</th>
            <th className="pb-2 text-right font-medium px-2">Output Tok</th>
            <th className="pb-2 text-right font-medium px-2">Amount</th>
            <th className="pb-2 text-right font-medium px-2">Δ Cost</th>
            <th className="pb-2 text-left font-medium px-2">Match</th>
            <th className="pb-2 px-2"></th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => (
            <>
              <tr key={line.id} className="border-b border-slate-50 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/30">
                <td className="py-2 px-2 font-mono text-xs text-slate-700 dark:text-slate-200">{line.model ?? '—'}</td>
                <td className="py-2 px-2 text-xs text-slate-500 dark:text-slate-400">
                  {line.occurred_at ? new Date(line.occurred_at).toLocaleString() : '—'}
                </td>
                <td className="py-2 px-2 text-right tabular-nums text-slate-600 dark:text-slate-300">
                  {line.input_tokens?.toLocaleString() ?? '—'}
                </td>
                <td className="py-2 px-2 text-right tabular-nums text-slate-600 dark:text-slate-300">
                  {line.output_tokens?.toLocaleString() ?? '—'}
                </td>
                <td className="py-2 px-2 text-right tabular-nums font-medium text-slate-800 dark:text-slate-100">
                  {fmt(line.amount)}
                </td>
                <td className={`py-2 px-2 text-right tabular-nums text-xs ${line.cost_delta != null && Number(line.cost_delta) !== 0 ? Number(line.cost_delta) > 0 ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400'}`}>
                  {line.cost_delta != null ? fmt(line.cost_delta) : '—'}
                </td>
                <td className="py-2 px-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${MATCH_STYLES[line.match_status] ?? ''}`}>
                    {line.match_status}
                  </span>
                </td>
                <td className="py-2 px-2">
                  {line.match_status !== 'disputed' && (
                    <button
                      onClick={() => setDisputing(disputing === line.id ? null : line.id)}
                      className="text-xs text-slate-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
                    >
                      <AlertTriangle className="h-3.5 w-3.5" />
                    </button>
                  )}
                  {line.dispute_note && (
                    <span className="ml-1 text-xs text-amber-600 dark:text-amber-400 italic">{line.dispute_note.slice(0, 30)}</span>
                  )}
                </td>
              </tr>
              {disputing === line.id && (
                <tr key={`dispute-${line.id}`}>
                  <td colSpan={8} className="pb-3 px-2">
                    <div className="flex gap-2 items-center">
                      <input
                        value={disputeNote}
                        onChange={(e) => setDisputeNote(e.target.value)}
                        placeholder="Dispute reason…"
                        className="flex-1 rounded border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 px-2 py-1 text-xs text-slate-800 dark:text-slate-100 focus:outline-none"
                      />
                      <button
                        disabled={!disputeNote.trim()}
                        onClick={async () => {
                          await onDisputed(line.id, disputeNote.trim())
                          setDisputing(null); setDisputeNote('')
                        }}
                        className="rounded px-2 py-1 text-xs font-medium bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-50 transition-colors"
                      >
                        Flag
                      </button>
                      <button onClick={() => setDisputing(null)} className="text-xs text-slate-400 hover:text-slate-600">Cancel</button>
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Invoice row with expand ────────────────────────────────────────────────────

function InvoiceRow({
  invoice, apiKey, onDelete,
}: {
  invoice: InvoiceResponse
  apiKey: string
  onDelete: (id: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [summary, setSummary] = useState<ReconciliationSummary | null>(null)
  const [lines, setLines] = useState<InvoiceLineResponse[]>([])
  const [lineFilter, setLineFilter] = useState<string>('')
  const [reconciling, setReconciling] = useState(false)
  const [loadingLines, setLoadingLines] = useState(false)

  async function loadDetail() {
    if (!apiKey) return
    try {
      const [s, l] = await Promise.all([
        getInvoiceSummary(apiKey, invoice.id),
        listInvoiceLines(apiKey, invoice.id, { limit: 200 }),
      ])
      setSummary(s)
      setLines(l.items)
    } catch { toast.error('Failed to load invoice detail') }
  }

  async function handleExpand() {
    const next = !expanded
    setExpanded(next)
    if (next && summary === null) await loadDetail()
  }

  async function handleReconcile() {
    setReconciling(true)
    try {
      const result = await reconcileInvoice(apiKey, invoice.id)
      toast.success(`Reconciled: ${result.matched_exact ?? 0} exact + ${result.matched_fuzzy ?? 0} fuzzy, ${result.unmatched ?? 0} unmatched`)
      toast.info('Reconciliation summary emailed to workspace admins')
      await loadDetail()
    } catch { toast.error('Reconciliation failed') } finally { setReconciling(false) }
  }

  async function handleDispute(lineId: string, note: string) {
    try {
      await disputeInvoiceLine(apiKey, invoice.id, lineId, note)
      toast.success('Line flagged as disputed')
      setLines((prev) => prev.map((l) => l.id === lineId ? { ...l, match_status: 'disputed', dispute_note: note } : l))
    } catch { toast.error('Failed to dispute line') }
  }

  const filteredLines = lineFilter ? lines.filter((l) => l.match_status === lineFilter) : lines

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 overflow-hidden">
      {/* Header row */}
      <div className="flex items-center gap-3 p-4">
        <button onClick={handleExpand} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-slate-800 dark:text-slate-100 capitalize">{invoice.provider}</span>
            <span className="text-xs text-slate-400 dark:text-slate-500">
              {invoice.period_start} → {invoice.period_end}
            </span>
            {invoice.filename && (
              <span className="text-xs text-slate-400 dark:text-slate-500 truncate">{invoice.filename}</span>
            )}
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[invoice.status] ?? ''}`}>
              {invoice.status}
            </span>
          </div>
          <div className="mt-0.5 flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
            <span>Total: <strong className="text-slate-700 dark:text-slate-200">{fmt(invoice.total_amount)}</strong></span>
            <span>{invoice.line_count} lines</span>
            {invoice.matched_count > 0 && (
              <span className="text-emerald-600 dark:text-emerald-400">
                {invoice.matched_count} matched
              </span>
            )}
            {invoice.unmatched_amount && Number(invoice.unmatched_amount) > 0 && (
              <span className="text-red-600 dark:text-red-400">
                {fmt(invoice.unmatched_amount)} unmatched
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleReconcile}
            disabled={reconciling}
            className="flex items-center gap-1.5 rounded-lg border border-violet-200 dark:border-violet-700 px-2.5 py-1.5 text-xs font-medium text-violet-600 dark:text-violet-400 hover:bg-violet-50 dark:hover:bg-violet-900/30 disabled:opacity-50 transition-colors"
          >
            {reconciling ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Reconcile
          </button>
          <button
            onClick={() => onDelete(invoice.id)}
            className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-slate-100 dark:border-slate-800 p-4 space-y-4">
          {summary ? (
            <SummaryPanel summary={summary} invoiceId={invoice.id} apiKey={apiKey} />
          ) : (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <RefreshCw className="h-4 w-4 animate-spin" />Loading…
            </div>
          )}

          {/* Lines */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <p className="text-xs font-medium text-slate-600 dark:text-slate-400">Invoice Lines</p>
              <div className="flex gap-1">
                {['', 'unmatched', 'fuzzy', 'exact', 'disputed'].map((s) => (
                  <button
                    key={s}
                    onClick={() => setLineFilter(s)}
                    className={`rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors ${lineFilter === s ? 'bg-violet-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'}`}
                  >
                    {s || 'all'}
                  </button>
                ))}
              </div>
            </div>
            {filteredLines.length > 0 ? (
              <LinesTable
                lines={filteredLines}
                invoiceId={invoice.id}
                apiKey={apiKey}
                onDisputed={handleDispute}
              />
            ) : (
              <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-4">
                {lines.length === 0
                  ? 'No lines loaded — click Reconcile first.'
                  : `No lines with status "${lineFilter}".`}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function InvoicesPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  const [invoices, setInvoices] = useState<InvoiceResponse[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const data = await listInvoices(apiKey)
      setInvoices(data.items)
    } catch { toast.error('Failed to load invoices') } finally { setLoading(false) }
  }, [apiKey])

  useEffect(() => { refresh() }, [refresh])

  async function handleDelete(id: string) {
    try {
      await deleteInvoice(apiKey, id)
      toast.success('Invoice deleted')
      setInvoices((prev) => prev.filter((i) => i.id !== id))
    } catch { toast.error('Failed to delete invoice') }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Invoice Reconciliation</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Upload provider usage exports and reconcile them against your tracked provider calls.
        </p>
      </div>

      <UploadForm apiKey={apiKey} onUploaded={refresh} />

      {loading ? (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-8">
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
            ))}
          </div>
        </div>
      ) : invoices.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 p-12 text-center">
          <FileX className="mx-auto h-10 w-10 text-slate-300 dark:text-slate-600 mb-3" />
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400">No invoices yet</p>
          <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
            Upload a provider CSV or JSON export to get started.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {invoices.map((invoice) => (
            <InvoiceRow
              key={invoice.id}
              invoice={invoice}
              apiKey={apiKey}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  )
}
