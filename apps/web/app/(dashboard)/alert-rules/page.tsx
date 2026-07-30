'use client'

import { useSession } from 'next-auth/react'
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import { useRole } from '@/components/rbac/useRole'
import {
  listAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  listAlertHistory,
  emailAnalyticsReport,
} from '@/lib/api'
import type { AlertRule, AlertFiring } from '@/types/api'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

export default function AlertRulesPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { canManageOrgSettings } = useRole()

  const [alertRules, setAlertRules] = useState<AlertRule[]>([])
  const [alertHistory, setAlertHistory] = useState<AlertFiring[]>([])
  const [newAlertName, setNewAlertName] = useState('')
  const [newAlertMetric, setNewAlertMetric] = useState('error_rate')
  const [newAlertOperator, setNewAlertOperator] = useState('gt')
  const [newAlertThreshold, setNewAlertThreshold] = useState('')
  const [newAlertWindow, setNewAlertWindow] = useState('60')
  const [newAlertEmailEnabled, setNewAlertEmailEnabled] = useState(false)
  const [creatingAlert, setCreatingAlert] = useState(false)
  const [sendingReport, setSendingReport] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return
    try {
      const [alertsData, historyData] = await Promise.all([
        listAlertRules(apiKey, true),
        listAlertHistory(apiKey, 10),
      ])
      setAlertRules(alertsData.items)
      setAlertHistory(historyData.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load alert rules')
    }
  }, [apiKey, canManageOrgSettings])

  useEffect(() => { load() }, [load])

  async function handleCreateAlert(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !newAlertName.trim() || !newAlertThreshold) return
    setCreatingAlert(true)
    try {
      const rule = await createAlertRule(apiKey, {
        name: newAlertName.trim(),
        metric: newAlertMetric,
        operator: newAlertOperator,
        threshold: parseFloat(newAlertThreshold),
        window_minutes: parseInt(newAlertWindow, 10),
        email_enabled: newAlertEmailEnabled,
      })
      setAlertRules((prev) => [rule, ...prev])
      setNewAlertName('')
      setNewAlertThreshold('')
      setNewAlertEmailEnabled(false)
      toast.success('Alert rule created')
    } catch (err) {
      console.error(err)
      toast.error('Failed to create alert rule')
    } finally {
      setCreatingAlert(false)
    }
  }

  async function handleToggleAlert(rule: AlertRule) {
    if (!apiKey) return
    try {
      const updated = await updateAlertRule(apiKey, rule.id, { is_active: !rule.is_active })
      setAlertRules((prev) => prev.map((r) => (r.id === rule.id ? updated : r)))
      toast.success(updated.is_active ? 'Rule enabled' : 'Rule disabled')
    } catch (err) {
      console.error(err)
      toast.error('Failed to update rule')
    }
  }

  async function handleDeleteAlert(ruleId: string) {
    if (!apiKey || !confirm('Delete this alert rule?')) return
    try {
      await deleteAlertRule(apiKey, ruleId)
      setAlertRules((prev) => prev.filter((r) => r.id !== ruleId))
      toast.success('Alert rule deleted')
    } catch (err) {
      console.error(err)
      toast.error('Failed to delete rule')
    }
  }

  async function handleSendReport() {
    if (!apiKey) return
    setSendingReport(true)
    try {
      const result = await emailAnalyticsReport(apiKey, 7)
      toast.success(`Report sent to ${result.recipients} recipient${result.recipients !== 1 ? 's' : ''}`)
    } catch (err) {
      console.error(err)
      toast.error('Failed to send report')
    } finally {
      setSendingReport(false)
    }
  }

  if (!canManageOrgSettings) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Alert Rules</h1>
        <p className="mt-4 text-sm text-slate-500">Alert rule management is an organization-admin function.</p>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Alert Rules</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Fire Slack notifications when a metric crosses a threshold. Evaluated every 5 minutes.</p>
      </div>

      <form onSubmit={handleCreateAlert} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <input className={inputCls} placeholder="Rule name (e.g. High error rate)" value={newAlertName} onChange={(e) => setNewAlertName(e.target.value)} required />
        <select className={inputCls} value={newAlertMetric} onChange={(e) => setNewAlertMetric(e.target.value)}>
          <option value="error_rate">Error Rate</option>
          <option value="p95_latency">P95 Latency (ms)</option>
          <option value="avg_score">Avg Score</option>
          <option value="spend_velocity">Spend Velocity ($)</option>
        </select>
        <div className="flex gap-2">
          <select className={`${inputCls} w-24`} value={newAlertOperator} onChange={(e) => setNewAlertOperator(e.target.value)}>
            <option value="gt">&gt; (above)</option>
            <option value="lt">&lt; (below)</option>
          </select>
          <input className={`${inputCls} flex-1`} type="number" step="any" min="0" placeholder="Threshold" value={newAlertThreshold} onChange={(e) => setNewAlertThreshold(e.target.value)} required />
        </div>
        <div className="flex items-center gap-2">
          <input className={`${inputCls} w-24`} type="number" min="5" max="1440" placeholder="60" value={newAlertWindow} onChange={(e) => setNewAlertWindow(e.target.value)} />
          <span className="text-sm text-gray-500 dark:text-gray-400">min window</span>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 cursor-pointer">
          <input
            type="checkbox"
            checked={newAlertEmailEnabled}
            onChange={(e) => setNewAlertEmailEnabled(e.target.checked)}
            className="rounded border-gray-300 dark:border-gray-600"
          />
          Email workspace admins
        </label>
        <button type="submit" disabled={creatingAlert} className="rounded bg-indigo-600 px-4 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
          {creatingAlert ? 'Creating…' : 'Add Rule'}
        </button>
      </form>

      {alertRules.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-gray-500">No alert rules yet.</p>
      ) : (
        <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
              <tr>
                <th className="px-4 py-2 text-left">Name</th>
                <th className="px-4 py-2 text-left">Metric</th>
                <th className="px-4 py-2 text-left">Condition</th>
                <th className="px-4 py-2 text-left">Window</th>
                <th className="px-4 py-2 text-left">Email</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {alertRules.map((rule) => (
                <tr key={rule.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                  <td className="px-4 py-2 font-medium dark:text-gray-200">{rule.name}</td>
                  <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">{rule.metric}</td>
                  <td className="px-4 py-2 text-xs dark:text-gray-300">{rule.operator === 'gt' ? '>' : '<'} {rule.threshold}</td>
                  <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">{rule.window_minutes}m</td>
                  <td className="px-4 py-2">
                    <span className={`text-xs ${rule.email_enabled ? 'text-violet-600 dark:text-violet-400' : 'text-gray-400 dark:text-gray-600'}`}>
                      {rule.email_enabled ? 'On' : 'Off'}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <button onClick={() => handleToggleAlert(rule)} className={`rounded px-2 py-0.5 text-xs font-medium ${rule.is_active ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'}`}>
                      {rule.is_active ? 'Active' : 'Paused'}
                    </button>
                  </td>
                  <td className="px-4 py-2">
                    <button onClick={() => handleDeleteAlert(rule.id)} className="text-xs text-red-500 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {alertHistory.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">Recent Firings</h3>
          <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 uppercase text-gray-400 dark:bg-gray-800">
                <tr>
                  <th className="px-3 py-2 text-left">Rule</th>
                  <th className="px-3 py-2 text-left">Value</th>
                  <th className="px-3 py-2 text-left">Fired At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {alertHistory.map((f) => (
                  <tr key={f.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-3 py-2 font-medium dark:text-gray-200">{f.rule_name}</td>
                    <td className="px-3 py-2 font-mono dark:text-gray-300">{parseFloat(f.metric_value).toFixed(4)}</td>
                    <td className="px-3 py-2 text-gray-500 dark:text-gray-400">{new Date(f.fired_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Email Reports card */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5">
        <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-1">Email Reports</h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
          Weekly analytics reports (last 7 days) are automatically emailed every Monday at 07:00 UTC to all workspace admins.
          You can also send a report on demand.
        </p>
        <button
          onClick={handleSendReport}
          disabled={sendingReport}
          className="rounded bg-violet-600 px-4 py-1.5 text-sm text-white hover:bg-violet-700 disabled:opacity-50"
        >
          {sendingReport ? 'Sending…' : 'Send Report Now'}
        </button>
      </div>
    </div>
  )
}
