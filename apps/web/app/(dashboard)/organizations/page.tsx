'use client'

import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  LayoutGrid,
  MoreHorizontal,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  UsersRound,
  X,
} from 'lucide-react'
import Link from 'next/link'
import { useRole } from '@/components/rbac/useRole'
import {
  createOrganization,
  deletePlatformOrganization,
  getBudgetControlPlatformPosture,
  getPlatformAdminObservePosture,
  getPlatformLifecyclePosture,
  listPlatformOrganizations,
  updatePlatformOrganization,
} from '@/lib/api'
import type { BudgetControlPlatformPosture, PlatformAdminObservePosture, PlatformLifecyclePosture, TenantResponse, TenantStatus } from '@/types/api'

const inputCls =
  'rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 px-3 py-1.5 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500'
const TABLE_HEAD =
  'px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400'

type SessionShape = {
  apiKey?: string
  tenantId?: string
}

function StatusBadge({ status }: { status: TenantStatus }) {
  const styles: Record<TenantStatus, string> = {
    active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
    suspended: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
    archived: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${styles[status]}`}>
      {status}
    </span>
  )
}

function OrgIcon() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-100 text-violet-600 dark:bg-violet-950 dark:text-violet-300">
      <Building2 className="h-4 w-4" />
    </div>
  )
}

export default function OrganizationsPage() {
  const { data: session } = useSession()
  const { isPlatformAdmin } = useRole()
  const apiKey = (session as SessionShape | null)?.apiKey ?? ''
  const currentTenantId = (session as SessionShape | null)?.tenantId ?? ''

  const [organizations, setOrganizations] = useState<TenantResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [editing, setEditing] = useState<TenantResponse | null>(null)
  const [deleting, setDeleting] = useState<TenantResponse | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  const [orgName, setOrgName] = useState('')
  const [orgAdminEmail, setOrgAdminEmail] = useState('')
  const [orgAdminPassword, setOrgAdminPassword] = useState('ChangeMe123!')
  const [orgAdminName, setOrgAdminName] = useState('')
  const [skipVerification, setSkipVerification] = useState(true)

  const [editName, setEditName] = useState('')
  const [editPlan, setEditPlan] = useState('free')
  const [editStatus, setEditStatus] = useState<TenantStatus>('active')
  const [deleteConfirmation, setDeleteConfirmation] = useState('')
  const [budgetPlatformPosture, setBudgetPlatformPosture] = useState<BudgetControlPlatformPosture | null>(null)
  const [lifecyclePosture, setLifecyclePosture] = useState<PlatformLifecyclePosture | null>(null)
  const [observePosture, setObservePosture] = useState<PlatformAdminObservePosture | null>(null)

  const load = useCallback(async () => {
    if (!apiKey || !isPlatformAdmin) {
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      setOrganizations(await listPlatformOrganizations(apiKey))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load organizations')
    } finally {
      setLoading(false)
    }
  }, [apiKey, isPlatformAdmin])

  useEffect(() => {
    load()
    if (apiKey) {
      getBudgetControlPlatformPosture(apiKey).then(setBudgetPlatformPosture).catch(() => {})
      getPlatformLifecyclePosture(apiKey).then(setLifecyclePosture).catch(() => {})
      getPlatformAdminObservePosture(apiKey).then(setObservePosture).catch(() => {})
    }
  }, [load, apiKey])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return organizations
    return organizations.filter((org) => org.name.toLowerCase().includes(q) || org.plan.toLowerCase().includes(q))
  }, [organizations, search])

  function openEdit(org: TenantResponse) {
    setEditing(org)
    setEditName(org.name)
    setEditPlan(org.plan)
    setEditStatus(org.status)
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    if (!orgName.trim() || !orgAdminEmail.trim() || !orgAdminPassword.trim()) return
    setBusyId('create')
    try {
      await createOrganization(apiKey, {
        name: orgName.trim(),
        admin_email: orgAdminEmail.trim(),
        admin_password: orgAdminPassword,
        admin_full_name: orgAdminName.trim() || null,
        skip_verification: skipVerification,
      })
      setOrganizations(await listPlatformOrganizations(apiKey))
      setShowCreate(false)
      setOrgName('')
      setOrgAdminEmail('')
      setOrgAdminPassword('ChangeMe123!')
      setOrgAdminName('')
      setSkipVerification(true)
      toast.success('Organization created')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create organization')
    } finally {
      setBusyId(null)
    }
  }

  async function handleSaveEdit(e: FormEvent) {
    e.preventDefault()
    if (!editing) return
    const statusLocked = editing.is_default || editing.id === currentTenantId
    setBusyId(editing.id)
    try {
      const updated = await updatePlatformOrganization(apiKey, editing.id, {
        name: editName.trim(),
        plan: editPlan,
        ...(statusLocked ? {} : { status: editStatus }),
      })
      setOrganizations((prev) => prev.map((org) => (org.id === updated.id ? updated : org)))
      setEditing(null)
      toast.success('Organization updated')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update organization')
    } finally {
      setBusyId(null)
    }
  }

  async function handleStatus(org: TenantResponse, status: TenantStatus) {
    if (status !== 'active' && (org.is_default || org.id === currentTenantId)) {
      toast.error('Default or current organization cannot be suspended or archived')
      return
    }
    setBusyId(org.id)
    try {
      const updated = await updatePlatformOrganization(apiKey, org.id, { status })
      setOrganizations((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
      toast.success(`Organization ${status}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update organization')
    } finally {
      setBusyId(null)
    }
  }

  async function handleDelete(e: FormEvent) {
    e.preventDefault()
    if (!deleting || deleteConfirmation !== deleting.name) return
    setBusyId(deleting.id)
    try {
      await deletePlatformOrganization(apiKey, deleting.id, deleteConfirmation)
      setOrganizations((prev) => prev.filter((org) => org.id !== deleting.id))
      setDeleting(null)
      setDeleteConfirmation('')
      toast.success('Organization deleted')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete organization')
    } finally {
      setBusyId(null)
    }
  }

  if (!isPlatformAdmin) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Organizations</h1>
        <p className="mt-4 text-sm text-slate-500">Organization lifecycle is a platform-admin function.</p>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Organizations</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Platform-wide lifecycle view of organizations, workspaces, and membership.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white hover:bg-violet-700"
          >
            <Plus className="h-4 w-4" /> New Organization
          </button>
          <button onClick={load} className="rounded-lg border border-slate-300 p-2 text-slate-500 hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-800">
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {budgetPlatformPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Budget Control — Platform Posture</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Total Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetPlatformPosture.platform_totals.total_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">30d Spend</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">${budgetPlatformPosture.spend_context.total_spend_30d.toFixed(2)}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Overrides</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetPlatformPosture.override_context.active_overrides}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Breached</p>
              <p className={`mt-1 text-lg font-semibold ${budgetPlatformPosture.platform_totals.total_breaches > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{budgetPlatformPosture.platform_totals.total_breaches}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
            <Link href="/budgets" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
            <Link href="/budgets?scope=feature_tag" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Feature Budgets</Link>
            <Link href="/analytics?tab=economics" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Economics</Link>
            <Link href="/settings" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Platform Settings</Link>
          </div>
        </div>
      )}

      {lifecyclePosture && (
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">FinOps Lifecycle</p>
            <div className="mt-3 grid gap-3 grid-cols-2">
              <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Billing Periods</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{lifecyclePosture.finops_context.billing_periods}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Active Periods</p>
                <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">{lifecyclePosture.finops_context.active_billing_periods}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Chargeback Rules</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{lifecyclePosture.finops_context.chargeback_rules}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Ledger Snapshots</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{lifecyclePosture.finops_context.ledger_snapshots}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
              <Link href="/billing" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Billing Periods</Link>
              <Link href="/chargeback" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Chargeback</Link>
              <Link href="/settings?tab=compliance" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Ledger</Link>
            </div>
          </div>

          <div className="rounded-2xl border border-violet-200 bg-violet-50/50 p-5 shadow-sm dark:border-violet-900 dark:bg-violet-950/30">
            <p className="text-xs font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400">Gateway Readiness</p>
            <div className="mt-3 grid gap-3 grid-cols-2">
              <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Gateway Routes</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{lifecyclePosture.gateway_context.gateway_routes}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Providers</p>
                <p className="mt-1 text-lg font-semibold text-violet-600 dark:text-violet-400">{lifecyclePosture.gateway_context.distinct_providers}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3 col-span-2">
                <p className="text-xs text-slate-500 dark:text-slate-400">Guardrail Rules</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{lifecyclePosture.gateway_context.guardrail_rules}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-violet-200 dark:border-violet-800">
              <Link href="/gateway" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Model Gateway</Link>
              <Link href="/guardrails" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Guardrails</Link>
              <Link href="/provider-profiles" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Provider Profiles</Link>
            </div>
          </div>

          <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm dark:border-amber-900 dark:bg-amber-950/30">
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">Governance & Audit</p>
            <div className="mt-3 grid gap-3 grid-cols-2">
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Audit Events (7d)</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{lifecyclePosture.governance_context.audit_events_30d}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Tool Policies</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{lifecyclePosture.governance_context.tool_policies}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3 col-span-2">
                <p className="text-xs text-slate-500 dark:text-slate-400">Alert Rules</p>
                <p className="mt-1 text-lg font-semibold text-amber-600 dark:text-amber-400">{lifecyclePosture.governance_context.alert_rules}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-amber-200 dark:border-amber-800">
              <Link href="/audit-log" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Audit Log</Link>
              <Link href="/tool-policies" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Tool Policies</Link>
              <Link href="/alerts" className="text-xs text-amber-700 hover:underline dark:text-amber-400">Alert Rules</Link>
            </div>
          </div>
        </div>
      )}

      {lifecyclePosture && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50/50 p-5 shadow-sm dark:border-blue-900 dark:bg-blue-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">Org & Access Lifecycle</p>
          <div className="mt-3 grid gap-3 grid-cols-3">
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Total Workspaces</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{lifecyclePosture.org_access_context.total_workspaces}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">API Keys</p>
              <p className="mt-1 text-lg font-semibold text-blue-600 dark:text-blue-400">{lifecyclePosture.org_access_context.total_api_keys}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Total Users</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{lifecyclePosture.org_access_context.total_users}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-blue-200 dark:border-blue-800">
            <Link href="/workspaces" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Workspaces</Link>
            <Link href="/api-keys" className="text-xs text-blue-600 hover:underline dark:text-blue-400">API Keys</Link>
            <Link href="/users" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Users</Link>
            <Link href="/onboarding" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Onboarding</Link>
            <Link href="/settings" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Platform Settings</Link>
          </div>
        </div>
      )}

      {observePosture && (
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-cyan-200 bg-cyan-50/50 p-5 shadow-sm dark:border-cyan-900 dark:bg-cyan-950/30">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">Monitoring & Telemetry</p>
              <span className="text-xs text-cyan-600 dark:text-cyan-400">{observePosture.period_days}d</span>
            </div>
            <div className="grid gap-3 grid-cols-2">
              <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Alert Rules</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.monitoring_context.alert_rules}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Alert Firings</p>
                <p className={`mt-1 text-lg font-semibold ${observePosture.monitoring_context.alert_firings_7d > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{observePosture.monitoring_context.alert_firings_7d}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">OTLP Batches</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.telemetry_context.otlp_batches_7d}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Spans Ingested</p>
                <p className="mt-1 text-lg font-semibold text-cyan-600 dark:text-cyan-400">{observePosture.telemetry_context.otlp_spans_7d}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-cyan-200 dark:border-cyan-800">
              <Link href="/monitoring" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Monitoring →</Link>
              <Link href="/telemetry" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Telemetry →</Link>
              <Link href="/alerts" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Alert Rules →</Link>
            </div>
          </div>
          <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm dark:border-amber-900 dark:bg-amber-950/30">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">Governance & Build Context</p>
              <span className="text-xs text-amber-600 dark:text-amber-400">{observePosture.period_days}d</span>
            </div>
            <div className="grid gap-3 grid-cols-2">
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Guardrail Rules</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.governance_context.guardrail_rules}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Tool Policies</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.governance_context.tool_policies}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Eval Experiments</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.build_context.eval_experiments}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Agents</p>
                <p className="mt-1 text-lg font-semibold text-amber-600 dark:text-amber-400">{observePosture.build_context.agents}</p>
              </div>
            </div>
            <div className="mt-3 grid gap-3 grid-cols-2">
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Capture Policies</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.governance_context.capture_policies}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Workflow Runs</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.build_context.workflow_runs_7d}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-amber-200 dark:border-amber-800">
              <Link href="/governance" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Governance →</Link>
              <Link href="/evaluation" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Evaluation Studio →</Link>
              <Link href="/agents" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Agents →</Link>
              <Link href="/settings" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Platform Settings →</Link>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between gap-4">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={`Search ${organizations.length} organizations...`} className={`${inputCls} w-full pl-8`} />
        </div>
        <span className="text-xs font-medium text-slate-500">{organizations.length} total</span>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-800/50">
            <tr>
              <th className={TABLE_HEAD}>Organization</th>
              <th className={TABLE_HEAD}>Plan</th>
              <th className={TABLE_HEAD}>Status</th>
              <th className={TABLE_HEAD}>Workspaces</th>
              <th className={TABLE_HEAD}>Members</th>
              <th className={TABLE_HEAD}>Created</th>
              <th className={TABLE_HEAD} />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-400">Loading...</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-400">No organizations found.</td></tr>
            ) : filtered.map((org) => {
              const isCurrent = org.id === currentTenantId
              const statusDisabled = org.is_default || isCurrent || busyId === org.id
              const deleteDisabled = org.is_default || isCurrent || busyId === org.id
              return (
                <tr key={org.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <OrgIcon />
                      <div>
                        <div className="flex items-center gap-2 font-medium text-slate-800 dark:text-slate-100">
                          {org.name}
                          {org.is_default && <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-violet-700 dark:bg-violet-950 dark:text-violet-300">Default</span>}
                          {isCurrent && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-600 dark:bg-slate-800 dark:text-slate-300">Current</span>}
                        </div>
                        <div className="text-xs text-slate-500">{org.id}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 capitalize text-slate-600 dark:text-slate-300">{org.plan}</td>
                  <td className="px-4 py-3"><StatusBadge status={org.status} /></td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                      <LayoutGrid className="h-3.5 w-3.5 text-slate-400" /> {org.workspace_count}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                      <UsersRound className="h-3.5 w-3.5 text-slate-400" /> {org.member_count}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">{new Date(org.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-3">
                      <button onClick={() => openEdit(org)} title="Edit organization" className="text-slate-400 hover:text-violet-600">
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleStatus(org, org.status === 'active' ? 'suspended' : 'active')}
                        disabled={statusDisabled}
                        title={org.is_default ? 'Default organization cannot be suspended' : isCurrent ? 'Switch orgs before suspending this one' : org.status === 'active' ? 'Suspend organization' : 'Reactivate organization'}
                        className="text-slate-400 hover:text-amber-600 disabled:cursor-not-allowed disabled:opacity-35"
                      >
                        {org.status === 'active' ? <MoreHorizontal className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                      </button>
                      <button
                        onClick={() => { setDeleting(org); setDeleteConfirmation('') }}
                        disabled={deleteDisabled}
                        title={org.is_default ? 'Default organization cannot be deleted' : isCurrent ? 'Switch orgs before deleting this one' : 'Delete organization'}
                        className="text-slate-400 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-35"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <Modal title="New organization" onClose={() => setShowCreate(false)}>
          <form onSubmit={handleCreate} className="space-y-3">
            <input autoFocus type="text" required placeholder="Organization name" value={orgName} onChange={(e) => setOrgName(e.target.value)} className={`${inputCls} w-full`} />
            <input type="email" required placeholder="Org admin email" value={orgAdminEmail} onChange={(e) => setOrgAdminEmail(e.target.value)} className={`${inputCls} w-full`} />
            <input type="text" placeholder="Org admin full name (optional)" value={orgAdminName} onChange={(e) => setOrgAdminName(e.target.value)} className={`${inputCls} w-full`} />
            <input type="text" required placeholder="Temporary password" value={orgAdminPassword} onChange={(e) => setOrgAdminPassword(e.target.value)} className={`${inputCls} w-full`} />
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
              <input type="checkbox" checked={skipVerification} onChange={(e) => setSkipVerification(e.target.checked)} className="h-4 w-4 rounded border-slate-300" />
              Mark seeded admin as verified
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setShowCreate(false)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600">Cancel</button>
              <button type="submit" disabled={busyId === 'create'} className="rounded-lg bg-violet-600 px-3 py-1.5 text-sm text-white disabled:opacity-50">{busyId === 'create' ? 'Creating...' : 'Create organization'}</button>
            </div>
          </form>
        </Modal>
      )}

      {editing && (
        <Modal title={`Edit ${editing.name}`} onClose={() => setEditing(null)}>
          <form onSubmit={handleSaveEdit} className="space-y-3">
            <input autoFocus type="text" required value={editName} onChange={(e) => setEditName(e.target.value)} className={`${inputCls} w-full`} />
            <select value={editPlan} onChange={(e) => setEditPlan(e.target.value)} className={`${inputCls} w-full`}>
              <option value="free">Free</option>
              <option value="starter">Starter</option>
              <option value="growth">Growth</option>
              <option value="enterprise">Enterprise</option>
            </select>
            <select
              value={editStatus}
              onChange={(e) => setEditStatus(e.target.value as TenantStatus)}
              disabled={editing.is_default || editing.id === currentTenantId}
              title={editing.is_default ? 'Default organization status is locked' : editing.id === currentTenantId ? 'Current organization status is locked' : 'Organization status'}
              className={`${inputCls} w-full disabled:cursor-not-allowed disabled:opacity-60`}
            >
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
              <option value="archived">Archived</option>
            </select>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setEditing(null)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600">Cancel</button>
              <button type="submit" disabled={busyId === editing.id} className="rounded-lg bg-violet-600 px-3 py-1.5 text-sm text-white disabled:opacity-50">{busyId === editing.id ? 'Saving...' : 'Save'}</button>
            </div>
          </form>
        </Modal>
      )}

      {deleting && (
        <Modal title={`Delete ${deleting.name}`} onClose={() => setDeleting(null)}>
          <form onSubmit={handleDelete} className="space-y-4">
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
              <div className="mb-1 flex items-center gap-2 font-medium">
                <AlertTriangle className="h-4 w-4" /> Permanent organization deletion
              </div>
              This removes {deleting.workspace_count} workspaces and {deleting.member_count} memberships for this organization.
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">
                Type {deleting.name} to confirm
              </label>
              <input autoFocus value={deleteConfirmation} onChange={(e) => setDeleteConfirmation(e.target.value)} className={`${inputCls} w-full`} />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setDeleting(null)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600">Cancel</button>
              <button type="submit" disabled={deleteConfirmation !== deleting.name || busyId === deleting.id} className="rounded-lg bg-red-600 px-3 py-1.5 text-sm text-white disabled:opacity-50">{busyId === deleting.id ? 'Deleting...' : 'Delete organization'}</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-5 shadow-xl dark:border-slate-700 dark:bg-slate-900" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X className="h-5 w-5" /></button>
        </div>
        {children}
      </div>
    </div>
  )
}
