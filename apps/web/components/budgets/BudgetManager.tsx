'use client'

import { useEffect, useMemo, useState } from 'react'
import { Plus, Shield } from 'lucide-react'
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
    <div className="space-y-5">
      {/* KPI cards */}
      <div className="grid gap-3 md:grid-cols-4">
        {[
          { label: 'Active Budgets', value: String(activeBudgets.length), sub: 'Live policies enforcing spend.' },
          { label: 'At Risk', value: String(atRiskCount), sub: 'Budgets at or above 80% of limit.' },
          { label: 'Current Spend', value: rollup ? formatMoney(rollup.current_spend_usd) : '$0.00', sub: 'Workspace rollup.' },
          { label: 'Channels', value: String(notifications.length), sub: 'Webhook/Slack destinations.' },
        ].map(({ label, value, sub }) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</p>
            <p className="mt-1.5 text-xl font-bold text-slate-900 dark:text-white">{value}</p>
            <p className="mt-1 text-[11px] text-slate-500">{sub}</p>
          </div>
        ))}
      </div>

      {/* Spend control banner + new budget */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Shield className="h-4 w-4 text-blue-500" />
            <p className="text-xs font-bold text-slate-900 dark:text-white">Spend Control Plane</p>
          </div>
          <p className="text-[11px] text-slate-500">
            Budgets own the policy lifecycle. Overrides and notifications stay attached to that policy instead of becoming separate products.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:brightness-110"
        >
          <Plus className="h-3.5 w-3.5" /> New Budget
        </button>
      </div>

      {initialScopeType && (
        <div className="rounded-lg border border-blue-200 bg-blue-50/70 px-3 py-2 text-[11px] text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-100">
          Showing budget policy for <span className="font-semibold">{initialScopeType.replace('_', ' ')}</span>
          {initialScopeId ? <> <span className="font-mono text-[10px]">{initialScopeId}</span></> : null}.
        </div>
      )}

      {/* Tab bar */}
      <div className="rounded-lg bg-slate-100 p-1 dark:bg-slate-800/80">
        <nav className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                activeTab === tab.id
                  ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
                  : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
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
