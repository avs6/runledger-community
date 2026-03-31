'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useSearchParams, useRouter } from 'next/navigation'
import {
  Plus, Bell, Scale, DollarSign, TrendingDown, FileText,
  RefreshCw, Wallet, Building2, AlertTriangle, Webhook, Trash2,
} from 'lucide-react'
import { toast } from 'sonner'
import { useRole } from '@/components/rbac/useRole'
import type { Budget, NotificationResponse, BillingPeriod, ChargebackRuleResponse, BillingWebhookConfig } from '@/types/api'
import {
  getBudgets,
  listBudgetNotifications,
  createBudgetNotification,
  getBillingPeriods,
  listChargebackRules,
  createChargebackRule,
  listBillingWebhooks,
  createBillingWebhook,
  deleteBillingWebhook,
} from '@/lib/api'
import BudgetList from '@/components/budgets/BudgetList'
import CreateBudgetModal from '@/components/budgets/CreateBudgetModal'
import BillingPeriodTable from '@/components/billing/BillingPeriodTable'
import CreatePeriodModal from '@/components/billing/CreatePeriodModal'

const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const ALL_EVENTS = ['budget.breach', 'runaway.detected']

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500'

// ── Types ─────────────────────────────────────────────────────────────────────

interface WorkspaceFinanceSummary {
  workspace_id: string
  workspace_name: string
  spend_30d_usd: string
  active_budget_count: number
  total_budget_limit_usd: string
  open_billing_periods: number
  closed_billing_periods: number
}

interface OrgFinanceSummary {
  workspaces: WorkspaceFinanceSummary[]
  org_spend_30d_usd: string
  org_total_budget_limit_usd: string
}

// ── Org overview tab (org admin only) ─────────────────────────────────────────

function OrgOverviewTab({ apiKey }: { apiKey: string }) {
  const [summary, setSummary] = useState<OrgFinanceSummary | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const res = await fetch(`${apiBase}/org/finance`, {
        headers: { Authorization: `Bearer ${apiKey}` },
      })
      if (!res.ok) throw new Error(await res.text())
      setSummary(await res.json())
    } catch {
      toast.error('Failed to load org finance summary')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { load() }, [load])

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
        ))}
      </div>
    )
  }

  if (!summary) return null

  const totalSpend = parseFloat(summary.org_spend_30d_usd)
  const totalLimit = parseFloat(summary.org_total_budget_limit_usd)
  const utilization = totalLimit > 0 ? (totalSpend / totalLimit) * 100 : 0

  return (
    <div className="space-y-6">
      {/* Org totals */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <DollarSign className="h-3.5 w-3.5 text-violet-500" />
            Org Spend (30d)
          </div>
          <p className="text-2xl font-semibold text-slate-900 dark:text-white">
            ${totalSpend.toFixed(2)}
          </p>
          {totalLimit > 0 && (
            <p className="text-xs text-slate-400 mt-0.5">
              {utilization.toFixed(1)}% of ${totalLimit.toFixed(2)} budget
            </p>
          )}
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <Building2 className="h-3.5 w-3.5 text-indigo-500" />
            Workspaces
          </div>
          <p className="text-2xl font-semibold text-slate-900 dark:text-white">
            {summary.workspaces.length}
          </p>
          <p className="text-xs text-slate-400 mt-0.5">
            {summary.workspaces.filter((w) => w.active_budget_count > 0).length} with active budgets
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <FileText className="h-3.5 w-3.5 text-amber-500" />
            Open Billing Periods
          </div>
          <p className="text-2xl font-semibold text-slate-900 dark:text-white">
            {summary.workspaces.reduce((s, w) => s + w.open_billing_periods, 0)}
          </p>
          <p className="text-xs text-slate-400 mt-0.5">
            {summary.workspaces.reduce((s, w) => s + w.closed_billing_periods, 0)} closed
          </p>
        </div>
      </div>

      {/* Per-workspace breakdown */}
      <div>
        <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-3">
          Per-Workspace Breakdown
        </h2>
        <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Workspace</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Spend (30d)</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Budget</th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">Utilization</th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">Billing</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {summary.workspaces.map((ws) => {
                const spend = parseFloat(ws.spend_30d_usd)
                const limit = parseFloat(ws.total_budget_limit_usd)
                const util = limit > 0 ? (spend / limit) * 100 : null
                const overBudget = util !== null && util >= 100
                return (
                  <tr key={ws.workspace_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-500 text-white text-xs font-bold uppercase">
                          {ws.workspace_name[0]}
                        </div>
                        <span className="font-medium text-slate-900 dark:text-white">{ws.workspace_name}</span>
                        {overBudget && (
                          <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-sm text-slate-700 dark:text-slate-300">
                      ${spend.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-slate-500 dark:text-slate-400">
                      {ws.active_budget_count > 0 ? (
                        <span className="font-mono">${limit.toFixed(2)}</span>
                      ) : (
                        <span className="text-slate-300 dark:text-slate-600">No budget</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {util !== null ? (
                        <div className="flex items-center gap-2 justify-center">
                          <div className="w-20 h-1.5 rounded-full bg-slate-200 dark:bg-slate-700">
                            <div
                              className={`h-full rounded-full ${overBudget ? 'bg-red-500' : util > 80 ? 'bg-amber-500' : 'bg-violet-500'}`}
                              style={{ width: `${Math.min(util, 100)}%` }}
                            />
                          </div>
                          <span className={`text-xs font-medium ${overBudget ? 'text-red-600 dark:text-red-400' : 'text-slate-500 dark:text-slate-400'}`}>
                            {util.toFixed(0)}%
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-300 dark:text-slate-600">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2 text-xs">
                        {ws.open_billing_periods > 0 && (
                          <span className="rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 px-2 py-0.5">
                            {ws.open_billing_periods} open
                          </span>
                        )}
                        {ws.closed_billing_periods > 0 && (
                          <span className="rounded-full bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 px-2 py-0.5">
                            {ws.closed_billing_periods} closed
                          </span>
                        )}
                        {ws.open_billing_periods === 0 && ws.closed_billing_periods === 0 && (
                          <span className="text-slate-300 dark:text-slate-600">None</span>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      <button
        onClick={load}
        className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
      >
        <RefreshCw className="h-3.5 w-3.5" />
        Refresh summary
      </button>
    </div>
  )
}

// ── Budgets tab ────────────────────────────────────────────────────────────────

function BudgetsTab({
  apiKey, workspaceName,
}: { apiKey: string; workspaceName: string }) {
  const [budgets, setBudgets] = useState<Budget[]>([])
  const [loading, setLoading] = useState(true)
  const [showBudgetModal, setShowBudgetModal] = useState(false)
  const [notifications, setNotifications] = useState<NotificationResponse[]>([])
  const [notifChannel, setNotifChannel] = useState<'webhook' | 'slack'>('webhook')
  const [notifUrl, setNotifUrl] = useState('')
  const [notifEvents, setNotifEvents] = useState<string[]>(ALL_EVENTS)
  const [addingNotif, setAddingNotif] = useState(false)
  const [showNotifForm, setShowNotifForm] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [budgetData, notifData] = await Promise.all([
        getBudgets(apiKey),
        listBudgetNotifications(apiKey),
      ])
      setBudgets(budgetData.items)
      setNotifications(notifData.items)
    } catch {
      toast.error('Failed to load budgets')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { load() }, [load])

  function toggleEvent(event: string) {
    setNotifEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    )
  }

  async function handleAddNotification(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !notifUrl.trim() || notifEvents.length === 0) return
    setAddingNotif(true)
    try {
      const created = await createBudgetNotification(apiKey, {
        channel: notifChannel,
        destination_url: notifUrl.trim(),
        events: notifEvents,
      })
      setNotifications((prev) => [created, ...prev])
      setNotifUrl('')
      setNotifEvents(ALL_EVENTS)
      setShowNotifForm(false)
      toast.success('Notification channel added')
    } catch {
      toast.error('Failed to add notification channel')
    } finally {
      setAddingNotif(false)
    }
  }

  const activeBudgets = budgets.filter((b) => b.is_active).length
  const totalLimit = budgets.reduce((s, b) => s + parseFloat(b.limit_usd), 0)

  return (
    <div className="space-y-6">
      {/* Workspace context */}
      <div className="flex items-center gap-2 rounded-lg border border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-950/30 px-4 py-2.5">
        <div className="h-2 w-2 rounded-full bg-violet-500" />
        <span className="text-sm text-violet-800 dark:text-violet-200">
          Showing budgets for workspace: <span className="font-semibold">{workspaceName}</span>
        </span>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <DollarSign className="h-3.5 w-3.5 text-violet-500" />
            Active Budgets
          </div>
          <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{activeBudgets}</p>
          <p className="text-xs text-slate-400">${totalLimit.toFixed(2)} total limit</p>
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <Bell className="h-3.5 w-3.5 text-amber-500" />
            Alert Channels
          </div>
          <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{notifications.length}</p>
          <p className="text-xs text-slate-400">{notifications.filter((n) => n.is_active).length} active</p>
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <TrendingDown className="h-3.5 w-3.5 text-green-500" />
            Total Limit
          </div>
          <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">
            ${totalLimit.toFixed(0)}
          </p>
          <p className="text-xs text-slate-400">across {activeBudgets} budget{activeBudgets !== 1 ? 's' : ''}</p>
        </div>
      </div>

      {/* Budgets */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">Spend Limits</h2>
          <button
            onClick={() => setShowBudgetModal(true)}
            className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700"
          >
            <Plus className="h-4 w-4" />
            New Budget
          </button>
        </div>
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
            ))}
          </div>
        ) : budgets.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-600 p-8 text-center">
            <DollarSign className="mx-auto h-8 w-8 text-slate-300 dark:text-slate-600" />
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">No budgets for this workspace yet.</p>
            <button onClick={() => setShowBudgetModal(true)} className="mt-3 text-sm text-violet-600 hover:underline dark:text-violet-400">
              Create your first budget
            </button>
          </div>
        ) : (
          <BudgetList
            items={budgets}
            apiKey={apiKey}
            onDeleted={(id) => {
              setBudgets((prev) => prev.filter((b) => b.id !== id))
              toast.success('Budget deleted')
            }}
          />
        )}
      </div>

      {/* Notification Channels */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-slate-400" />
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">Notification Channels</h2>
          </div>
          {!showNotifForm && (
            <button
              onClick={() => setShowNotifForm(true)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Channel
            </button>
          )}
        </div>

        {showNotifForm && (
          <form onSubmit={handleAddNotification}
            className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4">
            <div className="mb-3 flex flex-wrap items-end gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-500 dark:text-slate-400">Channel type</label>
                <select value={notifChannel} onChange={(e) => setNotifChannel(e.target.value as 'webhook' | 'slack')} className={inputCls}>
                  <option value="webhook">Webhook</option>
                  <option value="slack">Slack</option>
                </select>
              </div>
              <div className="flex flex-1 flex-col gap-1">
                <label className="text-xs text-slate-500 dark:text-slate-400">
                  {notifChannel === 'slack' ? 'Slack webhook URL' : 'Destination URL'}
                </label>
                <input type="url" placeholder={notifChannel === 'slack' ? 'https://hooks.slack.com/services/...' : 'https://your-webhook.example.com'}
                  value={notifUrl} onChange={(e) => setNotifUrl(e.target.value)} className={`w-full ${inputCls}`} required />
              </div>
            </div>
            <div className="mb-3">
              <label className="mb-1.5 block text-xs text-slate-500 dark:text-slate-400">Trigger on events</label>
              <div className="flex flex-wrap gap-3">
                {ALL_EVENTS.map((ev) => (
                  <label key={ev} className="flex cursor-pointer items-center gap-1.5 text-sm dark:text-slate-300">
                    <input type="checkbox" checked={notifEvents.includes(ev)} onChange={() => toggleEvent(ev)}
                      className="rounded border-slate-300 text-violet-600 focus:ring-violet-500" />
                    <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs dark:bg-slate-700 dark:text-slate-300">{ev}</code>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button type="submit" disabled={addingNotif || notifEvents.length === 0}
                className="rounded-lg bg-violet-600 px-3 py-1.5 text-sm text-white hover:bg-violet-700 disabled:opacity-50">
                {addingNotif ? 'Adding…' : 'Add Channel'}
              </button>
              <button type="button" onClick={() => setShowNotifForm(false)}
                className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800">
                Cancel
              </button>
            </div>
          </form>
        )}

        {!loading && notifications.length === 0 && !showNotifForm && (
          <p className="text-sm text-slate-400 dark:text-slate-500">No notification channels configured.</p>
        )}

        {notifications.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-xs uppercase text-slate-500 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-2.5 text-left">Channel</th>
                  <th className="px-4 py-2.5 text-left">Destination</th>
                  <th className="px-4 py-2.5 text-left">Events</th>
                  <th className="px-4 py-2.5 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                {notifications.map((n) => (
                  <tr key={n.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-2">
                      <span className="rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700 dark:bg-violet-950 dark:text-violet-300">{n.channel}</span>
                    </td>
                    <td className="max-w-xs truncate px-4 py-2 font-mono text-xs text-slate-500 dark:text-slate-400">{n.destination_url}</td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap gap-1">
                        {n.events.map((ev) => (
                          <code key={ev} className="rounded bg-slate-100 px-1.5 py-0.5 text-xs dark:bg-slate-700">{ev}</code>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs ${n.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>
                        {n.is_active ? 'active' : 'inactive'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showBudgetModal && (
        <CreateBudgetModal
          apiKey={apiKey}
          onCreated={(budget) => {
            setBudgets((prev) => [budget, ...prev])
            toast.success('Budget created')
          }}
          onClose={() => setShowBudgetModal(false)}
        />
      )}
    </div>
  )
}

// ── Billing & Chargeback tab (org admin only) ──────────────────────────────────

function BillingTab({
  apiKey, workspaceName,
}: { apiKey: string; workspaceName: string }) {
  const [periods, setPeriods] = useState<BillingPeriod[]>([])
  const [billingLoading, setBillingLoading] = useState(true)
  const [showPeriodModal, setShowPeriodModal] = useState(false)
  const [rules, setRules] = useState<ChargebackRuleResponse[]>([])
  const [ruleAllocType, setRuleAllocType] = useState<'cost_center' | 'team' | 'env'>('cost_center')
  const [ruleDimension, setRuleDimension] = useState('')
  const [ruleWeight, setRuleWeight] = useState('')
  const [addingRule, setAddingRule] = useState(false)
  const [showRuleForm, setShowRuleForm] = useState(false)
  // Webhook state
  const [webhooks, setWebhooks] = useState<BillingWebhookConfig[]>([])
  const [showWebhookForm, setShowWebhookForm] = useState(false)
  const [webhookUrl, setWebhookUrl] = useState('')
  const [webhookSecret, setWebhookSecret] = useState('')
  const [webhookLabel, setWebhookLabel] = useState('')
  const [addingWebhook, setAddingWebhook] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey) return
    setBillingLoading(true)
    try {
      const [periodData, ruleData, webhookData] = await Promise.all([
        getBillingPeriods(apiKey),
        listChargebackRules(apiKey),
        listBillingWebhooks(apiKey),
      ])
      setPeriods(periodData.items)
      setRules(ruleData.items)
      setWebhooks(webhookData.items)
    } catch {
      toast.error('Failed to load billing data')
    } finally {
      setBillingLoading(false)
    }
  }, [apiKey])

  useEffect(() => { load() }, [load])

  async function handleAddRule(e: React.FormEvent) {
    e.preventDefault()
    if (!ruleDimension.trim() || !ruleWeight.trim()) return
    const w = parseFloat(ruleWeight)
    if (isNaN(w) || w < 0 || w > 1) { toast.error('Weight must be between 0 and 1'); return }
    setAddingRule(true)
    try {
      const created = await createChargebackRule(apiKey, {
        allocation_type: ruleAllocType, dimension: ruleDimension.trim(), weight: ruleWeight,
      })
      setRules((prev) => [created, ...prev])
      setRuleDimension(''); setRuleWeight(''); setShowRuleForm(false)
      toast.success('Chargeback rule added')
    } catch {
      toast.error('Failed to add chargeback rule')
    } finally {
      setAddingRule(false)
    }
  }

  async function handleAddWebhook(e: React.FormEvent) {
    e.preventDefault()
    if (!webhookUrl.trim() || !webhookSecret.trim()) return
    setAddingWebhook(true)
    try {
      const created = await createBillingWebhook(apiKey, {
        url: webhookUrl.trim(),
        secret: webhookSecret.trim(),
        label: webhookLabel.trim() || 'billing webhook',
      })
      setWebhooks((prev) => [created, ...prev])
      setWebhookUrl(''); setWebhookSecret(''); setWebhookLabel(''); setShowWebhookForm(false)
      toast.success('Billing webhook registered')
    } catch {
      toast.error('Failed to register webhook')
    } finally {
      setAddingWebhook(false)
    }
  }

  async function handleDeleteWebhook(id: string) {
    try {
      await deleteBillingWebhook(apiKey, id)
      setWebhooks((prev) => prev.filter((w) => w.id !== id))
      toast.success('Webhook deleted')
    } catch {
      toast.error('Failed to delete webhook')
    }
  }

  const openPeriods = periods.filter((p) => p.status === 'open').length

  return (
    <div className="space-y-6">
      {/* Workspace context */}
      <div className="flex items-center gap-2 rounded-lg border border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-950/30 px-4 py-2.5">
        <div className="h-2 w-2 rounded-full bg-violet-500" />
        <span className="text-sm text-violet-800 dark:text-violet-200">
          Showing billing for workspace: <span className="font-semibold">{workspaceName}</span>
        </span>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <TrendingDown className="h-3.5 w-3.5 text-green-500" />
            Open Billing Periods
          </div>
          <p className="text-2xl font-semibold text-slate-900 dark:text-white">{openPeriods}</p>
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <Scale className="h-3.5 w-3.5 text-purple-500" />
            Chargeback Rules
          </div>
          <p className="text-2xl font-semibold text-slate-900 dark:text-white">{rules.length}</p>
        </div>
      </div>

      {/* Billing Periods */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">Billing Periods</h2>
          <div className="flex items-center gap-2">
            <button onClick={() => load()} disabled={billingLoading}
              className="flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-2.5 py-1.5 text-xs text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40">
              <RefreshCw className={`h-3.5 w-3.5 ${billingLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button onClick={() => setShowPeriodModal(true)}
              className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700">
              <Plus className="h-4 w-4" />
              New Period
            </button>
          </div>
        </div>
        {billingLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
            ))}
          </div>
        ) : (
          <BillingPeriodTable
            items={periods}
            apiKey={apiKey}
            onClosed={(id) => {
              setPeriods((prev) => prev.map((p) => (p.id === id ? { ...p, status: 'closed' as const } : p)))
              toast.success('Period closed and signed')
              load()
            }}
          />
        )}
      </div>

      {/* Chargeback Rules */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-slate-400" />
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">Chargeback Rules</h2>
          </div>
          {!showRuleForm && (
            <button onClick={() => setShowRuleForm(true)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">
              <Plus className="h-3.5 w-3.5" />
              Add Rule
            </button>
          )}
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Chargeback rules define how costs are allocated across cost centres. Weight is a fraction (0–1) of total cost.
        </p>

        {showRuleForm && (
          <form onSubmit={handleAddRule}
            className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-500 dark:text-slate-400">Allocation type</label>
                <select value={ruleAllocType} onChange={(e) => setRuleAllocType(e.target.value as typeof ruleAllocType)} className={inputCls}>
                  <option value="cost_center">Cost Center</option>
                  <option value="team">Workspace</option>
                  <option value="env">Environment</option>
                </select>
              </div>
              <div className="flex flex-1 flex-col gap-1">
                <label className="text-xs text-slate-500 dark:text-slate-400">Dimension</label>
                <input type="text" placeholder="e.g. engineering" value={ruleDimension}
                  onChange={(e) => setRuleDimension(e.target.value)} className={`w-full ${inputCls}`} required />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-500 dark:text-slate-400">Weight (0–1)</label>
                <input type="number" step="0.01" min="0" max="1" placeholder="0.5" value={ruleWeight}
                  onChange={(e) => setRuleWeight(e.target.value)} className={`w-24 ${inputCls}`} required />
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <button type="submit" disabled={addingRule}
                className="rounded-lg bg-violet-600 px-3 py-1.5 text-sm text-white hover:bg-violet-700 disabled:opacity-50">
                {addingRule ? 'Adding…' : 'Add Rule'}
              </button>
              <button type="button" onClick={() => setShowRuleForm(false)}
                className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800">
                Cancel
              </button>
            </div>
          </form>
        )}

        {!billingLoading && rules.length === 0 && !showRuleForm && (
          <p className="text-sm text-slate-400 dark:text-slate-500">
            No chargeback rules defined.
          </p>
        )}

        {rules.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-2.5 text-left">Type</th>
                  <th className="px-4 py-2.5 text-left">Dimension</th>
                  <th className="px-4 py-2.5 text-right">Weight</th>
                  <th className="px-4 py-2.5 text-left">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                {rules.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-2">
                      <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-950 dark:text-purple-300">
                        {r.allocation_type}
                      </span>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs dark:text-slate-300">{r.dimension}</td>
                    <td className="px-4 py-2 text-right font-mono text-xs dark:text-slate-300">
                      {(parseFloat(r.weight) * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-2 text-xs text-slate-500">{new Date(r.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Billing Webhooks */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Webhook className="h-4 w-4 text-indigo-500" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Billing Webhooks</h3>
          </div>
          {!showWebhookForm && (
            <button
              onClick={() => setShowWebhookForm(true)}
              className="flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
            >
              <Plus className="h-3.5 w-3.5" /> Add Webhook
            </button>
          )}
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Receive HMAC-signed <code className="font-mono">billing.period.closed</code> events when a period is closed. Verify with <code className="font-mono">X-RunLedger-Signature</code>.
        </p>

        {showWebhookForm && (
          <form onSubmit={handleAddWebhook} className="space-y-3 rounded-lg border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-950/30 p-4">
            <div className="grid grid-cols-1 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Endpoint URL</label>
                <input type="url" required value={webhookUrl} onChange={(e) => setWebhookUrl(e.target.value)}
                  placeholder="https://your-app.example.com/hooks/billing"
                  className={inputCls + ' w-full'} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Signing Secret</label>
                <input type="password" required value={webhookSecret} onChange={(e) => setWebhookSecret(e.target.value)}
                  placeholder="Shared secret (min 8 chars)"
                  className={inputCls + ' w-full'} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Label (optional)</label>
                <input type="text" value={webhookLabel} onChange={(e) => setWebhookLabel(e.target.value)}
                  placeholder="e.g. Finance ERP"
                  className={inputCls + ' w-full'} />
              </div>
            </div>
            <div className="flex gap-2">
              <button type="submit" disabled={addingWebhook}
                className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                {addingWebhook ? 'Saving…' : 'Save'}
              </button>
              <button type="button" onClick={() => setShowWebhookForm(false)}
                className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800">
                Cancel
              </button>
            </div>
          </form>
        )}

        {!billingLoading && webhooks.length === 0 && !showWebhookForm && (
          <p className="text-sm text-slate-400 dark:text-slate-500">No webhooks configured.</p>
        )}

        {webhooks.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-2.5 text-left">Label</th>
                  <th className="px-4 py-2.5 text-left">URL</th>
                  <th className="px-4 py-2.5 text-center">Status</th>
                  <th className="px-4 py-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                {webhooks.map((w) => (
                  <tr key={w.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-2 font-medium text-slate-900 dark:text-white">{w.label}</td>
                    <td className="px-4 py-2 font-mono text-xs text-slate-500 dark:text-slate-400 max-w-xs truncate">{w.url}</td>
                    <td className="px-4 py-2 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${w.enabled ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>
                        {w.enabled ? 'enabled' : 'disabled'}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button onClick={() => handleDeleteWebhook(w.id)}
                        className="text-red-500 hover:text-red-700 dark:hover:text-red-400">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showPeriodModal && (
        <CreatePeriodModal
          apiKey={apiKey}
          onCreated={(period) => {
            setPeriods((prev) => [period, ...prev])
            toast.success('Billing period created')
          }}
          onClose={() => setShowPeriodModal(false)}
        />
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = 'overview' | 'budgets' | 'billing'

export default function FinancePage() {
  const { data: session } = useSession()
  const { isWorkspaceAdmin, isOrgAdmin, isPlatformAdmin } = useRole()
  const apiKey = (session as unknown as Record<string, unknown>)?.apiKey as string ?? ''
  const workspaceName = (session as unknown as Record<string, unknown>)?.workspaceName as string ?? 'Current Workspace'

  const searchParams = useSearchParams()
  const router = useRouter()
  const [tab, setTab] = useState<Tab>((searchParams.get('tab') as Tab) ?? (isOrgAdmin || isPlatformAdmin ? 'overview' : 'budgets'))

  const canAccessFinance = isWorkspaceAdmin || isOrgAdmin || isPlatformAdmin
  const canSeeBilling = isOrgAdmin || isPlatformAdmin

  function handleTabChange(t: Tab) {
    setTab(t)
    router.replace(t === 'budgets' ? '/finance' : `/finance?tab=${t}`, { scroll: false })
  }

  if (!canAccessFinance) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-800 mb-4">
          <Wallet className="h-7 w-7 text-slate-400 dark:text-slate-500" />
        </div>
        <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-1">
          Workspace Admin Access Required
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-xs">
          Finance is available to workspace admins and above. Contact your workspace administrator.
        </p>
      </div>
    )
  }

  const tabs: { id: Tab; label: string; icon: React.ReactNode; adminOnly: boolean }[] = [
    { id: 'overview', label: 'Org Overview', icon: <Building2 className="h-3.5 w-3.5" />, adminOnly: true },
    { id: 'budgets', label: 'Budgets', icon: <DollarSign className="h-3.5 w-3.5" />, adminOnly: false },
    { id: 'billing', label: 'Billing & Chargeback', icon: <FileText className="h-3.5 w-3.5" />, adminOnly: true },
  ]

  const visibleTabs = tabs.filter((t) => !t.adminOnly || canSeeBilling)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Finance</h1>
        <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">
          Budgets, spend guardrails, billing periods, and chargeback rules
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200 dark:border-slate-700">
        {visibleTabs.map(({ id, label, icon }) => (
          <button
            key={id}
            onClick={() => handleTabChange(id)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === id
                ? 'border-violet-500 text-violet-700 dark:text-violet-400'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
            }`}
          >
            {icon}
            {label}
          </button>
        ))}
      </div>

      {tab === 'overview' && canSeeBilling && <OrgOverviewTab apiKey={apiKey} />}
      {tab === 'budgets' && <BudgetsTab apiKey={apiKey} workspaceName={workspaceName} />}
      {tab === 'billing' && canSeeBilling && <BillingTab apiKey={apiKey} workspaceName={workspaceName} />}
    </div>
  )
}
