'use client'

import { useState, useEffect, useCallback } from 'react'
import { Trash2, Play, Eye, Plus, ToggleLeft, ToggleRight, AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'
import {
  listRetentionPolicies,
  createRetentionPolicy,
  updateRetentionPolicy,
  deleteRetentionPolicy,
  purgeRetention,
} from '@/lib/api'
import type {
  RetentionPolicy,
  RetentionResourceType,
  RetentionActionType,
  RetentionScopeType,
} from '@/types/api'

const RESOURCE_TYPES: { value: RetentionResourceType; label: string; desc: string }[] = [
  { value: 'runs', label: 'Agent Runs', desc: 'Cascades to spans, provider calls, and tool calls' },
  { value: 'spans', label: 'Spans', desc: 'Span records only; agent runs are preserved' },
  { value: 'payloads', label: 'Payloads (scrub)', desc: 'Remove messages/response from span metadata' },
  { value: 'provider_calls', label: 'Provider Calls', desc: 'LLM call records and token counts' },
]

const RESOURCE_ACTIONS: Record<RetentionResourceType, RetentionActionType[]> = {
  runs: ['delete'],
  spans: ['delete', 'scrub'],
  payloads: ['scrub'],
  provider_calls: ['delete'],
}

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-teal-500 dark:focus:ring-teal-400'

export default function RetentionTab({ apiKey }: { apiKey: string }) {
  const [policies, setPolicies] = useState<RetentionPolicy[]>([])
  const [loading, setLoading] = useState(false)

  // Create form state
  const [creating, setCreating] = useState(false)
  const [formResource, setFormResource] = useState<RetentionResourceType>('runs')
  const [formAction, setFormAction] = useState<RetentionActionType>('delete')
  const [formScope, setFormScope] = useState<RetentionScopeType>('workspace')
  const [formScopeValue, setFormScopeValue] = useState('')
  const [formAgeDays, setFormAgeDays] = useState('90')
  const [showForm, setShowForm] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const res = await listRetentionPolicies(apiKey)
      setPolicies(res.items)
    } catch {
      toast.error('Failed to load retention policies')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { load() }, [load])

  // Auto-select valid action when resource type changes
  const handleResourceChange = (r: RetentionResourceType) => {
    setFormResource(r)
    const validActions = RESOURCE_ACTIONS[r]
    if (!validActions.includes(formAction)) {
      setFormAction(validActions[0])
    }
  }

  async function handleCreate() {
    if (!apiKey) return
    setCreating(true)
    try {
      await createRetentionPolicy(apiKey, {
        resource_type: formResource,
        action: formAction,
        scope: formScope,
        scope_value: formScope === 'end_user' ? formScopeValue || null : null,
        max_age_days: formScope === 'workspace' ? parseInt(formAgeDays, 10) || null : null,
      })
      toast.success('Retention policy created')
      setShowForm(false)
      setFormResource('runs')
      setFormAction('delete')
      setFormScope('workspace')
      setFormScopeValue('')
      setFormAgeDays('90')
      await load()
    } catch (e: unknown) {
      toast.error((e as Error)?.message ?? 'Failed to create policy')
    } finally {
      setCreating(false)
    }
  }

  async function handleToggle(policy: RetentionPolicy) {
    try {
      await updateRetentionPolicy(apiKey, policy.id, { is_active: !policy.is_active })
      toast.success(`Policy ${policy.is_active ? 'disabled' : 'enabled'}`)
      await load()
    } catch {
      toast.error('Failed to update policy')
    }
  }

  async function handleDelete(policy: RetentionPolicy) {
    if (!confirm(`Delete this ${policy.resource_type} retention policy? This cannot be undone.`)) return
    try {
      await deleteRetentionPolicy(apiKey, policy.id)
      toast.success('Policy deleted')
      await load()
    } catch {
      toast.error('Failed to delete policy')
    }
  }

  async function handlePurge(policy: RetentionPolicy, dryRun: boolean) {
    try {
      const result = await purgeRetention(apiKey, { policy_id: policy.id, dry_run: dryRun })
      if (dryRun) {
        toast.info(`Dry run: ${result.affected_rows} row(s) would be affected`)
      } else {
        toast.success(`Purged ${result.affected_rows} row(s)`)
        await load()
      }
    } catch {
      toast.error('Purge failed')
    }
  }

  function policyDesc(p: RetentionPolicy): string {
    if (p.scope === 'end_user') {
      return `${p.resource_type} • ${p.action} • user: ${p.scope_value}`
    }
    return `${p.resource_type} • ${p.action} • older than ${p.max_age_days}d`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Data Retention Policies</h3>
          <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
            Automatically purge or scrub data on a schedule. GDPR end-user erasure is also supported.
          </p>
        </div>
        <button
          onClick={() => setShowForm(v => !v)}
          className="flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-teal-700"
        >
          <Plus className="h-3.5 w-3.5" />
          New Policy
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-4 space-y-4">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white">Create Retention Policy</h4>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Resource Type</label>
              <select
                value={formResource}
                onChange={e => handleResourceChange(e.target.value as RetentionResourceType)}
                className={inputCls + ' w-full'}
              >
                {RESOURCE_TYPES.map(r => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                {RESOURCE_TYPES.find(r => r.value === formResource)?.desc}
              </p>
            </div>

            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Action</label>
              <select
                value={formAction}
                onChange={e => setFormAction(e.target.value as RetentionActionType)}
                className={inputCls + ' w-full'}
              >
                {RESOURCE_ACTIONS[formResource].map(a => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Scope</label>
              <select
                value={formScope}
                onChange={e => setFormScope(e.target.value as RetentionScopeType)}
                className={inputCls + ' w-full'}
              >
                <option value="workspace">Workspace (age-based)</option>
                <option value="end_user">End User (GDPR erasure)</option>
              </select>
            </div>

            {formScope === 'workspace' ? (
              <div>
                <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Retain for (days)</label>
                <input
                  type="number"
                  min={1}
                  max={3650}
                  value={formAgeDays}
                  onChange={e => setFormAgeDays(e.target.value)}
                  className={inputCls + ' w-full'}
                />
              </div>
            ) : (
              <div>
                <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">End User ID</label>
                <input
                  type="text"
                  placeholder="user-123"
                  value={formScopeValue}
                  onChange={e => setFormScopeValue(e.target.value)}
                  className={inputCls + ' w-full'}
                />
              </div>
            )}
          </div>

          {formScope === 'workspace' && (
            <div className="flex items-center gap-2 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 px-3 py-2">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" />
              <p className="text-xs text-amber-700 dark:text-amber-400">
                Data older than {formAgeDays || '?'} days will be permanently deleted by the nightly worker.
              </p>
            </div>
          )}

          <div className="flex gap-2 justify-end">
            <button
              onClick={() => setShowForm(false)}
              className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={creating}
              className="rounded-lg bg-teal-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50"
            >
              {creating ? 'Creating…' : 'Create Policy'}
            </button>
          </div>
        </div>
      )}

      {/* Policy list */}
      {loading && policies.length === 0 ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-14 rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse" />
          ))}
        </div>
      ) : policies.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-200 dark:border-gray-700 py-10 text-center">
          <Trash2 className="mx-auto h-8 w-8 text-gray-300 dark:text-gray-600 mb-2" />
          <p className="text-sm text-gray-500 dark:text-gray-400">No retention policies yet</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            Create a policy to automatically age-out old data or erase end-user records
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50/60 dark:bg-gray-800/40">
                <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Policy</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Last Run</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Purged</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Status</th>
                <th className="px-4 py-2.5 text-right text-xs font-medium text-gray-500 dark:text-gray-400">Actions</th>
              </tr>
            </thead>
            <tbody>
              {policies.map(p => (
                <tr key={p.id} className="border-b border-gray-100 dark:border-gray-800 last:border-0 hover:bg-gray-50/60 dark:hover:bg-gray-800/30">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900 dark:text-white text-xs font-mono">
                      {policyDesc(p)}
                    </div>
                    <div className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                      {p.scope === 'workspace' ? 'Nightly schedule' : 'GDPR end-user erasure'}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400">
                    {p.last_run_at ? new Date(p.last_run_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400">
                    {p.last_purged_count !== null ? p.last_purged_count.toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleToggle(p)}
                      className="flex items-center gap-1 text-xs"
                      title={p.is_active ? 'Click to disable' : 'Click to enable'}
                    >
                      {p.is_active ? (
                        <><ToggleRight className="h-4 w-4 text-teal-600" /><span className="text-teal-700 dark:text-teal-400">Active</span></>
                      ) : (
                        <><ToggleLeft className="h-4 w-4 text-gray-400" /><span className="text-gray-500">Inactive</span></>
                      )}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => handlePurge(p, true)}
                        title="Dry run — count without deleting"
                        className="rounded p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20"
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => handlePurge(p, false)}
                        title="Run purge now"
                        className="rounded p-1 text-gray-400 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20"
                      >
                        <Play className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(p)}
                        title="Delete policy"
                        className="rounded p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
