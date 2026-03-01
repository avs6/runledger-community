'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { Plus, Scale } from 'lucide-react'
import { toast } from 'sonner'
import type { BillingPeriod, ChargebackRuleResponse } from '@/types/api'
import { getBillingPeriods, listChargebackRules, createChargebackRule } from '@/lib/api'
import BillingPeriodTable from '@/components/billing/BillingPeriodTable'
import CreatePeriodModal from '@/components/billing/CreatePeriodModal'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500'

export default function BillingPage() {
  const { data: session } = useSession()
  const apiKey = session?.apiKey ?? ''

  // ── Billing periods ───────────────────────────────────────────────────────────
  const [periods, setPeriods] = useState<BillingPeriod[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)

  // ── Chargeback rules ──────────────────────────────────────────────────────────
  const [rules, setRules] = useState<ChargebackRuleResponse[]>([])
  const [ruleAllocType, setRuleAllocType] = useState<'cost_center' | 'team' | 'env'>('cost_center')
  const [ruleDimension, setRuleDimension] = useState('')
  const [ruleWeight, setRuleWeight] = useState('')
  const [addingRule, setAddingRule] = useState(false)
  const [showRuleForm, setShowRuleForm] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [periodData, ruleData] = await Promise.all([
        getBillingPeriods(apiKey),
        listChargebackRules(apiKey),
      ])
      setPeriods(periodData.items)
      setRules(ruleData.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load billing data')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => {
    load()
  }, [load])

  function handleCreated(period: BillingPeriod) {
    setPeriods((prev) => [period, ...prev])
    toast.success('Billing period created')
  }

  function handleClosed(id: string) {
    setPeriods((prev) =>
      prev.map((p) => (p.id === id ? { ...p, status: 'closed' as const } : p))
    )
    toast.success('Period closed and signed')
    load()
  }

  async function handleAddRule(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !ruleDimension.trim() || !ruleWeight.trim()) return
    const w = parseFloat(ruleWeight)
    if (isNaN(w) || w < 0 || w > 1) {
      toast.error('Weight must be between 0 and 1')
      return
    }
    setAddingRule(true)
    try {
      const created = await createChargebackRule(apiKey, {
        allocation_type: ruleAllocType,
        dimension: ruleDimension.trim(),
        weight: ruleWeight,
      })
      setRules((prev) => [created, ...prev])
      setRuleDimension('')
      setRuleWeight('')
      setShowRuleForm(false)
      toast.success('Chargeback rule added')
    } catch (err) {
      console.error(err)
      toast.error('Failed to add chargeback rule')
    } finally {
      setAddingRule(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* ── Billing Periods ───────────────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold dark:text-white">Billing</h1>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            New Period
          </button>
        </div>

        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800" />
            ))}
          </div>
        ) : (
          <BillingPeriodTable items={periods} apiKey={apiKey} onClosed={handleClosed} />
        )}
      </div>

      {/* ── Chargeback Rules ──────────────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            <h2 className="text-base font-semibold dark:text-gray-100">Chargeback Rules</h2>
          </div>
          {!showRuleForm && (
            <button
              onClick={() => setShowRuleForm(true)}
              className="flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Rule
            </button>
          )}
        </div>

        <p className="text-xs text-gray-500 dark:text-gray-400">
          Chargeback rules define how costs are allocated across cost centres, teams, or environments.
          Weight is a fraction (0–1) of total cost to assign to this dimension.
        </p>

        {showRuleForm && (
          <form
            onSubmit={handleAddRule}
            className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/50"
          >
            <div className="flex flex-wrap items-end gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 dark:text-gray-400">Allocation type</label>
                <select
                  value={ruleAllocType}
                  onChange={(e) => setRuleAllocType(e.target.value as typeof ruleAllocType)}
                  className={inputCls}
                >
                  <option value="cost_center">Cost Center</option>
                  <option value="team">Team</option>
                  <option value="env">Environment</option>
                </select>
              </div>
              <div className="flex flex-1 flex-col gap-1">
                <label className="text-xs text-gray-500 dark:text-gray-400">
                  Dimension (e.g. engineering, prod)
                </label>
                <input
                  type="text"
                  placeholder="e.g. engineering"
                  value={ruleDimension}
                  onChange={(e) => setRuleDimension(e.target.value)}
                  className={`w-full ${inputCls}`}
                  required
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 dark:text-gray-400">Weight (0–1)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  placeholder="0.5"
                  value={ruleWeight}
                  onChange={(e) => setRuleWeight(e.target.value)}
                  className={`w-24 ${inputCls}`}
                  required
                />
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <button
                type="submit"
                disabled={addingRule}
                className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {addingRule ? 'Adding…' : 'Add Rule'}
              </button>
              <button
                type="button"
                onClick={() => setShowRuleForm(false)}
                className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {!loading && rules.length === 0 && !showRuleForm && (
          <p className="text-sm text-gray-400 dark:text-gray-500">
            No chargeback rules defined. Add rules to split costs across cost centres or teams.
          </p>
        )}

        {rules.length > 0 && (
          <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                <tr>
                  <th className="px-4 py-2 text-left">Allocation Type</th>
                  <th className="px-4 py-2 text-left">Dimension</th>
                  <th className="px-4 py-2 text-right">Weight</th>
                  <th className="px-4 py-2 text-left">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {rules.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-4 py-2">
                      <span className="rounded bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-950 dark:text-purple-300">
                        {r.allocation_type}
                      </span>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">{r.dimension}</td>
                    <td className="px-4 py-2 text-right font-mono text-xs dark:text-gray-300">
                      {(parseFloat(r.weight) * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">
                      {new Date(r.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && session?.apiKey && (
        <CreatePeriodModal
          apiKey={session.apiKey}
          onCreated={handleCreated}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}
