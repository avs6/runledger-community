import type { ReconciliationResult } from '@/types/api'
import { CheckCircle, XCircle } from 'lucide-react'

interface Props {
  result: ReconciliationResult
}

export default function ReconciliationPanel({ result }: Props) {
  const isPassing = result.status === 'pass'

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center gap-2">
        {isPassing ? (
          <CheckCircle className="h-5 w-5 text-green-500" />
        ) : (
          <XCircle className="h-5 w-5 text-red-500" />
        )}
        <span
          className={`text-base font-semibold ${isPassing ? 'text-green-700' : 'text-red-700'}`}
        >
          Reconciliation: {isPassing ? 'PASS' : 'FAIL'}
        </span>
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-gray-500">Provider Calls Sum</dt>
          <dd className="font-mono font-medium text-gray-900">
            ${parseFloat(result.provider_calls_sum).toFixed(6)}
          </dd>
        </div>
        <div>
          <dt className="text-gray-500">Usage Daily Sum</dt>
          <dd className="font-mono font-medium text-gray-900">
            ${parseFloat(result.usage_daily_sum).toFixed(6)}
          </dd>
        </div>
        <div>
          <dt className="text-gray-500">Delta %</dt>
          <dd
            className={`font-mono font-medium ${parseFloat(result.delta_pct) > 0.01 ? 'text-red-600' : 'text-gray-900'}`}
          >
            {parseFloat(result.delta_pct).toFixed(4)}%
          </dd>
        </div>
        <div>
          <dt className="text-gray-500">Orphaned Calls</dt>
          <dd
            className={`font-medium ${result.orphaned_calls > 0 ? 'text-red-600' : 'text-gray-900'}`}
          >
            {result.orphaned_calls}
          </dd>
        </div>
        <div>
          <dt className="text-gray-500">Duplicate Groups</dt>
          <dd
            className={`font-medium ${result.duplicate_calls > 0 ? 'text-red-600' : 'text-gray-900'}`}
          >
            {result.duplicate_calls}
          </dd>
        </div>
      </dl>

      {result.issues.length > 0 && (
        <div className="mt-4 rounded-md bg-red-50 p-3">
          <p className="mb-1 text-xs font-medium text-red-700">Issues</p>
          <ul className="space-y-1">
            {result.issues.map((issue, i) => (
              <li key={i} className="text-xs text-red-600">
                • {issue}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
