'use client'

import { useState } from 'react'
import { X } from 'lucide-react'
import type { Budget } from '@/types/api'
import { createBudget } from '@/lib/api'

interface Props {
  apiKey: string
  onCreated: (budget: Budget) => void
  onClose: () => void
}

const fieldCls =
  'w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder:text-gray-400 dark:placeholder:text-gray-500'

const labelCls = 'mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300'

export default function CreateBudgetModal({ apiKey, onCreated, onClose }: Props) {
  const [scopeType, setScopeType] = useState('workspace')
  const [scopeId, setScopeId] = useState('')
  const [periodType, setPeriodType] = useState('daily')
  const [limitUsd, setLimitUsd] = useState('')
  const [action, setAction] = useState('block')
  const [downgradeModel, setDowngradeModel] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const budget = await createBudget(apiKey, {
        scope_type: scopeType,
        scope_id: scopeType !== 'workspace' ? scopeId || null : null,
        period_type: periodType,
        limit_usd: parseFloat(limitUsd),
        action,
        downgrade_to_model: action === 'downgrade' ? downgradeModel || null : null,
      })
      onCreated(budget)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create budget')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-xl bg-white dark:bg-gray-900 shadow-xl border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">New Budget</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
          {error && (
            <p className="rounded bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 px-3 py-2 text-sm text-red-600 dark:text-red-400">{error}</p>
          )}

          <div>
            <label className={labelCls}>Scope type</label>
            <select value={scopeType} onChange={(e) => setScopeType(e.target.value)} className={fieldCls}>
              <option value="workspace">Workspace (all traffic)</option>
              <option value="end_user">End user</option>
              <option value="feature_tag">Feature tag</option>
            </select>
          </div>

          {scopeType !== 'workspace' && (
            <div>
              <label className={labelCls}>{scopeType === 'end_user' ? 'End user ID' : 'Feature tag'}</label>
              <input
                type="text"
                value={scopeId}
                onChange={(e) => setScopeId(e.target.value)}
                required
                placeholder={scopeType === 'end_user' ? 'u_12345' : 'support-chat'}
                className={fieldCls}
              />
            </div>
          )}

          <div>
            <label className={labelCls}>Period</label>
            <select value={periodType} onChange={(e) => setPeriodType(e.target.value)} className={fieldCls}>
              <option value="daily">Daily</option>
              <option value="monthly">Monthly</option>
              <option value="total">Total (lifetime)</option>
            </select>
          </div>

          <div>
            <label className={labelCls}>Limit (USD)</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={limitUsd}
              onChange={(e) => setLimitUsd(e.target.value)}
              required
              placeholder="10.00"
              className={fieldCls}
            />
          </div>

          <div>
            <label className={labelCls}>Action on breach</label>
            <select value={action} onChange={(e) => setAction(e.target.value)} className={fieldCls}>
              <option value="block">Block (return 402)</option>
              <option value="notify">Notify only (allow call)</option>
              <option value="downgrade">Downgrade model</option>
            </select>
          </div>

          {action === 'downgrade' && (
            <div>
              <label className={labelCls}>Downgrade to model</label>
              <input
                type="text"
                value={downgradeModel}
                onChange={(e) => setDowngradeModel(e.target.value)}
                required
                placeholder="gpt-4o-mini"
                className={fieldCls}
              />
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {submitting ? 'Creating…' : 'Create Budget'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
