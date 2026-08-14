'use client'

import Link from 'next/link'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { ChevronLeft } from 'lucide-react'
import { createBudgetOverride, revokeBudgetOverride, updateBudget } from '@/lib/api'
import type { Breach, Budget, BudgetOverride } from '@/types/api'
import BreachHistoryTable from './BreachHistoryTable'

interface Props {
  apiKey: string
  initialBudget: Budget
  initialBreaches: Breach[]
  initialOverrides: BudgetOverride[]
}

function formatMoney(value: string | number) {
  return `$${Number(value).toFixed(2)}`
}

function getScopeLink(budget: Budget): { href: string; label: string } | null {
  if (budget.scope_type === 'provider_profile') {
    return { href: '/provider-profiles', label: 'Open provider profiles' }
  }
  if (budget.scope_type === 'api_key') {
    return { href: '/api-keys', label: 'Open API keys' }
  }
  if (budget.scope_type === 'access_group') {
    return { href: '/access-groups', label: 'Open access groups' }
  }
  return null
}

export default function BudgetDetailClient({
  apiKey,
  initialBudget,
  initialBreaches,
  initialOverrides,
}: Props) {
  const router = useRouter()
  const [budget, setBudget] = useState(initialBudget)
  const scopeLink = getScopeLink(budget)
  const [breaches] = useState(initialBreaches)
  const [overrides, setOverrides] = useState(initialOverrides)
  const [saving, setSaving] = useState(false)
  const [overrideSaving, setOverrideSaving] = useState(false)
  const [form, setForm] = useState({
    scope_type: initialBudget.scope_type,
    scope_id: initialBudget.scope_id ?? '',
    period_type: initialBudget.period_type,
    limit_usd: initialBudget.limit_usd,
    action: initialBudget.action,
    downgrade_to_model: initialBudget.downgrade_to_model ?? '',
    is_active: initialBudget.is_active,
  })
  const [overrideForm, setOverrideForm] = useState({
    override_limit_usd: '',
    starts_at: '',
    expires_at: '',
    reason: '',
    require_approval: false,
  })

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const updated = await updateBudget(apiKey, budget.id, {
        scope_type: form.scope_type,
        scope_id: form.scope_type === 'workspace' ? null : form.scope_id || null,
        period_type: form.period_type,
        limit_usd: parseFloat(form.limit_usd),
        action: form.action,
        downgrade_to_model:
          form.action === 'downgrade' || form.action === 'fallback'
            ? form.downgrade_to_model || null
            : null,
        is_active: form.is_active,
      })
      setBudget(updated)
      setForm({
        scope_type: updated.scope_type,
        scope_id: updated.scope_id ?? '',
        period_type: updated.period_type,
        limit_usd: updated.limit_usd,
        action: updated.action,
        downgrade_to_model: updated.downgrade_to_model ?? '',
        is_active: updated.is_active,
      })
      toast.success('Budget updated')
      router.refresh()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update budget')
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  async function handleCreateOverride(e: React.FormEvent) {
    e.preventDefault()
    setOverrideSaving(true)
    try {
      const created = await createBudgetOverride(apiKey, budget.id, {
        override_limit_usd: parseFloat(overrideForm.override_limit_usd),
        starts_at: new Date(overrideForm.starts_at).toISOString(),
        expires_at: new Date(overrideForm.expires_at).toISOString(),
        reason: overrideForm.reason || undefined,
        require_approval: overrideForm.require_approval,
      })
      setOverrides((current) => [created, ...current])
      setOverrideForm({
        override_limit_usd: '',
        starts_at: '',
        expires_at: '',
        reason: '',
        require_approval: false,
      })
      toast.success(
        overrideForm.require_approval ? 'Override sent for approval' : 'Override created'
      )
      router.refresh()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create override')
      console.error(err)
    } finally {
      setOverrideSaving(false)
    }
  }

  async function handleRevokeOverride(overrideId: string) {
    try {
      const updated = await revokeBudgetOverride(apiKey, budget.id, overrideId)
      setOverrides((current) => current.map((item) => (item.id === overrideId ? updated : item)))
      toast.success('Override revoked')
      router.refresh()
    } catch (err) {
      toast.error('Failed to revoke override')
      console.error(err)
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Link
          href="/budgets"
          className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
        >
          <ChevronLeft className="h-4 w-4" />
          Budgets
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-slate-950 dark:text-slate-100">
              Budget Detail
            </h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Budget {budget.id}</p>
            {budget.scope_display_name && (
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                Related scope: {budget.scope_display_name}
              </p>
            )}
            {scopeLink && (
              <Link
                href={scopeLink.href}
                className="mt-2 inline-flex text-sm font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-300"
              >
                {scopeLink.label}
              </Link>
            )}
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <p className="text-xs uppercase tracking-wide text-slate-500">Live Spend</p>
            <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-slate-100">
              {formatMoney(budget.current_spend_usd)}
            </p>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {Number(budget.pct_used).toFixed(0)}% of {formatMoney(budget.limit_usd)}
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <form
          onSubmit={handleSave}
          className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950"
        >
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Policy</p>
            <h2 className="mt-2 text-lg font-semibold text-slate-950 dark:text-slate-100">
              Edit budget rule
            </h2>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                Scope type
              </span>
              <select
                value={form.scope_type}
                onChange={(e) =>
                  setForm({ ...form, scope_type: e.target.value as Budget['scope_type'] })
                }
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              >
                <option value="workspace">Workspace</option>
                <option value="end_user">End user</option>
                <option value="feature_tag">Feature tag</option>
                <option value="app">App / workflow</option>
                <option value="access_group">Access group</option>
                <option value="api_key">API key</option>
                <option value="provider_profile">Provider profile</option>
              </select>
            </label>

            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                Scope value
              </span>
              <input
                value={form.scope_id}
                onChange={(e) => setForm({ ...form, scope_id: e.target.value })}
                disabled={form.scope_type === 'workspace'}
                placeholder={
                  form.scope_type === 'workspace'
                    ? 'All workspace traffic'
                    : form.scope_type === 'feature_tag'
                      ? 'support-chat'
                      : form.scope_type === 'app'
                        ? 'workflow:customer-support'
                        : 'UUID or scope key'
                }
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm disabled:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-white dark:disabled:bg-slate-800"
              />
            </label>

            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                Period
              </span>
              <select
                value={form.period_type}
                onChange={(e) =>
                  setForm({ ...form, period_type: e.target.value as Budget['period_type'] })
                }
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              >
                <option value="daily">Daily</option>
                <option value="monthly">Monthly</option>
                <option value="total">Total</option>
              </select>
            </label>

            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                Limit (USD)
              </span>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={form.limit_usd}
                onChange={(e) => setForm({ ...form, limit_usd: e.target.value })}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              />
            </label>

            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                Breach action
              </span>
              <select
                value={form.action}
                onChange={(e) => setForm({ ...form, action: e.target.value as Budget['action'] })}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              >
                <option value="block">Block</option>
                <option value="notify">Notify</option>
                <option value="downgrade">Downgrade</option>
                <option value="throttle">Throttle</option>
                <option value="fallback">Fallback</option>
              </select>
            </label>

            <label className="block">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                Downgrade / fallback model
              </span>
              <input
                value={form.downgrade_to_model}
                onChange={(e) => setForm({ ...form, downgrade_to_model: e.target.value })}
                disabled={form.action !== 'downgrade' && form.action !== 'fallback'}
                placeholder="gpt-4o-mini"
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm disabled:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-white dark:disabled:bg-slate-800"
              />
            </label>
          </div>

          <label className="flex items-center gap-3 rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-700 dark:border-slate-800 dark:text-slate-300">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              className="h-4 w-4"
            />
            Keep this budget active
          </label>

          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </form>

        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <p className="text-xs uppercase tracking-wide text-slate-500">Temporary Override</p>
            <h2 className="mt-2 text-lg font-semibold text-slate-950 dark:text-slate-100">
              Create exception window
            </h2>
            <form onSubmit={handleCreateOverride} className="mt-4 space-y-4">
              <label className="block">
                <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                  Override limit (USD)
                </span>
                <input
                  required
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={overrideForm.override_limit_usd}
                  onChange={(e) =>
                    setOverrideForm({ ...overrideForm, override_limit_usd: e.target.value })
                  }
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                />
              </label>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block">
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                    Starts at
                  </span>
                  <input
                    required
                    type="datetime-local"
                    value={overrideForm.starts_at}
                    onChange={(e) => setOverrideForm({ ...overrideForm, starts_at: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                    Expires at
                  </span>
                  <input
                    required
                    type="datetime-local"
                    value={overrideForm.expires_at}
                    onChange={(e) =>
                      setOverrideForm({ ...overrideForm, expires_at: e.target.value })
                    }
                    className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </label>
              </div>
              <label className="block">
                <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                  Reason
                </span>
                <input
                  value={overrideForm.reason}
                  onChange={(e) => setOverrideForm({ ...overrideForm, reason: e.target.value })}
                  placeholder="Temporary launch or investigation exception"
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                />
              </label>
              <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 dark:border-slate-800 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={overrideForm.require_approval}
                  onChange={(e) =>
                    setOverrideForm({ ...overrideForm, require_approval: e.target.checked })
                  }
                  className="h-4 w-4"
                />
                Require approval before activation
              </label>
              <button
                type="submit"
                disabled={overrideSaving}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {overrideSaving ? 'Saving...' : 'Create Override'}
              </button>
            </form>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <p className="text-xs uppercase tracking-wide text-slate-500">Overrides</p>
            <div className="mt-3 space-y-3">
              {overrides.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  No overrides configured yet.
                </p>
              ) : (
                overrides.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-xl border border-slate-200 p-4 dark:border-slate-800"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-slate-950 dark:text-slate-100">
                          {formatMoney(item.override_limit_usd)} until{' '}
                          {new Date(item.expires_at).toLocaleString()}
                        </p>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          Original {formatMoney(item.original_limit_usd)} - {item.status}
                        </p>
                        {item.reason && (
                          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                            {item.reason}
                          </p>
                        )}
                        {item.approval_id && (
                          <Link
                            href="/approvals"
                            className="mt-2 inline-flex text-xs text-blue-600 hover:underline dark:text-blue-300"
                          >
                            Review approval
                          </Link>
                        )}
                      </div>
                      {item.status === 'active' && (
                        <button
                          onClick={() => handleRevokeOverride(item.id)}
                          className="rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-950/30"
                        >
                          Revoke
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <p className="text-xs uppercase tracking-wide text-slate-500">Breach History</p>
        <div className="mt-4">
          <BreachHistoryTable items={breaches} />
        </div>
      </div>
    </div>
  )
}
