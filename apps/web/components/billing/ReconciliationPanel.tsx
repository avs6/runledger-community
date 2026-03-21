import type { ReconciliationResult } from '@/types/api'
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react'

interface Props {
  result: ReconciliationResult
}

export default function ReconciliationPanel({ result }: Props) {
  const isPass    = result.status === 'pass'
  const isWarning = result.status === 'warning'
  const isFail    = result.status === 'fail'

  const statusIcon = isPass
    ? <CheckCircle className="h-5 w-5 text-emerald-500" />
    : isWarning
    ? <AlertTriangle className="h-5 w-5 text-amber-500" />
    : <XCircle className="h-5 w-5 text-red-500" />

  const statusLabel = isPass ? 'PASS' : isWarning ? 'WARNING' : 'FAIL'
  const statusColor = isPass
    ? 'text-emerald-700 dark:text-emerald-400'
    : isWarning
    ? 'text-amber-700 dark:text-amber-400'
    : 'text-red-700 dark:text-red-400'

  return (
    <div className="rounded-xl border border-slate-200/80 bg-white p-5 dark:border-slate-700/60 dark:bg-slate-900">
      <div className="mb-4 flex items-center gap-2">
        {statusIcon}
        <span className={`text-base font-semibold ${statusColor}`}>
          Reconciliation: {statusLabel}
        </span>
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-slate-500 dark:text-slate-400">Provider Calls Sum</dt>
          <dd className="font-mono font-medium text-slate-900 dark:text-slate-100">
            ${parseFloat(result.provider_calls_sum).toFixed(6)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 dark:text-slate-400">Usage Daily Sum</dt>
          <dd className="font-mono font-medium text-slate-900 dark:text-slate-100">
            ${parseFloat(result.usage_daily_sum).toFixed(6)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 dark:text-slate-400">Delta %</dt>
          <dd className={`font-mono font-medium ${parseFloat(result.delta_pct) > 0.01 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-slate-100'}`}>
            {parseFloat(result.delta_pct).toFixed(4)}%
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 dark:text-slate-400">Orphaned Calls</dt>
          <dd className={`font-medium ${result.orphaned_calls > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-slate-100'}`}>
            {result.orphaned_calls}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 dark:text-slate-400">Duplicate Groups</dt>
          <dd className={`font-medium ${result.duplicate_calls > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-900 dark:text-slate-100'}`}>
            {result.duplicate_calls}
          </dd>
        </div>
      </dl>

      {result.issues.length > 0 && (
        <div className="mt-4 rounded-lg bg-red-50 p-3 dark:bg-red-950/30">
          <p className="mb-1 text-xs font-semibold text-red-700 dark:text-red-400">Issues</p>
          <ul className="space-y-1">
            {result.issues.map((issue, i) => (
              <li key={i} className="text-xs text-red-600 dark:text-red-400">• {issue}</li>
            ))}
          </ul>
        </div>
      )}

      {result.warnings && result.warnings.length > 0 && (
        <div className="mt-3 rounded-lg bg-amber-50 p-3 dark:bg-amber-950/30">
          <p className="mb-1 text-xs font-semibold text-amber-700 dark:text-amber-400">Warnings</p>
          <ul className="space-y-1">
            {result.warnings.map((w, i) => (
              <li key={i} className="text-xs text-amber-600 dark:text-amber-400">• {w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
