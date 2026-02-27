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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-base font-semibold">New Budget</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
          {error && (
            <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
          )}

          {/* Scope type */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Scope type
            </label>
            <select
              value={scopeType}
              onChange={(e) => setScopeType(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="workspace">Workspace (all traffic)</option>
              <option value="end_user">End user</option>
              <option value="feature_tag">Feature tag</option>
            </select>
          </div>

          {/* Scope ID */}
          {scopeType !== 'workspace' && (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                {scopeType === 'end_user' ? 'End user ID' : 'Feature tag'}
              </label>
              <input
                type="text"
                value={scopeId}
                onChange={(e) => setScopeId(e.target.value)}
                required
                placeholder={scopeType === 'end_user' ? 'u_12345' : 'support-chat'}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          )}

          {/* Period */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Period</label>
            <select
              value={periodType}
              onChange={(e) => setPeriodType(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="daily">Daily</option>
              <option value="monthly">Monthly</option>
              <option value="total">Total (lifetime)</option>
            </select>
          </div>

          {/* Limit */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Limit (USD)
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={limitUsd}
              onChange={(e) => setLimitUsd(e.target.value)}
              required
              placeholder="10.00"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Action */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Action on breach
            </label>
            <select
              value={action}
              onChange={(e) => setAction(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="block">Block (return 402)</option>
              <option value="notify">Notify only (allow call)</option>
              <option value="downgrade">Downgrade model</option>
            </select>
          </div>

          {/* Downgrade model */}
          {action === 'downgrade' && (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Downgrade to model
              </label>
              <input
                type="text"
                value={downgradeModel}
                onChange={(e) => setDowngradeModel(e.target.value)}
                required
                placeholder="gpt-4o-mini"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
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
