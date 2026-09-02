'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { ChevronLeft } from 'lucide-react'
import { createBudgetOverride, revokeBudgetOverride, updateBudget, getBudgetPerformancePosture, getBudgetOrgScopePosture, getBudgetOverrideGovernancePosture, getFinOpsInternalPosture, getBudgetDetailDrillbackPosture, getBudgetOverrideExceptionPosture } from '@/lib/api'
import type { Breach, Budget, BudgetOverride, BudgetPerformancePosture, BudgetOrgScopePosture, BudgetOverrideGovernancePosture, FinOpsInternalPosture, BudgetDetailDrillbackPosture, BudgetOverrideExceptionPosture } from '@/types/api'
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
    return budget.scope_id
      ? { href: `/api-keys/${budget.scope_id}`, label: 'Open API key detail' }
      : { href: '/api-keys', label: 'Open API keys' }
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
  const [perfPosture, setPerfPosture] = useState<BudgetPerformancePosture | null>(null)
  const [perfLoading, setPerfLoading] = useState(false)
  const [orgPosture, setOrgPosture] = useState<BudgetOrgScopePosture | null>(null)
  const [orgLoading, setOrgLoading] = useState(false)
  const [govPosture, setGovPosture] = useState<BudgetOverrideGovernancePosture | null>(null)
  const [govLoading, setGovLoading] = useState(false)
  const [finopsPosture, setFinopsPosture] = useState<FinOpsInternalPosture | null>(null)
  const [drillbackPosture, setDrillbackPosture] = useState<BudgetDetailDrillbackPosture | null>(null)
  const [exceptionPosture, setExceptionPosture] = useState<BudgetOverrideExceptionPosture | null>(null)

  useEffect(() => {
    if (apiKey && initialBudget.id) {
      setPerfLoading(true)
      getBudgetPerformancePosture(apiKey, initialBudget.id)
        .then(setPerfPosture)
        .catch(() => {})
        .finally(() => setPerfLoading(false))

      setOrgLoading(true)
      getBudgetOrgScopePosture(apiKey, initialBudget.id)
        .then(setOrgPosture)
        .catch(() => {})
        .finally(() => setOrgLoading(false))

      setGovLoading(true)
      getBudgetOverrideGovernancePosture(apiKey)
        .then(setGovPosture)
        .catch(() => {})
        .finally(() => setGovLoading(false))

      getFinOpsInternalPosture(apiKey)
        .then(setFinopsPosture)
        .catch(() => {})

      getBudgetDetailDrillbackPosture(apiKey)
        .then(setDrillbackPosture)
        .catch(() => {})

      getBudgetOverrideExceptionPosture(apiKey)
        .then(setExceptionPosture)
        .catch(() => {})
    }
  }, [apiKey, initialBudget.id])

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

      {orgPosture && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50/50 p-6 shadow-sm dark:border-blue-900 dark:bg-blue-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">Org & Access Scope Context</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-blue-200 bg-white p-3 dark:border-blue-800 dark:bg-slate-900">
              <p className="text-xs text-slate-500 dark:text-slate-400">Workspace Users</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgPosture.org_context.workspace_users}</p>
            </div>
            <div className="rounded-xl border border-blue-200 bg-white p-3 dark:border-blue-800 dark:bg-slate-900">
              <p className="text-xs text-slate-500 dark:text-slate-400">Access Groups</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgPosture.org_context.workspace_access_groups}</p>
            </div>
            <div className="rounded-xl border border-blue-200 bg-white p-3 dark:border-blue-800 dark:bg-slate-900">
              <p className="text-xs text-slate-500 dark:text-slate-400">API Keys</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgPosture.org_context.workspace_api_keys}</p>
            </div>
            <div className="rounded-xl border border-blue-200 bg-white p-3 dark:border-blue-800 dark:bg-slate-900">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgPosture.org_context.total_active_budgets}</p>
            </div>
          </div>

          {orgPosture.scope_entity && Object.keys(orgPosture.scope_entity).length > 0 && (
            <div className="mt-4 rounded-xl border border-blue-200 bg-white p-4 dark:border-blue-800 dark:bg-slate-900">
              <p className="text-xs font-medium text-blue-600 dark:text-blue-400">
                {orgPosture.scope_type === 'access_group' ? 'Access Group' : 'API Key'} Detail
              </p>
              <div className="mt-2 grid gap-2 text-sm md:grid-cols-2">
                {orgPosture.scope_type === 'access_group' && (
                  <>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Name: </span>
                      <span className="font-medium text-slate-900 dark:text-white">{String(orgPosture.scope_entity.name ?? '—')}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Members: </span>
                      <span className="font-medium text-slate-900 dark:text-white">{String(orgPosture.scope_entity.member_count ?? 0)}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Guardrail profile: </span>
                      <span className="font-medium text-slate-900 dark:text-white">{String(orgPosture.scope_entity.guardrail_profile ?? 'None')}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Status: </span>
                      <span className={`font-medium ${orgPosture.scope_entity.is_active ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                        {orgPosture.scope_entity.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </>
                )}
                {orgPosture.scope_type === 'api_key' && (
                  <>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Name: </span>
                      <span className="font-medium text-slate-900 dark:text-white">{String(orgPosture.scope_entity.name ?? '—')}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Key prefix: </span>
                      <span className="font-mono font-medium text-slate-900 dark:text-white">{String(orgPosture.scope_entity.key_prefix ?? '—')}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Ownership: </span>
                      <span className="font-medium text-slate-900 dark:text-white">{String(orgPosture.scope_entity.ownership_type ?? '—')}</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-xl border border-blue-200 bg-white p-3 dark:border-blue-800 dark:bg-slate-900">
              <p className="text-xs text-slate-500 dark:text-slate-400">30d Workspace Spend</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">{formatMoney(orgPosture.org_context.total_spend_30d_usd)}</p>
            </div>
            <div className="rounded-xl border border-blue-200 bg-white p-3 dark:border-blue-800 dark:bg-slate-900">
              <p className="text-xs text-slate-500 dark:text-slate-400">AI Hub Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">
                {orgPosture.hub_context.hub_model_count} catalog
                <span className="ml-2 text-sm font-normal text-slate-500">({orgPosture.hub_context.distinct_models_30d} used 30d)</span>
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3 pt-3 mt-3 border-t border-blue-200 dark:border-blue-800">
            <Link href="/organization" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Organization</Link>
            <Link href="/access-groups" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Access Groups</Link>
            <Link href="/api-keys" className="text-xs text-blue-600 hover:underline dark:text-blue-400">API Keys</Link>
            <Link href="/ai-hub" className="text-xs text-blue-600 hover:underline dark:text-blue-400">AI Hub</Link>
            <Link href="/telemetry" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Telemetry</Link>
            <Link href="/users" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Users</Link>
          </div>
        </div>
      )}
      {orgLoading && (
        <p className="text-sm text-slate-400">Loading org & access scope context…</p>
      )}

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
            {budget.scope_type !== 'workspace' && budget.scope_display_name && (
              <p className="mt-1 text-xs text-blue-600 dark:text-blue-400">
                Scoped to {budget.scope_type.replace('_', ' ')}: {budget.scope_display_name}
              </p>
            )}
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
        <p className="text-xs uppercase tracking-wide text-slate-500">Spend by End User</p>
        {budget.breakdown && budget.breakdown.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm text-slate-600 dark:text-slate-400">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">End User ID</th>
                  <th className="text-right p-2">Spend (USD)</th>
                  <th className="text-right p-2">Run Count</th>
                  <th className="text-right p-2">Call Count</th>
                  <th className="text-right p-2">% of Total</th>
                </tr>
              </thead>
              <tbody>
                {budget.breakdown.map((entry) => (
                  <tr key={entry.end_user_id} className="border-t">
                    <td className="p-2">{entry.end_user_id}</td>
                    <td className="text-right p-2">{formatMoney(entry.cost_usd)}</td>
                    <td className="text-right p-2">{entry.run_count}</td>
                    <td className="text-right p-2">{entry.call_count}</td>
                    <td className="text-right p-2">{entry.pct_of_total}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
            No spend attributed to end users yet.
          </p>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <p className="text-xs uppercase tracking-wide text-slate-500">Performance Economics</p>
        {perfLoading ? (
          <p className="mt-4 text-sm text-slate-400">Loading performance posture…</p>
        ) : perfPosture ? (
          <div className="mt-4 space-y-4">
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-xs text-slate-500 dark:text-slate-400">Cache Hit Rate (30d)</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{perfPosture.cache.cache_hit_rate_pct}%</p>
                <p className="text-xs text-slate-400">{perfPosture.cache.cache_hits_30d.toLocaleString()} / {perfPosture.cache.total_requests_30d.toLocaleString()} requests</p>
              </div>
              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-xs text-slate-500 dark:text-slate-400">Est. Cache Savings</p>
                <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">~{perfPosture.cache.estimated_savings_pct}%</p>
                <p className="text-xs text-slate-400">avoided cost from cache hits</p>
              </div>
              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-xs text-slate-500 dark:text-slate-400">Rate-Limited Routes</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{perfPosture.rate_limits.rate_limited_routes} / {perfPosture.rate_limits.total_active_routes}</p>
                <p className="text-xs text-slate-400">{perfPosture.rate_limits.containment_coverage_pct}% containment</p>
              </div>
              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-xs text-slate-500 dark:text-slate-400">Billing Periods</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{perfPosture.billing.billing_period_count}</p>
                <p className="text-xs text-slate-400">{perfPosture.chargeback.chargeback_rule_count} chargeback rules</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-3 pt-2 border-t border-slate-200 dark:border-slate-700">
              <Link href="/gateway" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Gateway</Link>
              <Link href="/gateway#cache" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Response Cache</Link>
              <Link href="/gateway#rate-limits" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Rate Limits</Link>
              <Link href="/billing-periods" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Billing Periods</Link>
              <Link href="/billing-periods?view=detail" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Billing Detail</Link>
              <Link href="/chargeback" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Chargeback</Link>
              <Link href="/tool-registry" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Tool Registry</Link>
              <Link href="/approvals?status=pending" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Approvals</Link>
              <Link href="/alert-rules" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Alert Rules</Link>
              <Link href="/tags" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Tags</Link>
              <Link href="/cost-savings" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Cost & Savings</Link>
            </div>
          </div>
        ) : (
          <p className="mt-4 text-sm text-slate-400">Performance posture unavailable.</p>
        )}
      </div>

      <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-6 shadow-sm dark:border-amber-900 dark:bg-amber-950/30">
        <p className="text-xs uppercase tracking-wide text-amber-700 dark:text-amber-400">Safety &amp; Governance Context</p>
        {govLoading ? (
          <p className="mt-4 text-sm text-slate-400">Loading governance posture…</p>
        ) : govPosture ? (
          <div className="mt-4 space-y-4">
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
              <div className="rounded-xl border border-amber-200 p-3 dark:border-amber-800">
                <p className="text-xs text-slate-500 dark:text-slate-400">Pending Approvals</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{govPosture.approval_context.pending_approvals}</p>
                <p className="text-xs text-slate-400">{govPosture.approval_context.approved_30d} approved / {govPosture.approval_context.denied_30d} denied (30d)</p>
              </div>
              <div className="rounded-xl border border-amber-200 p-3 dark:border-amber-800">
                <p className="text-xs text-slate-500 dark:text-slate-400">Alert Rules</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{govPosture.alert_context.budget_alert_rules}</p>
                <p className="text-xs text-slate-400">{govPosture.alert_context.active_budget_alerts} active</p>
              </div>
              <div className="rounded-xl border border-amber-200 p-3 dark:border-amber-800">
                <p className="text-xs text-slate-500 dark:text-slate-400">Audit Events (30d)</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{govPosture.audit_context.override_audit_events_30d}</p>
                <p className="text-xs text-slate-400">{govPosture.audit_context.total_overrides} overrides total</p>
              </div>
              <div className="rounded-xl border border-amber-200 p-3 dark:border-amber-800">
                <p className="text-xs text-slate-500 dark:text-slate-400">Approval Coverage</p>
                <p className="mt-1 text-lg font-semibold text-amber-600 dark:text-amber-400">{govPosture.governance_context.approval_coverage_pct}%</p>
                <p className="text-xs text-slate-400">{govPosture.approval_context.overrides_with_approval} of {govPosture.audit_context.total_overrides} overrides</p>
              </div>
              <div className="rounded-xl border border-amber-200 p-3 dark:border-amber-800">
                <p className="text-xs text-slate-500 dark:text-slate-400">Tags</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{govPosture.tag_context.budget_tags + govPosture.tag_context.override_tags}</p>
                <p className="text-xs text-slate-400">{govPosture.tag_context.budget_tags} budget / {govPosture.tag_context.override_tags} override</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-3 pt-2 border-t border-amber-200 dark:border-amber-800">
              <Link href="/approvals?status=pending" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Approvals</Link>
              <Link href="/alert-rules" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Alert Rules</Link>
              <Link href="/audit-log" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Audit Log</Link>
              <Link href="/tags" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Tags</Link>
              <Link href="/governance" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Governance Pack</Link>
            </div>
          </div>
        ) : (
          <p className="mt-4 text-sm text-slate-400">Governance posture unavailable.</p>
        )}
      </div>

      {finopsPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 dark:border-emerald-900 dark:bg-emerald-950/40">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">FinOps Internal Posture</h2>
            <span className="text-xs text-emerald-600 dark:text-emerald-400">{finopsPosture.period_days}d window</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Billing Periods</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{finopsPosture.billing_context.total_periods}</p>
              <p className="text-xs text-slate-400">{finopsPosture.billing_context.open_periods} open · ${finopsPosture.billing_context.total_billed_usd.toFixed(2)} billed</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Chargeback Rules</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{finopsPosture.chargeback_context.total_rules}</p>
              <p className="text-xs text-slate-400">{finopsPosture.chargeback_context.active_rules} active</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Ledger Snapshots</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{finopsPosture.ledger_context.total_snapshots}</p>
              <p className="text-xs text-slate-400">latest: {finopsPosture.ledger_context.latest_snapshot_date}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Overrides</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{finopsPosture.override_context.total_overrides}</p>
              <p className="text-xs text-slate-400">{finopsPosture.override_context.active_overrides} active</p>
            </div>
            <div className="rounded-xl bg-white/80 p-3 dark:bg-slate-900/60">
              <p className="text-xs text-slate-500">Notifications</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{finopsPosture.notification_context.total_notifications}</p>
              <p className="text-xs text-slate-400">${finopsPosture.notification_context.spend_30d.toFixed(2)} 30d spend</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Link href="/billing" className="text-emerald-700 hover:underline dark:text-emerald-400">Billing →</Link>
            <Link href="/chargeback" className="text-emerald-700 hover:underline dark:text-emerald-400">Chargeback →</Link>
            <Link href="/settings?tab=compliance" className="text-emerald-700 hover:underline dark:text-emerald-400">Ledger →</Link>
            <Link href="/budgets" className="text-emerald-700 hover:underline dark:text-emerald-400">Budgets →</Link>
          </div>
        </div>
      )}

      {drillbackPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">Budget Detail Drillback Context</h2>
            <span className="text-xs text-emerald-600 dark:text-emerald-400">{drillbackPosture.period_days}d window</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Scope Owners</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{drillbackPosture.scope_context.workspace_users} users</p>
              <p className="text-xs text-slate-400">{drillbackPosture.scope_context.access_groups} groups · {drillbackPosture.scope_context.api_keys} keys</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Runtime</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{drillbackPosture.runtime_context.cache_configs} caches</p>
              <p className="text-xs text-slate-400">{drillbackPosture.runtime_context.rate_limited_routes} rate-limited routes</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Evidence</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{drillbackPosture.evidence_context.runs_30d} runs</p>
              <p className="text-xs text-slate-400">{drillbackPosture.evidence_context.requests_30d.toLocaleString()} requests · {drillbackPosture.evidence_context.audit_events_30d} audit</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Workflows</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{drillbackPosture.workflow_context.workflows} definitions</p>
              <p className="text-xs text-slate-400">{drillbackPosture.workflow_context.workflow_runs_30d} runs 30d</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Spend</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">${drillbackPosture.spend_context.total_spend_30d.toFixed(2)}</p>
              <p className="text-xs text-slate-400">{drillbackPosture.spend_context.distinct_models_30d} models</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Link href="/analytics/users" className="text-emerald-600 hover:underline dark:text-emerald-400">Users →</Link>
            <Link href="/access-groups" className="text-emerald-600 hover:underline dark:text-emerald-400">Access Groups →</Link>
            <Link href="/api-keys" className="text-emerald-600 hover:underline dark:text-emerald-400">API Keys →</Link>
            <Link href="/gateway" className="text-emerald-600 hover:underline dark:text-emerald-400">Gateway →</Link>
            <Link href="/runs" className="text-emerald-600 hover:underline dark:text-emerald-400">Runs →</Link>
            <Link href="/request-flow" className="text-emerald-600 hover:underline dark:text-emerald-400">Request Flow →</Link>
            <Link href="/audit" className="text-emerald-600 hover:underline dark:text-emerald-400">Audit Log →</Link>
            <Link href="/workflows" className="text-emerald-600 hover:underline dark:text-emerald-400">Workflows →</Link>
          </div>
        </div>
      )}

      {exceptionPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">Override Exception Context</h2>
            <span className="text-xs text-emerald-600 dark:text-emerald-400">{exceptionPosture.period_days}d window</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Overrides</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{exceptionPosture.override_context.total_overrides}</p>
              <p className="text-xs text-slate-400">{exceptionPosture.override_context.active_overrides} active · {exceptionPosture.override_context.expired_overrides} expired</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Approvals</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{exceptionPosture.approval_context.pending_approvals} pending</p>
              <p className="text-xs text-slate-400">{exceptionPosture.approval_context.approved_30d} approved · {exceptionPosture.approval_context.denied_30d} denied</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Runtime</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{exceptionPosture.runtime_context.active_routes} routes</p>
              <p className="text-xs text-slate-400">{exceptionPosture.runtime_context.rate_limited_routes} rate-limited</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Monitoring</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{exceptionPosture.monitoring_context.alert_rules} alert rules</p>
              <p className="text-xs text-slate-400">{exceptionPosture.monitoring_context.audit_events_30d} audit events</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Override Limit</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">${exceptionPosture.override_context.active_override_limit_usd.toFixed(2)}</p>
              <p className="text-xs text-slate-400">${exceptionPosture.spend_context.total_spend_30d.toFixed(2)} spend 30d</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Link href="/approvals" className="text-emerald-600 hover:underline dark:text-emerald-400">Approvals →</Link>
            <Link href="/alerts" className="text-emerald-600 hover:underline dark:text-emerald-400">Alert Rules →</Link>
            <Link href="/gateway" className="text-emerald-600 hover:underline dark:text-emerald-400">Gateway →</Link>
            <Link href="/audit" className="text-emerald-600 hover:underline dark:text-emerald-400">Audit Log →</Link>
            <Link href="/governance" className="text-emerald-600 hover:underline dark:text-emerald-400">Governance →</Link>
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <p className="text-xs uppercase tracking-wide text-slate-500">Breach History</p>
        <div className="mt-4">
          <BreachHistoryTable items={breaches} />
        </div>
      </div>
    </div>
  )
}
