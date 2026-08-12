'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  ShieldCheck,
  Plus,
  Edit2,
  Trash2,
  X,
  Search,
} from 'lucide-react'
import {
  listGuardrailRules,
  createGuardrailRule,
  updateGuardrailRule,
  deleteGuardrailRule,
  getGuardrailStats,
  listGuardrailEvents,
  listGuardrailTemplates,
  listPartnerGuardrails,
} from '@/lib/api'
import type {
  GuardrailRuleResponse,
  GuardrailStats,
  GuardrailEventList,
  GuardrailTemplate,
  PartnerGuardrailList,
} from '@/types/api'

function pct(value: number | null | undefined) {
  if (value == null) return '--'
  return `${(value * 100).toFixed(1)}%`
}

const severityColors: Record<string, string> = {
  critical: 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300 border-rose-200',
  high: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 border-amber-200',
  medium: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 border-blue-200',
  low: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200',
}

const inputCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'

export default function GuardrailsPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey

  const [rules, setRules] = useState<GuardrailRuleResponse[]>([])
  const [stats, setStats] = useState<GuardrailStats | null>(null)
  const [events, setEvents] = useState<GuardrailEventList | null>(null)
  const [templates, setTemplates] = useState<GuardrailTemplate[]>([])
  const [partners, setPartners] = useState<PartnerGuardrailList | null>(null)
  const [loading, setLoading] = useState(true)

  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  // ── Create / Edit modal ───────────────────────────────────────────────────
  const [showModal, setShowModal] = useState(false)
  const [editingRule, setEditingRule] = useState<GuardrailRuleResponse | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [mode, setMode] = useState('pre_call')
  const [ruleType, setRuleType] = useState('custom')
  const [severity, setSeverity] = useState('medium')
  const [logic, setLogic] = useState('')
  const [saving, setSaving] = useState(false)

  async function loadData() {
    if (!apiKey) return
    setLoading(true)
    try {
      const [rulesRes, statsRes, eventsRes, templatesRes, partnersRes] =
        await Promise.all([
          listGuardrailRules(apiKey, { limit: 50 }),
          getGuardrailStats(apiKey, 24).catch(() => null),
          listGuardrailEvents(apiKey, { limit: 8 }).catch(() => null),
          listGuardrailTemplates(apiKey).catch(() => []),
          listPartnerGuardrails(apiKey).catch(() => null),
        ])

      setRules(rulesRes.items)
      setStats(statsRes)
      setEvents(eventsRes)
      setTemplates(templatesRes)
      setPartners(partnersRes)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load guardrails')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [apiKey])

  function resetForm() {
    setName('')
    setDescription('')
    setMode('pre_call')
    setRuleType('custom')
    setSeverity('medium')
    setLogic('')
    setEditingRule(null)
  }

  function openEdit(rule: GuardrailRuleResponse) {
    setEditingRule(rule)
    setName(rule.name)
    setDescription(rule.description || '')
    setMode(rule.mode || 'pre_call')
    setRuleType(rule.rule_type || 'custom')
    setSeverity(rule.severity || 'medium')
    setLogic(rule.logic || '')
    setShowModal(true)
  }

  function applyTemplate(tpl: GuardrailTemplate) {
    setName(tpl.name)
    setDescription(tpl.description || '')
    setMode(tpl.mode || 'pre_call')
    setSeverity('medium')
    setLogic(tpl.default_logic || '')
    setRuleType('template')
    setShowModal(true)
  }

  async function handleToggleStatus(rule: GuardrailRuleResponse) {
    if (!apiKey) return
    const nextStatus = rule.status === 'active' ? 'disabled' : 'active'
    try {
      await updateGuardrailRule(apiKey, rule.id, { status: nextStatus })
      toast.success(`Guardrail "${rule.name}" is now ${nextStatus}`)
      loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to update guardrail status')
    }
  }

  async function handleSaveRule(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !name.trim()) return
    setSaving(true)
    try {
      if (editingRule) {
        await updateGuardrailRule(apiKey, editingRule.id, {
          name: name.trim(),
          description: description.trim() || undefined,
          mode,
          severity,
          logic: logic.trim() || undefined,
        })
        toast.success('Guardrail rule updated')
      } else {
        await createGuardrailRule(apiKey, {
          name: name.trim(),
          description: description.trim() || undefined,
          mode,
          rule_type: ruleType,
          severity,
          logic: logic.trim() || undefined,
          status: 'active',
        })
        toast.success('Guardrail rule created and enforced')
      }
      setShowModal(false)
      resetForm()
      loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to save guardrail rule')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteRule(rule: GuardrailRuleResponse) {
    if (!apiKey || !confirm(`Delete guardrail rule "${rule.name}"?`)) return
    try {
      await deleteGuardrailRule(apiKey, rule.id)
      toast.success('Guardrail rule deleted')
      loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to delete guardrail rule')
    }
  }

  if (!apiKey) return <div className="p-8 text-slate-500">Sign in to view guardrails.</div>

  const filteredRules = rules.filter((r) => {
    const matchesSearch =
      r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (r.description && r.description.toLowerCase().includes(searchQuery.toLowerCase()))
    const matchesStatus = statusFilter === 'all' || r.status === statusFilter
    return matchesSearch && matchesStatus
  })

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6 md:p-10">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Guardrails &amp; Safety Engine
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Content safety, prompt-injection defense, PII redaction, partner moderation, and live enforcement telemetry.
          </p>
        </div>
        <button
          onClick={() => {
            resetForm()
            setShowModal(true)
          }}
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 transition"
        >
          <Plus className="h-4 w-4" />
          Add Guardrail Rule
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Evaluations</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
            {stats?.total_evaluations ?? '--'}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Block Rate</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
            {pct(stats?.block_rate)}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Avg Latency</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
            {stats?.avg_latency_ms != null ? `${stats.avg_latency_ms.toFixed(1)} ms` : '--'}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">False Positives</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
            {pct(stats?.false_positive_rate)}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Partner Checks</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
            {partners?.total ?? 0}
          </p>
        </div>
      </div>
      {/* Rules Controls & Filter Tabs */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          {['all', 'active', 'disabled', 'draft'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold capitalize transition ${
                statusFilter === st
                  ? 'bg-blue-600 text-white'
                  : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300'
              }`}
            >
              {st} ({st === 'all' ? rules.length : rules.filter((r) => r.status === st).length})
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search rules..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={`${inputCls} pl-9`}
          />
        </div>
      </div>

      {/* Compact Guardrail Cards Grid */}
      {loading ? (
        <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
          Loading guardrails...
        </div>
      ) : filteredRules.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500 dark:bg-slate-900/40">
          No guardrail rules found. Click &quot;Add Guardrail Rule&quot; to configure safety enforcements.
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filteredRules.map((rule) => {
            const isEnforced = rule.status === 'active'
            return (
              <div
                key={rule.id}
                className={`flex flex-col justify-between rounded-2xl border p-4 shadow-sm transition hover:shadow-md ${
                  isEnforced
                    ? 'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900'
                    : 'border-slate-200/60 bg-slate-50/60 dark:border-slate-800/60 dark:bg-slate-900/30 opacity-75'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`rounded-lg p-1.5 ${
                        isEnforced
                          ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400'
                          : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500'
                      }`}>
                        <ShieldCheck className="h-4 w-4" />
                      </span>
                      <h3 className="font-semibold text-slate-900 dark:text-white text-sm line-clamp-1">
                        {rule.name}
                      </h3>
                    </div>

                    <button
                      onClick={() => handleToggleStatus(rule)}
                      title={isEnforced ? 'Disable rule' : 'Enforce rule'}
                      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                        isEnforced ? 'bg-emerald-600' : 'bg-slate-300 dark:bg-slate-700'
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                          isEnforced ? 'translate-x-4' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </div>

                  <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 min-h-[32px]">
                    {rule.description || 'No description provided.'}
                  </p>

                  <div className="mt-3 flex flex-wrap items-center gap-1.5">
                    <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300 uppercase">
                      {rule.mode}
                    </span>
                    <span className={`rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase ${
                      severityColors[rule.severity] || severityColors.low
                    }`}>
                      {rule.severity}
                    </span>
                    <span className="rounded-md bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700 dark:bg-blue-950 dark:text-blue-300 uppercase">
                      {rule.rule_type}
                    </span>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between dark:border-slate-800 text-xs">
                  <span className="text-[11px] text-slate-400">
                    {isEnforced ? 'Enforced' : 'Paused'}
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => openEdit(rule)}
                      title="Edit rule"
                      className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => handleDeleteRule(rule)}
                      title="Delete rule"
                      className="rounded-md p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/40 dark:hover:text-rose-400"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Built-in Rule Templates */}
      {templates.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Default Safety Templates
            </h2>
            <span className="text-xs text-slate-500">{templates.length} available presets</span>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {templates.map((tpl) => (
              <div
                key={tpl.template_id}
                className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900"
              >
                <div>
                  <h4 className="font-semibold text-slate-900 dark:text-white text-xs">
                    {tpl.name}
                  </h4>
                  <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2">
                    {tpl.description}
                  </p>
                </div>
                <button
                  onClick={() => applyTemplate(tpl)}
                  className="mt-3 w-full rounded-lg border border-blue-200 bg-blue-50 px-2.5 py-1.5 text-[11px] font-semibold text-blue-700 hover:bg-blue-100 transition dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300"
                >
                  Apply Template
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Live Enforcement Events */}
      {events && events.items.length > 0 && (
        <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-800 dark:bg-slate-900/80">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
            Recent Enforcement Events
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 text-left font-medium text-slate-500 uppercase tracking-wide dark:bg-slate-800/60">
                <tr>
                  <th className="px-4 py-3">Rule Name</th>
                  <th className="px-4 py-3">Decision</th>
                  <th className="px-4 py-3">Model</th>
                  <th className="px-4 py-3">Latency</th>
                  <th className="px-4 py-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {events.items.map((ev) => (
                  <tr key={ev.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                      {ev.guardrail_name}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                        ev.decision === 'block'
                          ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                          : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                      }`}>
                        {ev.decision}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-500">{ev.model || '--'}</td>
                    <td className="px-4 py-3 text-slate-500">{ev.latency_ms.toFixed(1)} ms</td>
                    <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">
                      {new Date(ev.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ── Create / Edit Modal ────────────────────────────────────────────── */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-900 dark:border dark:border-slate-800">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                {editingRule ? 'Edit Guardrail Rule' : 'Create Guardrail Rule'}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSaveRule} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Rule Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Redact PII in System Prompt"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className={inputCls}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Description
                </label>
                <textarea
                  placeholder="What does this rule protect against?"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className={`${inputCls} min-h-16`}
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Enforcement Mode
                  </label>
                  <select
                    value={mode}
                    onChange={(e) => setMode(e.target.value)}
                    className={inputCls}
                  >
                    <option value="pre_call">Pre-call (Input Guard)</option>
                    <option value="post_call">Post-call (Output Filter)</option>
                    <option value="both">Both (Pre &amp; Post)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Severity
                  </label>
                  <select
                    value={severity}
                    onChange={(e) => setSeverity(e.target.value)}
                    className={inputCls}
                  >
                    <option value="critical">Critical (Hard Block)</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low (Audit Log)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Rule Pattern / Regex Logic (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. (regex|keyword|pattern)"
                  value={logic}
                  onChange={(e) => setLogic(e.target.value)}
                  className={inputCls}
                />
              </div>

              <div className="mt-6 flex justify-end gap-2 pt-4 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving || !name.trim()}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Saving...' : editingRule ? 'Update Rule' : 'Create & Enforce'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
