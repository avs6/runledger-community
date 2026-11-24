import type { LedgerVerifyResult } from '@/types/api'

const STYLES: Record<LedgerVerifyResult['status'], string> = {
  ok: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  late_data: 'bg-sky-100 text-sky-700 dark:bg-sky-900/60 dark:text-sky-300',
  incomplete: 'bg-amber-100 text-amber-700 dark:bg-amber-900/60 dark:text-amber-300',
  unsealed_drift: 'bg-amber-100 text-amber-700 dark:bg-amber-900/60 dark:text-amber-300',
  tampered: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  not_found: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
}

const LABELS: Record<LedgerVerifyResult['status'], string> = {
  ok: 'ok',
  late_data: 'ok · late data',
  incomplete: 'rows missing',
  unsealed_drift: 'legacy · drift',
  tampered: 'tampered',
  not_found: 'not found',
}

/** One-line explanation of a ledger verification (review cd:M-02). */
export function ledgerVerifySummary(r: LedgerVerifyResult): string {
  const parts: string[] = []
  if (r.late_enriched_rows) parts.push(`${r.late_enriched_rows} call(s) priced after sealing`)
  if (r.late_arrival_rows) parts.push(`${r.late_arrival_rows} call(s) recorded after sealing`)
  if (r.modified_rows) parts.push(`${r.modified_rows} sealed call(s) changed`)
  if (r.missing_rows) parts.push(`${r.missing_rows} sealed call(s) no longer exist (retention?)`)
  if (r.anchor_ok === true) parts.push('matches the off-box anchor')
  else if (r.anchored === false && r.sealed) parts.push('not anchored off-box yet')
  if (r.detail) parts.push(r.detail)
  return parts.join('; ') || (r.status === 'ok' ? 'Matches the sealed manifest' : r.status)
}

export function LedgerVerifyBadge({ result }: { result: LedgerVerifyResult }) {
  const summary = ledgerVerifySummary(result)
  return (
    <span title={summary} className={`rounded px-2 py-0.5 text-xs ${STYLES[result.status] ?? STYLES.not_found}`}>
      {LABELS[result.status] ?? result.status}
      <span className="sr-only">: {summary}</span>
    </span>
  )
}
