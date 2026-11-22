'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { toast } from 'sonner'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import {
  apiErrorMessage,
  createChargebackRule,
  createCostCenter,
  deleteChargebackRule,
  deleteCostCenter,
  getChargebackReport,
  listChargebackRules,
  listCostCenters,
  updateChargebackRule,
  updateCostCenter,
} from '@/lib/api'
import type { ChargebackRuleDimension, ChargebackRuleResponse, CostCenter } from '@/types/api'

const RULE_DIMENSIONS: Array<{ value: ChargebackRuleDimension; label: string }> = [
  { value: 'feature_tag', label: 'Workflow tag' },
  { value: 'application', label: 'Application' },
  { value: 'api_key', label: 'API key' },
  { value: 'access_group', label: 'Access group' },
  { value: 'end_user', label: 'End user' },
  { value: 'model', label: 'Model' },
  { value: 'provider', label: 'Provider' },
  { value: 'intent', label: 'Intent' },
]

type RuleForm = {
  dimension: ChargebackRuleDimension
  dimension_value: string
  cost_center_id: string
  allocation_type: 'direct' | 'shared_weight'
  weight: string
  require_approval: boolean
}

const EMPTY_RULE: RuleForm = {
  dimension: 'feature_tag',
  dimension_value: '',
  cost_center_id: '',
  allocation_type: 'shared_weight',
  weight: '1',
  require_approval: false,
}

const inputCls =
  'w-full rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-rose-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100'
const btn =
  'rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800'
const primary =
  'rounded-lg bg-gradient-to-r from-rose-600 to-orange-600 px-4 py-1.5 text-xs font-semibold text-white shadow-sm hover:brightness-110 disabled:opacity-50'

const STATUS_STYLE: Record<ChargebackRuleResponse['status'], string> = {
  active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  pending_approval: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  denied: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
  inactive: 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
}

/**
 * Cost centers and the chargeback rules that map dimension values to them.
 *
 * A rule says "cost of <dimension> = <value> goes to <cost center> at <weight>".
 * Active weights for one value add up to at most 100 %, and all active rules use one
 * dimension so nothing is charged twice. Approval-gated rules activate only when a
 * different admin approves them in Approvals.
 */
export default function ChargebackRulesPanel({
  apiKey,
  period,
  onChange,
}: {
  apiKey: string
  period: string
  /** Called after any rule or cost-center change, so the page can refresh its counters. */
  onChange?: () => void
}) {
  const [rules, setRules] = useState<ChargebackRuleResponse[]>([])
  const [centers, setCenters] = useState<CostCenter[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<RuleForm>(EMPTY_RULE)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [valueOptions, setValueOptions] = useState<Array<{ key: string; label: string }>>([])
  const [ccForm, setCcForm] = useState({ name: '', code: '', parent_id: '' })
  const [ccEditing, setCcEditing] = useState<{ id: string; name: string; code: string } | null>(null)

  const centerName = useMemo(() => new Map(centers.map((c) => [c.id, c.code ? `${c.name} (${c.code})` : c.name])), [centers])
  const activeDimension = rules.find((r) => r.status === 'active')?.dimension

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [r, c] = await Promise.all([listChargebackRules(apiKey), listCostCenters(apiKey)])
      setRules(r.items)
      setCenters(c.items)
      onChange?.()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to load chargeback rules'))
    } finally {
      setLoading(false)
    }
  }, [apiKey, onChange])

  useEffect(() => {
    void load()
  }, [load])

  // Suggest values that actually carry cost this month for the chosen dimension.
  useEffect(() => {
    if (!showForm) return
    let cancelled = false
    getChargebackReport(apiKey, { period, dimension: form.dimension })
      .then((res) => {
        if (cancelled) return
        const items = res.items[0]?.breakdown ?? []
        setValueOptions(
          items.filter((i) => i.dimension_key).map((i) => ({ key: String(i.dimension_key), label: i.dimension_value })),
        )
      })
      .catch(() => setValueOptions([]))
    return () => {
      cancelled = true
    }
  }, [apiKey, period, form.dimension, showForm])

  function startCreate() {
    setEditingId(null)
    setForm({ ...EMPTY_RULE, dimension: activeDimension ?? 'feature_tag', cost_center_id: centers[0]?.id ?? '' })
    setShowForm(true)
  }

  function startEdit(rule: ChargebackRuleResponse) {
    setEditingId(rule.id)
    setForm({
      dimension: rule.dimension,
      dimension_value: rule.dimension_value ?? '',
      cost_center_id: rule.cost_center_id ?? '',
      allocation_type: rule.allocation_type,
      weight: rule.weight,
      require_approval: rule.approval_id !== null,
    })
    setShowForm(true)
  }

  async function saveRule() {
    if (!form.dimension_value.trim() || !form.cost_center_id) {
      toast.error('Pick a value and a cost center')
      return
    }
    setSaving(true)
    try {
      const weight = form.allocation_type === 'direct' ? '1' : form.weight
      if (editingId) {
        const updated = await updateChargebackRule(apiKey, editingId, {
          dimension: form.dimension,
          dimension_value: form.dimension_value.trim(),
          cost_center_id: form.cost_center_id,
          allocation_type: form.allocation_type,
          weight,
        })
        toast.success(updated.status === 'pending_approval' ? 'Rule changed — sent back for approval' : 'Rule updated')
      } else {
        const created = await createChargebackRule(apiKey, {
          dimension: form.dimension,
          dimension_value: form.dimension_value.trim(),
          cost_center_id: form.cost_center_id,
          allocation_type: form.allocation_type,
          weight,
          require_approval: form.require_approval,
        })
        toast.success(created.status === 'pending_approval' ? 'Rule waiting for approval' : 'Rule active')
      }
      setShowForm(false)
      await load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to save rule'))
    } finally {
      setSaving(false)
    }
  }

  async function toggle(rule: ChargebackRuleResponse) {
    try {
      await updateChargebackRule(apiKey, rule.id, { status: rule.status === 'active' ? 'inactive' : 'active' })
      await load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to change rule status'))
    }
  }

  async function removeRule(rule: ChargebackRuleResponse) {
    if (!window.confirm(`Delete the rule for ${rule.dimension_value}? Its cost becomes unassigned.`)) return
    try {
      await deleteChargebackRule(apiKey, rule.id)
      await load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to delete rule'))
    }
  }

  async function addCenter() {
    if (!ccForm.name.trim()) return
    try {
      await createCostCenter(apiKey, {
        name: ccForm.name.trim(),
        code: ccForm.code.trim() || null,
        parent_id: ccForm.parent_id || null,
      })
      setCcForm({ name: '', code: '', parent_id: '' })
      await load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to create cost center'))
    }
  }

  async function saveCenter() {
    if (!ccEditing) return
    try {
      await updateCostCenter(apiKey, ccEditing.id, { name: ccEditing.name.trim(), code: ccEditing.code.trim() || null })
      setCcEditing(null)
      await load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to update cost center'))
    }
  }

  async function removeCenter(cc: CostCenter) {
    if (!window.confirm(`Delete cost center ${cc.name}?`)) return
    try {
      await deleteCostCenter(apiKey, cc.id)
      await load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to delete cost center'))
    }
  }

  const valueLabel = (rule: ChargebackRuleResponse) =>
    valueOptions.find((o) => o.key === rule.dimension_value)?.label ?? rule.dimension_value ?? '—'

  return (
    <div className="space-y-4">
      {/* Cost centers */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold text-slate-900 dark:text-white">Cost centers</h3>
            <p className="text-[10px] text-slate-500">Where cost is charged back to. Nest them to mirror your finance structure.</p>
          </div>
        </div>
        <div className="mb-3 grid gap-2 md:grid-cols-4">
          <input className={inputCls} placeholder="Name (e.g. Support)" value={ccForm.name} onChange={(e) => setCcForm((f) => ({ ...f, name: e.target.value }))} />
          <input className={inputCls} placeholder="Code (optional)" value={ccForm.code} onChange={(e) => setCcForm((f) => ({ ...f, code: e.target.value }))} />
          <select className={inputCls} value={ccForm.parent_id} onChange={(e) => setCcForm((f) => ({ ...f, parent_id: e.target.value }))} aria-label="Parent cost center">
            <option value="">No parent</option>
            {centers.map((c) => <option key={c.id} value={c.id}>{centerName.get(c.id)}</option>)}
          </select>
          <button type="button" className={primary} onClick={() => void addCenter()} disabled={!ccForm.name.trim()}>
            <Plus className="mr-1 inline h-3 w-3" />Add cost center
          </button>
        </div>
        {centers.length === 0 ? (
          <p className="rounded border border-dashed border-slate-300 py-3 text-center text-[11px] text-slate-400 dark:border-slate-700">
            No cost centers yet. Add one before creating rules.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {centers.map((c) =>
              ccEditing?.id === c.id ? (
                <span key={c.id} className="flex items-center gap-1 rounded-lg border border-rose-300 px-2 py-1">
                  <input className="w-28 bg-transparent text-xs outline-none" value={ccEditing.name} onChange={(e) => setCcEditing({ ...ccEditing, name: e.target.value })} aria-label="Cost center name" />
                  <input className="w-16 bg-transparent text-xs outline-none" value={ccEditing.code} onChange={(e) => setCcEditing({ ...ccEditing, code: e.target.value })} aria-label="Cost center code" placeholder="code" />
                  <button type="button" className="text-[10px] font-semibold text-rose-600" onClick={() => void saveCenter()}>Save</button>
                  <button type="button" className="text-[10px] text-slate-500" onClick={() => setCcEditing(null)}>Cancel</button>
                </span>
              ) : (
                <span key={c.id} className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-2 py-1 text-xs dark:border-slate-700">
                  {c.parent_id ? <span className="text-slate-400">{centerName.get(c.parent_id)} ›</span> : null}
                  <span className="font-semibold text-slate-800 dark:text-slate-100">{c.name}</span>
                  {c.code ? <span className="font-mono text-[10px] text-slate-400">{c.code}</span> : null}
                  <button type="button" aria-label={`Edit ${c.name}`} onClick={() => setCcEditing({ id: c.id, name: c.name, code: c.code ?? '' })}>
                    <Pencil className="h-3 w-3 text-slate-400 hover:text-slate-700" />
                  </button>
                  <button type="button" aria-label={`Delete ${c.name}`} onClick={() => void removeCenter(c)}>
                    <Trash2 className="h-3 w-3 text-rose-400 hover:text-rose-600" />
                  </button>
                </span>
              ),
            )}
          </div>
        )}
      </div>

      {/* Rules */}
      <div className="flex items-center justify-between">
        <p className="text-[11px] text-slate-500">
          {activeDimension
            ? `Active rules map by ${RULE_DIMENSIONS.find((d) => d.value === activeDimension)?.label ?? activeDimension}. Deactivate them to map by another dimension.`
            : 'Map dimension values (e.g. a workflow tag) to cost centers. Unmapped cost shows as unassigned.'}
        </p>
        <button type="button" className={primary} onClick={startCreate} disabled={centers.length === 0}>
          <Plus className="mr-1 inline h-3 w-3" />New rule
        </button>
      </div>

      {showForm && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <h3 className="mb-3 text-xs font-bold text-slate-900 dark:text-white">{editingId ? 'Edit rule' : 'New rule'}</h3>
          <div className="grid gap-3 md:grid-cols-3">
            <label className="block text-xs">
              <span className="mb-1 block font-semibold text-slate-500">Dimension</span>
              <select className={inputCls} value={form.dimension} onChange={(e) => setForm((f) => ({ ...f, dimension: e.target.value as ChargebackRuleDimension, dimension_value: '' }))}>
                {RULE_DIMENSIONS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
              </select>
            </label>
            <label className="block text-xs">
              <span className="mb-1 block font-semibold text-slate-500">Value</span>
              <input className={inputCls} list="chargeback-values" value={form.dimension_value} placeholder="Type or pick a value with cost this month" onChange={(e) => setForm((f) => ({ ...f, dimension_value: e.target.value }))} />
              <datalist id="chargeback-values">
                {valueOptions.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
              </datalist>
            </label>
            <label className="block text-xs">
              <span className="mb-1 block font-semibold text-slate-500">Cost center</span>
              <select className={inputCls} value={form.cost_center_id} onChange={(e) => setForm((f) => ({ ...f, cost_center_id: e.target.value }))}>
                <option value="">Select…</option>
                {centers.map((c) => <option key={c.id} value={c.id}>{centerName.get(c.id)}</option>)}
              </select>
            </label>
            <label className="block text-xs">
              <span className="mb-1 block font-semibold text-slate-500">Allocation</span>
              <select className={inputCls} value={form.allocation_type} onChange={(e) => setForm((f) => ({ ...f, allocation_type: e.target.value as RuleForm['allocation_type'] }))}>
                <option value="shared_weight">Share by weight</option>
                <option value="direct">Direct (100 %)</option>
              </select>
            </label>
            <label className="block text-xs">
              <span className="mb-1 block font-semibold text-slate-500">Weight (0–1)</span>
              <input className={inputCls} type="number" min="0.0001" max="1" step="0.05" disabled={form.allocation_type === 'direct'} value={form.allocation_type === 'direct' ? '1' : form.weight} onChange={(e) => setForm((f) => ({ ...f, weight: e.target.value }))} />
            </label>
            {!editingId && (
              <label className="flex items-end gap-2 pb-1 text-xs text-slate-700 dark:text-slate-300">
                <input type="checkbox" className="rounded" checked={form.require_approval} onChange={(e) => setForm((f) => ({ ...f, require_approval: e.target.checked }))} />
                Require approval by another admin
              </label>
            )}
          </div>
          <div className="mt-4 flex gap-2">
            <button type="button" className={primary} disabled={saving} onClick={() => void saveRule()}>{saving ? 'Saving…' : editingId ? 'Save rule' : 'Create rule'}</button>
            <button type="button" className={btn} onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                {['Dimension', 'Value', 'Cost center', 'Share', 'Status', 'Created by', ''].map((h) => (
                  <th key={h} className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-6 text-center text-slate-500">Loading rules…</td></tr>
              ) : rules.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-6 text-center text-slate-500">No chargeback rules yet.</td></tr>
              ) : (
                rules.map((rule) => (
                  <tr key={rule.id} className="bg-white dark:bg-slate-900">
                    <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300">{RULE_DIMENSIONS.find((d) => d.value === rule.dimension)?.label ?? rule.dimension}</td>
                    <td className="px-4 py-2.5 font-mono text-slate-900 dark:text-white">{valueLabel(rule)}</td>
                    <td className="px-4 py-2.5 text-slate-700 dark:text-slate-200">{rule.cost_center_id ? centerName.get(rule.cost_center_id) ?? '(deleted)' : '—'}</td>
                    <td className="px-4 py-2.5 font-mono">{(Number(rule.weight) * 100).toFixed(0)} %</td>
                    <td className="px-4 py-2.5">
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${STATUS_STYLE[rule.status]}`}>{rule.status.replace('_', ' ')}</span>
                      {rule.status === 'pending_approval' && (
                        <Link href="/approvals" className="ml-2 text-[10px] text-amber-700 underline dark:text-amber-300">Approve in Approvals</Link>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-slate-500">{rule.created_by ?? '—'}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex justify-end gap-1.5">
                        {(rule.status === 'active' || rule.status === 'inactive') && (
                          <button type="button" className={btn} onClick={() => void toggle(rule)}>{rule.status === 'active' ? 'Deactivate' : 'Activate'}</button>
                        )}
                        <button type="button" aria-label="Edit rule" className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300" onClick={() => startEdit(rule)}>
                          <Pencil className="h-3 w-3" />
                        </button>
                        <button type="button" aria-label="Delete rule" className="rounded-md border border-rose-200 p-1.5 text-rose-600 hover:bg-rose-50 dark:border-rose-800/40 dark:text-rose-400" onClick={() => void removeRule(rule)}>
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
