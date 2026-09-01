'use client'

import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import type { Budget } from '@/types/api'
import { createBudget, getAccessGroups, listApiKeys } from '@/lib/api'

interface Props {
  apiKey: string
  onCreated: (budget: Budget) => void
  onClose: () => void
  initialScopeType?: Budget['scope_type']
  initialScopeId?: string
}

const fieldCls =
  'w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder:text-gray-500'

const labelCls = 'mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300'

interface ScopeOption {
  id: string
  label: string
}

export default function CreateBudgetModal({
  apiKey,
  onCreated,
  onClose,
  initialScopeType = 'workspace',
  initialScopeId = '',
}: Props) {
  const [scopeType, setScopeType] = useState<Budget['scope_type']>(initialScopeType)
  const [scopeId, setScopeId] = useState(initialScopeId)
  const [periodType, setPeriodType] = useState('daily')
  const [limitUsd, setLimitUsd] = useState('')
  const [action, setAction] = useState('block')
  const [downgradeModel, setDowngradeModel] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [accessGroups, setAccessGroups] = useState<ScopeOption[]>([])
  const [apiKeys, setApiKeys] = useState<ScopeOption[]>([])
  const [loadingEntities, setLoadingEntities] = useState(false)

  useEffect(() => {
    setScopeType(initialScopeType)
  }, [initialScopeType])

  useEffect(() => {
    setScopeId(initialScopeId)
  }, [initialScopeId])

  useEffect(() => {
    if (scopeType === 'access_group' && accessGroups.length === 0) {
      setLoadingEntities(true)
      getAccessGroups(apiKey)
        .then((resp) => {
          const items = Array.isArray(resp) ? resp : resp.items ?? []
          setAccessGroups(
            items.map((g: { id: string; name: string }) => ({ id: g.id, label: g.name }))
          )
        })
        .catch(() => {})
        .finally(() => setLoadingEntities(false))
    }
    if (scopeType === 'api_key' && apiKeys.length === 0) {
      setLoadingEntities(true)
      listApiKeys(apiKey)
        .then((keys) => {
          setApiKeys(
            keys.map((k: { id: string; name?: string | null; key_prefix?: string }) => ({
              id: k.id,
              label: k.name || k.key_prefix || k.id.slice(0, 8),
            }))
          )
        })
        .catch(() => {})
        .finally(() => setLoadingEntities(false))
    }
  }, [scopeType, apiKey, accessGroups.length, apiKeys.length])

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
        downgrade_to_model:
          action === 'downgrade' || action === 'fallback' ? downgradeModel || null : null,
      })
      onCreated(budget)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create budget')
    } finally {
      setSubmitting(false)
    }
  }

  const renderScopeIdInput = () => {
    if (scopeType === 'workspace') return null

    if (scopeType === 'access_group') {
      return (
        <div>
          <label className={labelCls}>Access group</label>
          {loadingEntities ? (
            <p className="text-sm text-gray-400">Loading access groups…</p>
          ) : accessGroups.length > 0 ? (
            <select
              value={scopeId}
              onChange={(e) => setScopeId(e.target.value)}
              required
              className={fieldCls}
            >
              <option value="">Select an access group</option>
              {accessGroups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.label}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              value={scopeId}
              onChange={(e) => setScopeId(e.target.value)}
              required
              placeholder="Access group UUID"
              className={fieldCls}
            />
          )}
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            This budget will apply to all traffic from members of this access group.
          </p>
        </div>
      )
    }

    if (scopeType === 'api_key') {
      return (
        <div>
          <label className={labelCls}>API key</label>
          {loadingEntities ? (
            <p className="text-sm text-gray-400">Loading API keys…</p>
          ) : apiKeys.length > 0 ? (
            <select
              value={scopeId}
              onChange={(e) => setScopeId(e.target.value)}
              required
              className={fieldCls}
            >
              <option value="">Select an API key</option>
              {apiKeys.map((k) => (
                <option key={k.id} value={k.id}>
                  {k.label}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              value={scopeId}
              onChange={(e) => setScopeId(e.target.value)}
              required
              placeholder="API key UUID"
              className={fieldCls}
            />
          )}
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            This budget will apply to all traffic authenticated by this API key.
          </p>
        </div>
      )
    }

    return (
      <div>
        <label className={labelCls}>
          {scopeType === 'end_user'
            ? 'End user ID'
            : scopeType === 'feature_tag'
              ? 'Feature tag'
              : scopeType === 'app'
                ? 'App / workflow key'
                : 'Provider profile ID'}
        </label>
        <input
          type="text"
          value={scopeId}
          onChange={(e) => setScopeId(e.target.value)}
          required
          placeholder={
            scopeType === 'end_user'
              ? 'u_12345'
              : scopeType === 'feature_tag'
                ? 'support-chat'
                : scopeType === 'app'
                  ? 'workflow:customer-support'
                  : 'UUID'
          }
          className={fieldCls}
        />
        {scopeType === 'provider_profile' && scopeId && (
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            This budget will be attached to the selected provider profile.
          </p>
        )}
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white shadow-xl dark:border-gray-700 dark:bg-gray-900">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-gray-700">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">New Budget</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
          {error && (
            <p className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
              {error}
            </p>
          )}

          <div>
            <label className={labelCls}>Scope type</label>
            <select
              value={scopeType}
              onChange={(e) => {
                setScopeType(e.target.value as Budget['scope_type'])
                setScopeId('')
              }}
              className={fieldCls}
            >
              <option value="workspace">Workspace (all traffic)</option>
              <option value="end_user">End user</option>
              <option value="feature_tag">Feature tag</option>
              <option value="app">App / workflow</option>
              <option value="access_group">Access group</option>
              <option value="api_key">API key</option>
              <option value="provider_profile">Provider profile</option>
            </select>
          </div>

          {renderScopeIdInput()}

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
              <option value="throttle">Throttle traffic</option>
              <option value="fallback">Fallback to model</option>
            </select>
          </div>

          {(action === 'downgrade' || action === 'fallback') && (
            <div>
              <label className={labelCls}>
                {action === 'fallback' ? 'Fallback to model' : 'Downgrade to model'}
              </label>
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
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {submitting ? 'Creating...' : 'Create Budget'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
