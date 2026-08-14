'use client'

import { useEffect, useMemo, useState } from 'react'
import { Plus } from 'lucide-react'
import type { Budget, BudgetRollupResponse, NotificationResponse } from '@/types/api'
import BudgetList from './BudgetList'
import BudgetNotificationsPanel from './BudgetNotificationsPanel'
import BudgetOverridesPanel from './BudgetOverridesPanel'
import CreateBudgetModal from './CreateBudgetModal'

interface Props {
  initialItems: Budget[]
  notifications: NotificationResponse[]
  rollup: BudgetRollupResponse | null
  apiKey: string
  initialTab?: 'policies' | 'overrides' | 'notifications'
  initialScopeType?: Budget['scope_type']
  initialScopeId?: string
  autoOpenCreate?: boolean
}

function formatMoney(value: string) {
  return `$${parseFloat(value).toFixed(2)}`
}

function SummaryCard({
  label,
  value,
  description,
}: {
  label: string
  value: string
  description: string
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950 dark:text-slate-100">{value}</p>
      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{description}</p>
    </div>
  )
}

export default function BudgetManager({
  initialItems,
  notifications,
  rollup,
  apiKey,
  initialTab = 'policies',
  initialScopeType,
  initialScopeId,
  autoOpenCreate = false,
}: Props) {
  const [items, setItems] = useState(initialItems)
  const [showCreate, setShowCreate] = useState(false)
  const [activeTab, setActiveTab] = useState<Props['initialTab']>(initialTab)

  const scopedItems = useMemo(() => {
    if (!initialScopeType) {
      return items
    }
    return items.filter((item) => {
      if (item.scope_type !== initialScopeType) return false
      if (!initialScopeId) return true
      return item.scope_id === initialScopeId
    })
  }, [initialScopeId, initialScopeType, items])
  const activeBudgets = useMemo(
    () => scopedItems.filter((item) => item.is_active),
    [scopedItems]
  )
  const atRiskCount = useMemo(
    () => scopedItems.filter((item) => parseFloat(item.pct_used) >= 80).length,
    [scopedItems]
  )

  useEffect(() => {
    if (autoOpenCreate) {
      setShowCreate(true)
      setActiveTab('policies')
    }
  }, [autoOpenCreate])

  const tabs: Array<{ id: NonNullable<Props['initialTab']>; label: string }> = [
    { id: 'policies', label: 'Policies' },
    { id: 'overrides', label: 'Overrides' },
    { id: 'notifications', label: 'Notifications' },
  ]

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <SummaryCard
          label="Active Budgets"
          value={String(activeBudgets.length)}
          description="Live policy objects currently enforcing spend behavior."
        />
        <SummaryCard
          label="At Risk"
          value={String(atRiskCount)}
          description="Budgets currently at or above 80% of configured limit."
        />
        <SummaryCard
          label="Current Spend"
          value={rollup ? formatMoney(rollup.current_spend_usd) : '$0.00'}
          description="Workspace rollup across currently active budget policies."
        />
        <SummaryCard
          label="Channels"
          value={String(notifications.length)}
          description="Webhook or Slack destinations receiving budget events."
        />
      </div>

      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950 md:flex-row md:items-end md:justify-between">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-wide text-slate-500">Spend Control Plane</p>
          <h2 className="text-xl font-semibold text-slate-950 dark:text-slate-100">
            Budget policy, exceptions, and breach delivery in one place
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Budgets own the policy lifecycle. Overrides and notifications stay attached to that
            policy instead of becoming separate FinOps products.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          New Budget
        </button>
      </div>

      {initialScopeType && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50/70 px-4 py-3 text-sm text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-100">
          Showing budget policy for <span className="font-semibold">{initialScopeType.replace('_', ' ')}</span>
          {initialScopeId ? <> <span className="font-mono text-xs">{initialScopeId}</span></> : null}.
          Create and edit budgets here without leaving the scoped flow.
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-full px-4 py-2 text-sm font-medium ${
              activeTab === tab.id
                ? 'bg-slate-950 text-white dark:bg-slate-100 dark:text-slate-950'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'policies' && (
        <BudgetList
          items={scopedItems}
          apiKey={apiKey}
          onDeleted={(id) => setItems((current) => current.filter((item) => item.id !== id))}
          emptyMessage={
            initialScopeType
              ? 'No budgets are attached to this scope yet. Create one to start enforcing spend policy here.'
              : undefined
          }
        />
      )}

      {activeTab === 'overrides' && <BudgetOverridesPanel budgets={items} apiKey={apiKey} />}

      {activeTab === 'notifications' && (
        <BudgetNotificationsPanel initialItems={notifications} apiKey={apiKey} />
      )}

      {showCreate && (
        <CreateBudgetModal
          apiKey={apiKey}
          onClose={() => setShowCreate(false)}
          initialScopeType={initialScopeType}
          initialScopeId={initialScopeId}
          onCreated={(budget) => {
            setItems((current) => [budget, ...current])
            setActiveTab('policies')
          }}
        />
      )}
    </div>
  )
}
