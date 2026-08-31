'use client'

import { useSession } from 'next-auth/react'
import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { toast } from 'sonner'
import { useRole } from '@/components/rbac/useRole'
import { Building2, Radio, Link2, Layers } from 'lucide-react'
import {
  listAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  listAlertHistory,
  emailAnalyticsReport,
  getApprovalsAlertFinopsPosture,
  getExceptionWorkflowsOrgPosture,
  getExceptionWorkflowsGatewayPosture,
  getGovernanceInternalPosture,
  getAlertRulesRuntimePosture,
} from '@/lib/api'
import type { AlertRule, AlertFiring, ApprovalsAlertFinopsPosture, ExceptionWorkflowsOrgPosture, ExceptionWorkflowsGatewayPosture, GovernanceInternalPosture, AlertRulesRuntimePosture } from '@/types/api'

const inputCls =
  'rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500'

export default function AlertRulesPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { canManageOrgSettings } = useRole()

  const [alertRules, setAlertRules] = useState<AlertRule[]>([])
  const [alertHistory, setAlertHistory] = useState<AlertFiring[]>([])
  const [finopsPosture, setFinopsPosture] = useState<ApprovalsAlertFinopsPosture | null>(null)
  const [orgPosture, setOrgPosture] = useState<ExceptionWorkflowsOrgPosture | null>(null)
  const [gatewayPosture, setGatewayPosture] = useState<ExceptionWorkflowsGatewayPosture | null>(null)
  const [govInternal, setGovInternal] = useState<GovernanceInternalPosture | null>(null)
  const [runtimePosture, setRuntimePosture] = useState<AlertRulesRuntimePosture | null>(null)
  const [newAlertName, setNewAlertName] = useState('')
  const [newAlertMetric, setNewAlertMetric] = useState('error_rate')
  const [newAlertOperator, setNewAlertOperator] = useState('gt')
  const [newAlertThreshold, setNewAlertThreshold] = useState('')
  const [newAlertWindow, setNewAlertWindow] = useState('60')
  const [newAlertEmailEnabled, setNewAlertEmailEnabled] = useState(false)
  const [creatingAlert, setCreatingAlert] = useState(false)
  const [sendingReport, setSendingReport] = useState(false)
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null)
  const [editAlertName, setEditAlertName] = useState('')
  const [editAlertMetric, setEditAlertMetric] = useState('error_rate')
  const [editAlertOperator, setEditAlertOperator] = useState('gt')
  const [editAlertThreshold, setEditAlertThreshold] = useState('')
  const [editAlertWindow, setEditAlertWindow] = useState('60')
  const [editAlertEmailEnabled, setEditAlertEmailEnabled] = useState(false)
  const [savingEdit, setSavingEdit] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return
    try {
      const [alertsData, historyData, posture, orgP, gwP, govI, rtP] = await Promise.all([
        listAlertRules(apiKey, true),
        listAlertHistory(apiKey, 10),
        getApprovalsAlertFinopsPosture(apiKey).catch(() => null),
        getExceptionWorkflowsOrgPosture(apiKey).catch(() => null),
        getExceptionWorkflowsGatewayPosture(apiKey).catch(() => null),
        getGovernanceInternalPosture(apiKey).catch(() => null),
        getAlertRulesRuntimePosture(apiKey).catch(() => null),
      ])
      setAlertRules(alertsData.items)
      setAlertHistory(historyData.items)
      setFinopsPosture(posture)
      setOrgPosture(orgP)
      setGatewayPosture(gwP)
      setGovInternal(govI)
      setRuntimePosture(rtP)
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

  function startEditing(rule: AlertRule) {
    setEditingRuleId(rule.id)
    setEditAlertName(rule.name)
    setEditAlertMetric(rule.metric)
    setEditAlertOperator(rule.operator)
    setEditAlertThreshold(String(rule.threshold))
    setEditAlertWindow(String(rule.window_minutes))
    setEditAlertEmailEnabled(rule.email_enabled)
  }

  function resetEditing() {
    setEditingRuleId(null)
    setEditAlertName('')
    setEditAlertMetric('error_rate')
    setEditAlertOperator('gt')
    setEditAlertThreshold('')
    setEditAlertWindow('60')
    setEditAlertEmailEnabled(false)
  }

  async function handleSaveEdit() {
    if (!apiKey || !editingRuleId || !editAlertName.trim() || !editAlertThreshold) return
    setSavingEdit(true)
    try {
      const updated = await updateAlertRule(apiKey, editingRuleId, {
        name: editAlertName.trim(),
        metric: editAlertMetric,
        operator: editAlertOperator,
        threshold: parseFloat(editAlertThreshold),
        window_minutes: parseInt(editAlertWindow, 10),
        email_enabled: editAlertEmailEnabled,
      })
      setAlertRules((prev) => prev.map((r) => (r.id === updated.id ? updated : r)))
      toast.success('Alert rule updated')
      resetEditing()
    } catch (err) {
      console.error(err)
      toast.error('Failed to update rule')
    } finally {
      setSavingEdit(false)
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
        <h1 className="text-2xl font-bold text-slate-950">Alert Rules</h1>
        <p className="mt-4 text-sm text-slate-500">Alert rule management is an organization-admin function.</p>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-950">Alert Rules</h1>
        <p className="mt-1 text-sm text-slate-600">Fire Slack notifications when a metric crosses a threshold. Evaluated every 5 minutes.</p>
      </div>

      {finopsPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 space-y-3">
          <h2 className="text-sm font-semibold text-emerald-900">FinOps Budget Context</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-emerald-700">{finopsPosture.approval_context.budget_increase_total}</p>
              <p className="text-xs text-emerald-600">Budget Increase Requests</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-emerald-700">{finopsPosture.budget_context.total_budgets}</p>
              <p className="text-xs text-emerald-600">Active Budgets</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-emerald-700">{finopsPosture.budget_context.breach_count_30d}</p>
              <p className="text-xs text-emerald-600">Breaches (30d)</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-emerald-700">{finopsPosture.alert_context.budget_alert_rules}</p>
              <p className="text-xs text-emerald-600">Budget Alert Rules</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-xs font-medium text-emerald-700">
            <Link href="/budgets" className="underline hover:text-emerald-900">Budgets</Link>
            <Link href="/budgets?detail=true" className="underline hover:text-emerald-900">Budget Detail</Link>
            <Link href="/approvals?status=pending" className="underline hover:text-emerald-900">Approvals</Link>
            <Link href="/chargeback" className="underline hover:text-emerald-900">Chargeback</Link>
          </div>
        </div>
      )}

      {/* Org & Access Scope */}
      {orgPosture && (
        <div className="rounded-2xl border border-blue-200 dark:border-blue-800 bg-blue-50/60 dark:bg-blue-950/40 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <h2 className="text-lg font-semibold text-blue-900 dark:text-blue-100">Org &amp; Access Scope</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Workspace Users</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.user_context.total_users}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Access Groups</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.access_group_context.total_groups}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Active Alert Rules</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.alert_context.active_alert_rules}</p>
              <p className="text-xs text-slate-500">{orgPosture.alert_context.alert_firings_30d} firings (30d)</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Active API Keys</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.api_key_context.total_keys}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/organization" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">Organization</Link>
            <Link href="/users" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">Users</Link>
            <Link href="/workspaces" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">Workspaces</Link>
            <Link href="/access-groups" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">Access Groups</Link>
            <Link href="/api-keys" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">API Keys</Link>
            <Link href="/mcp-registry" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">MCP Registry</Link>
          </div>
        </div>
      )}

      {/* Gateway & Observe Runtime */}
      {gatewayPosture && (
        <div className="rounded-2xl border border-violet-200 dark:border-violet-800 bg-violet-50/60 dark:bg-violet-950/40 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Radio className="h-5 w-5 text-violet-600 dark:text-violet-400" />
            <h2 className="text-lg font-semibold text-violet-900 dark:text-violet-100">Gateway &amp; Observe Runtime</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-violet-700 dark:text-violet-300">Gateway Routes</p>
              <p className="mt-1 text-2xl font-bold text-violet-900 dark:text-violet-50">{gatewayPosture.provider_context.total_routes}</p>
              <p className="text-xs text-slate-500">{gatewayPosture.provider_context.total_providers} providers</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-violet-700 dark:text-violet-300">Guardrails</p>
              <p className="mt-1 text-2xl font-bold text-violet-900 dark:text-violet-50">{gatewayPosture.guardrail_context.total_guardrails}</p>
              <p className="text-xs text-slate-500">{gatewayPosture.guardrail_context.guardrail_events_30d} events (30d)</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-violet-700 dark:text-violet-300">Tool Calls (30d)</p>
              <p className="mt-1 text-2xl font-bold text-violet-900 dark:text-violet-50">{gatewayPosture.run_context.tool_runs_30d}</p>
              <p className="text-xs text-slate-500">{gatewayPosture.run_context.total_runs_30d} total runs</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-violet-700 dark:text-violet-300">Alert Firings (30d)</p>
              <p className="mt-1 text-2xl font-bold text-violet-900 dark:text-violet-50">{gatewayPosture.monitoring_context.alert_firings_30d}</p>
              <p className="text-xs text-slate-500">{gatewayPosture.monitoring_context.total_alert_rules} active rules</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/gateway" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Gateway</Link>
            <Link href="/guardrails" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Guardrails</Link>
            <Link href="/runs" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Runs</Link>
            <Link href="/request-explorer" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Request Explorer</Link>
            <Link href="/monitoring" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Monitoring</Link>
          </div>
        </div>
      )}

      {govInternal && (
        <div className="rounded-2xl border border-rose-200 dark:border-rose-800 bg-rose-50/60 dark:bg-rose-950/30 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-rose-600 dark:text-rose-400" />
            <h2 className="text-lg font-semibold text-rose-900 dark:text-rose-100">Governance Cohesion</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Registered Tools</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.tool_registry_context.total_tools}</p>
              <p className="text-xs text-slate-500">{govInternal.tool_registry_context.enforced_tools} enforced</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Active Policies</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.tool_policies_context.active_policies}</p>
              <p className="text-xs text-slate-500">{govInternal.tool_policies_context.total_policies} total</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Pending Approvals</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.approvals_context.pending_approvals}</p>
              <p className="text-xs text-slate-500">{govInternal.approvals_context.total_approvals_30d} total (30d)</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Security Events (30d)</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.security_context.security_events_30d}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/tool-registry" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tool Registry</Link>
            <Link href="/tool-policies" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tool Policies</Link>
            <Link href="/approvals" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Approvals</Link>
            <Link href="/data-capture" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Data Capture</Link>
            <Link href="/security" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Security</Link>
            <Link href="/audit" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Audit Log</Link>
            <Link href="/governance-pack" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Governance Pack</Link>
            <Link href="/tags" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tags</Link>
          </div>
        </div>
      )}

      {runtimePosture && (
        <div className="rounded-2xl border border-cyan-200 dark:border-cyan-800 bg-cyan-50/60 dark:bg-cyan-950/40 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-cyan-600 dark:text-cyan-400" />
            <h2 className="text-lg font-semibold text-cyan-900 dark:text-cyan-100">Runtime Scope &amp; Evidence</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Alert Firings 30d</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.ops_context.alert_firings_30d}</p>
              <p className="text-xs text-slate-500">{runtimePosture.ops_context.active_alert_rules} active rules</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Rate-Limited Routes</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.gateway_runtime.rate_limited_routes}</p>
              <p className="text-xs text-slate-500">{runtimePosture.gateway_runtime.model_routes} total routes</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Chargeback Rules</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.finops_context.chargeback_rules}</p>
              <p className="text-xs text-slate-500">{runtimePosture.finops_context.active_budgets} active budgets</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Runs 30d</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.observe_evidence.runs_30d}</p>
              <p className="text-xs text-slate-500">{runtimePosture.observe_evidence.provider_calls_30d} provider calls</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/gateway" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Model Gateway</Link>
            <Link href="/guardrails" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Guardrails</Link>
            <Link href="/rate-limits" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Rate Limits</Link>
            <Link href="/runs" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Runs</Link>
            <Link href="/monitoring" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Monitoring</Link>
            <Link href="/chargeback" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Chargeback</Link>
            <Link href="/budgets" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Budgets</Link>
          </div>
        </div>
      )}

      <form onSubmit={handleCreateAlert} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <input className={inputCls} placeholder="Rule name (e.g. High error rate)" value={newAlertName} onChange={(e) => setNewAlertName(e.target.value)} required />
        <select className={inputCls} value={newAlertMetric} onChange={(e) => setNewAlertMetric(e.target.value)}>
          <option value="error_rate">Error Rate</option>
          <option value="p95_latency">P95 Latency (ms)</option>
          <option value="avg_score">Avg Score</option>
          <option value="spend_velocity">Spend Velocity ($)</option>
          <option value="model_availability">Model Availability (%)</option>
          <option value="gateway_overhead_p95">Gateway Overhead P95 (ms)</option>
          <option value="budget_utilization">Budget Utilization (%)</option>
          <option value="budget_breach_count">Budget Breach Count</option>
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
          <span className="text-sm text-slate-600">min window</span>
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={newAlertEmailEnabled}
            onChange={(e) => setNewAlertEmailEnabled(e.target.checked)}
            className="rounded border-slate-300"
          />
          Email workspace admins
        </label>
        <button type="submit" disabled={creatingAlert} className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
          {creatingAlert ? 'Creating…' : 'Add Rule'}
        </button>
      </form>

      {alertRules.length === 0 ? (
        <p className="text-sm text-slate-500">No alert rules yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-300 bg-white/90 shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-600">
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
            <tbody className="divide-y divide-slate-200">
              {alertRules.map((rule) => (
                <tr key={rule.id} className="text-slate-800 hover:bg-blue-50/45">
                  <td className="px-4 py-2 font-medium text-slate-950">{rule.name}</td>
                  <td className="px-4 py-2 font-mono text-xs text-slate-700">{rule.metric}</td>
                  <td className="px-4 py-2 text-xs text-slate-700">{rule.operator === 'gt' ? '>' : '<'} {rule.threshold}</td>
                  <td className="px-4 py-2 text-xs text-slate-600">{rule.window_minutes}m</td>
                  <td className="px-4 py-2">
                    <span className={`text-xs ${rule.email_enabled ? 'text-blue-700' : 'text-slate-500'}`}>
                      {rule.email_enabled ? 'On' : 'Off'}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <button onClick={() => handleToggleAlert(rule)} className={`rounded px-2 py-0.5 text-xs font-medium ${rule.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'}`}>
                      {rule.is_active ? 'Active' : 'Paused'}
                    </button>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-3">
                      <button onClick={() => startEditing(rule)} className="text-xs text-blue-600 hover:underline">Edit</button>
                      <button onClick={() => handleDeleteAlert(rule.id)} className="text-xs text-red-500 hover:underline">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {alertHistory.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-medium text-slate-800">Recent Firings</h3>
          <div className="overflow-x-auto rounded-xl border border-slate-300 bg-white/90 shadow-sm">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 uppercase text-slate-600">
                <tr>
                  <th className="px-3 py-2 text-left">Rule</th>
                  <th className="px-3 py-2 text-left">Value</th>
                  <th className="px-3 py-2 text-left">Fired At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {alertHistory.map((f) => (
                  <tr key={f.id} className="text-slate-800 hover:bg-blue-50/45">
                    <td className="px-3 py-2 font-medium text-slate-950">{f.rule_name}</td>
                    <td className="px-3 py-2 font-mono text-slate-700">{parseFloat(f.metric_value).toFixed(4)}</td>
                    <td className="px-3 py-2 text-slate-600">{new Date(f.fired_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Email Reports card */}
      <div className="rounded-xl border border-slate-300 bg-white/90 p-5 shadow-sm">
        <h3 className="mb-1 text-sm font-semibold text-slate-950">Email Reports</h3>
        <p className="mb-4 text-xs text-slate-600">
          Scheduled analytics reports are managed by Platform Admins in Settings {'->'} Email. Org admins can still send an on-demand
          workspace report from here.
        </p>
        <button
          onClick={handleSendReport}
          disabled={sendingReport}
          className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {sendingReport ? 'Sending…' : 'Send Report Now'}
        </button>
      </div>
      {editingRuleId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-xl space-y-4 rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-900">
            <div>
              <h2 className="text-lg font-semibold text-slate-950 dark:text-white">Edit alert rule</h2>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                Update thresholds and delivery settings without leaving the governance workflow.
              </p>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <input className={inputCls} value={editAlertName} onChange={(e) => setEditAlertName(e.target.value)} />
              <select className={inputCls} value={editAlertMetric} onChange={(e) => setEditAlertMetric(e.target.value)}>
                <option value="error_rate">Error Rate</option>
                <option value="p95_latency">P95 Latency (ms)</option>
                <option value="avg_score">Avg Score</option>
                <option value="spend_velocity">Spend Velocity ($)</option>
                <option value="model_availability">Model Availability (%)</option>
                <option value="gateway_overhead_p95">Gateway Overhead P95 (ms)</option>
                <option value="budget_utilization">Budget Utilization (%)</option>
                <option value="budget_breach_count">Budget Breach Count</option>
              </select>
              <div className="flex gap-2">
                <select className={`${inputCls} w-24`} value={editAlertOperator} onChange={(e) => setEditAlertOperator(e.target.value)}>
                  <option value="gt">&gt; (above)</option>
                  <option value="lt">&lt; (below)</option>
                </select>
                <input className={`${inputCls} flex-1`} type="number" step="any" min="0" value={editAlertThreshold} onChange={(e) => setEditAlertThreshold(e.target.value)} />
              </div>
              <div className="flex items-center gap-2">
                <input className={`${inputCls} w-24`} type="number" min="5" max="1440" value={editAlertWindow} onChange={(e) => setEditAlertWindow(e.target.value)} />
                <span className="text-sm text-slate-600">min window</span>
              </div>
              <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={editAlertEmailEnabled} onChange={(e) => setEditAlertEmailEnabled(e.target.checked)} className="rounded border-slate-300" />
                Email workspace admins
              </label>
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={resetEditing} className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800">
                Cancel
              </button>
              <button onClick={handleSaveEdit} disabled={savingEdit} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
                {savingEdit ? 'Saving...' : 'Save changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
