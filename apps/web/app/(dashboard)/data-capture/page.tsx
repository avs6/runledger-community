'use client'

import { useSession } from 'next-auth/react'
import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { CheckCircle2, Database, Eye, Info, Layers, Link2, Loader2, Pencil, Plus, Radio, Search, Shield, Trash2, X, Building2 } from 'lucide-react'
import Link from 'next/link'
import { useRole } from '@/components/rbac/useRole'
import {
  deleteCapturePolicyScope,
  getCapturePolicy,
  getRetentionPreview,
  listCapturePolicyScopes,
  testPiiRedaction,
  upsertCapturePolicy,
  upsertCapturePolicyScope,
  getDataProtectionOrgPosture,
  getDataProtectionGatewayPosture,
  getGovernanceInternalPosture,
  getDataCaptureRuntimePosture,
} from '@/lib/api'
import type { CapturePolicyResponse, CapturePolicyScope, GovernanceInternalPosture, DataCaptureRuntimePosture, PiiTestResult, RetentionPreview, DataProtectionOrgPosture, DataProtectionGatewayPosture } from '@/types/api'

const inputCls =
  'rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:ring-indigo-400'

type Tab = 'global' | 'scoped' | 'pii'

const SCOPE_TYPES = ['org', 'workspace', 'api_key', 'model_route', 'user', 'intent', 'agent'] as const

const COMPLIANCE_NOTES: Record<string, { icon: typeof CheckCircle2; color: string; note: string }> = {
  METADATA_ONLY: {
    icon: CheckCircle2,
    color: 'text-emerald-600 dark:text-emerald-400',
    note: 'Compliant with GDPR Art. 5(1)(c) data minimization. No personal data stored.',
  },
  ERRORS_ONLY: {
    icon: Info,
    color: 'text-amber-600 dark:text-amber-400',
    note: 'Error payloads can still carry sensitive context. Review retention posture.',
  },
  SAMPLED: {
    icon: Info,
    color: 'text-amber-600 dark:text-amber-400',
    note: 'Sampled payload capture still falls within data retention and consent policies.',
  },
  FULL: {
    icon: Info,
    color: 'text-red-600 dark:text-red-400',
    note: 'Full capture stores request and response bodies. Use only with explicit approval.',
  },
}

function sampledRatePct(rate: string | null | undefined) {
  if (!rate) return '—'
  return `${(parseFloat(rate) * 100).toFixed(0)}%`
}

export default function DataCapturePage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''
  const { canManageOrgSettings } = useRole()

  const [tab, setTab] = useState<Tab>('global')
  const [capturePolicy, setCapturePolicy] = useState<CapturePolicyResponse | null>(null)
  const [privacyMode, setPrivacyMode] = useState('METADATA_ONLY')
  const [sampledRate, setSampledRate] = useState('')
  const [savingPrivacy, setSavingPrivacy] = useState(false)
  const [retention, setRetention] = useState<RetentionPreview | null>(null)
  const [loadingRetention, setLoadingRetention] = useState(false)

  const [scopes, setScopes] = useState<CapturePolicyScope[]>([])
  const [loadingScopes, setLoadingScopes] = useState(false)
  const [showScopeForm, setShowScopeForm] = useState(false)
  const [editingScopeKey, setEditingScopeKey] = useState<string | null>(null)
  const [scopeType, setScopeType] = useState<string>(SCOPE_TYPES[0])
  const [scopeId, setScopeId] = useState('')
  const [scopeMode, setScopeMode] = useState('METADATA_ONLY')
  const [scopeRate, setScopeRate] = useState('')
  const [savingScope, setSavingScope] = useState(false)

  const [piiText, setPiiText] = useState('')
  const [piiResult, setPiiResult] = useState<PiiTestResult | null>(null)
  const [testingPii, setTestingPii] = useState(false)
  const [orgPosture, setOrgPosture] = useState<DataProtectionOrgPosture | null>(null)
  const [gatewayPosture, setGatewayPosture] = useState<DataProtectionGatewayPosture | null>(null)
  const [govInternal, setGovInternal] = useState<GovernanceInternalPosture | null>(null)
  const [runtimePosture, setRuntimePosture] = useState<DataCaptureRuntimePosture | null>(null)

  const resetScopeForm = useCallback(() => {
    setEditingScopeKey(null)
    setScopeType(SCOPE_TYPES[0])
    setScopeId('')
    setScopeMode('METADATA_ONLY')
    setScopeRate('')
    setShowScopeForm(false)
  }, [])

  const loadPolicy = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return
    try {
      const policy = await getCapturePolicy(apiKey)
      if (policy) {
        setCapturePolicy(policy)
        setPrivacyMode(policy.privacy_mode)
        setSampledRate(policy.sampled_rate ? String(parseFloat(policy.sampled_rate) * 100) : '')
      }
    } catch {
      toast.error('Failed to load capture policy')
    }
  }, [apiKey, canManageOrgSettings])

  const loadScopes = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return
    setLoadingScopes(true)
    try {
      const res = await listCapturePolicyScopes(apiKey)
      setScopes(res.items)
    } catch {
      toast.error('Failed to load scoped policies')
    } finally {
      setLoadingScopes(false)
    }
  }, [apiKey, canManageOrgSettings])

  useEffect(() => {
    void loadPolicy()
    if (apiKey) {
      getDataProtectionOrgPosture(apiKey).then(setOrgPosture).catch(() => null)
      getDataProtectionGatewayPosture(apiKey).then(setGatewayPosture).catch(() => null)
      getGovernanceInternalPosture(apiKey).then(setGovInternal).catch(() => null)
      getDataCaptureRuntimePosture(apiKey).then(setRuntimePosture).catch(() => null)
    }
  }, [loadPolicy])

  useEffect(() => {
    if (!apiKey || !canManageOrgSettings) return
    setLoadingRetention(true)
    getRetentionPreview(apiKey, privacyMode)
      .then(setRetention)
      .catch(() => setRetention(null))
      .finally(() => setLoadingRetention(false))
  }, [apiKey, canManageOrgSettings, privacyMode])

  useEffect(() => {
    if (tab === 'scoped') {
      void loadScopes()
    }
  }, [tab, loadScopes])

  async function handleSavePrivacy(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setSavingPrivacy(true)
    try {
      const updated = await upsertCapturePolicy(apiKey, {
        privacy_mode: privacyMode,
        sampled_rate: privacyMode === 'SAMPLED' && sampledRate.trim() ? parseFloat(sampledRate) / 100 : null,
      })
      setCapturePolicy(updated)
      toast.success('Capture policy saved')
    } catch {
      toast.error('Failed to save capture policy')
    } finally {
      setSavingPrivacy(false)
    }
  }

  async function handleSaveScope() {
    if (!apiKey || !scopeId.trim()) return
    setSavingScope(true)
    try {
      await upsertCapturePolicyScope(apiKey, {
        scope_type: scopeType,
        scope_id: scopeId.trim(),
        privacy_mode: scopeMode,
        sampled_rate: scopeMode === 'SAMPLED' && scopeRate.trim() ? parseFloat(scopeRate) / 100 : null,
      })
      toast.success(editingScopeKey ? 'Scoped policy updated' : 'Scoped policy created')
      resetScopeForm()
      await loadScopes()
    } catch {
      toast.error('Failed to save scoped policy')
    } finally {
      setSavingScope(false)
    }
  }

  function handleEditScope(scope: CapturePolicyScope) {
    setEditingScopeKey(`${scope.scope_type}:${scope.scope_id}`)
    setScopeType(scope.scope_type)
    setScopeId(scope.scope_id)
    setScopeMode(scope.privacy_mode)
    setScopeRate(scope.sampled_rate ? String(parseFloat(scope.sampled_rate) * 100) : '')
    setShowScopeForm(true)
  }

  async function handleDeleteScope(scope: CapturePolicyScope) {
    if (!apiKey || !confirm(`Delete scoped override ${scope.scope_type}:${scope.scope_id}?`)) return
    try {
      await deleteCapturePolicyScope(apiKey, scope.scope_type, scope.scope_id)
      toast.success('Scoped policy deleted')
      if (editingScopeKey === `${scope.scope_type}:${scope.scope_id}`) {
        resetScopeForm()
      }
      await loadScopes()
    } catch {
      toast.error('Failed to delete scoped policy')
    }
  }

  async function handleTestPii() {
    if (!apiKey || !piiText.trim()) return
    setTestingPii(true)
    setPiiResult(null)
    try {
      setPiiResult(await testPiiRedaction(apiKey, piiText))
    } catch {
      toast.error('PII test failed')
    } finally {
      setTestingPii(false)
    }
  }

  if (!canManageOrgSettings) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Data Capture</h1>
        <p className="mt-4 text-sm text-slate-500">Data capture policy is an organization-admin function.</p>
      </div>
    )
  }

  const compliance = COMPLIANCE_NOTES[privacyMode]
  const ComplianceIcon = compliance?.icon ?? Info

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 dark:bg-indigo-900/40">
          <Database className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Data Capture Policy Studio</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Control privacy mode, per-scope overrides, and PII redaction behavior.
          </p>
        </div>
      </div>

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
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Capture Policies</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.capture_context.active_policies}</p>
              <p className="text-xs text-slate-500">{orgPosture.capture_context.total_policies} total</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Security Events (30d)</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.security_context.security_events_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">MCP Servers</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.mcp_context.active_servers}</p>
              <p className="text-xs text-slate-500">{orgPosture.mcp_context.total_servers} total</p>
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
              <p className="text-xs text-slate-500">{gatewayPosture.guardrail_context.guardrail_events_30d} events 30d</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-violet-700 dark:text-violet-300">Tool Calls (30d)</p>
              <p className="mt-1 text-2xl font-bold text-violet-900 dark:text-violet-50">{gatewayPosture.run_context.tool_runs_30d}</p>
              <p className="text-xs text-slate-500">{gatewayPosture.run_context.total_runs_30d} agent runs</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-violet-700 dark:text-violet-300">Alert Firings (30d)</p>
              <p className="mt-1 text-2xl font-bold text-violet-900 dark:text-violet-50">{gatewayPosture.monitoring_context.alert_firings_30d}</p>
              <p className="text-xs text-slate-500">{gatewayPosture.monitoring_context.total_alert_rules} rules</p>
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
              <p className="text-xs text-slate-500">{govInternal.approvals_context.total_approvals_30d} total 30d</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Audit Events 30d</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.audit_context.audit_events_30d}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/tool-registry" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tool Registry</Link>
            <Link href="/tool-policies" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tool Policies</Link>
            <Link href="/approvals" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Approvals</Link>
            <Link href="/security" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Security</Link>
            <Link href="/alert-rules" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Alert Rules</Link>
            <Link href="/audit" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Audit Log</Link>
            <Link href="/governance-pack" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Governance Pack</Link>
            <Link href="/tags" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tags</Link>
          </div>
        </div>
      )}

      {runtimePosture && (
        <div className="rounded-2xl border border-cyan-200 dark:border-cyan-800 bg-cyan-50/60 dark:bg-cyan-950/30 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-cyan-600 dark:text-cyan-400" />
            <h2 className="text-lg font-semibold text-cyan-900 dark:text-cyan-100">Runtime Scope &amp; Evidence</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Provider Calls 30d</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.gateway_evidence.provider_calls_30d}</p>
              <p className="text-xs text-slate-500">{runtimePosture.gateway_evidence.model_routes} model routes</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Runs 30d</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.observe_evidence.runs_30d}</p>
              <p className="text-xs text-slate-500">{runtimePosture.observe_evidence.audit_events_30d} audit events</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Total Budgets</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.budget_context.total_budgets}</p>
              <p className="text-xs text-slate-500">{runtimePosture.budget_context.budget_notifications_30d} notifications 30d</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Ledger Snapshots</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.ledger_context.ledger_snapshots}</p>
              <p className="text-xs text-slate-500">{runtimePosture.ledger_context.ledger_entries_30d} entries 30d</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/workspaces" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Workspaces</Link>
            <Link href="/api-keys" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">API Keys</Link>
            <Link href="/model-gateway" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Model Gateway</Link>
            <Link href="/response-cache" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Response Cache</Link>
            <Link href="/request-flow" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Request Flow</Link>
            <Link href="/audit" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Audit Log</Link>
            <Link href="/budgets" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Budgets</Link>
            <Link href="/ledger" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Ledger</Link>
          </div>
        </div>
      )}

      <div className="flex gap-1 rounded-lg bg-slate-100 p-1 dark:bg-slate-800">
        {[
          { key: 'global' as Tab, label: 'Global Policy', icon: Shield },
          { key: 'scoped' as Tab, label: 'Scoped Policies', icon: Eye },
          { key: 'pii' as Tab, label: 'PII Testing', icon: Search },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex flex-1 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === key
                ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === 'global' && (
        <div className="space-y-4">
          {capturePolicy && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span>Current:</span>
              <span className="rounded bg-indigo-100 px-2 py-0.5 font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                {capturePolicy.privacy_mode}
              </span>
              <span>{sampledRatePct(capturePolicy.sampled_rate)}</span>
            </div>
          )}

          <form onSubmit={handleSavePrivacy} className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Privacy Mode</p>
            <div className="flex flex-wrap items-end gap-3">
              <select value={privacyMode} onChange={(e) => setPrivacyMode(e.target.value)} className={inputCls}>
                <option value="METADATA_ONLY">METADATA_ONLY</option>
                <option value="ERRORS_ONLY">ERRORS_ONLY</option>
                <option value="SAMPLED">SAMPLED</option>
                <option value="FULL">FULL</option>
              </select>
              {privacyMode === 'SAMPLED' && (
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-500">Sample rate (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="1"
                    value={sampledRate}
                    onChange={(e) => setSampledRate(e.target.value)}
                    className={`w-24 ${inputCls}`}
                    required
                  />
                </div>
              )}
            </div>

            <div className="mt-4 flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50/60 p-3 dark:border-slate-700 dark:bg-slate-800/40">
              <ComplianceIcon className={`mt-0.5 h-4 w-4 flex-shrink-0 ${compliance.color}`} />
              <p className={`text-xs ${compliance.color}`}>{compliance.note}</p>
            </div>

            <button type="submit" disabled={savingPrivacy} className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
              {savingPrivacy ? 'Saving...' : 'Save Policy'}
            </button>
          </form>

          <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Retention Preview</p>
            {loadingRetention ? (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading preview...
              </div>
            ) : retention ? (
              <div className="space-y-4">
                <div className="rounded-lg bg-slate-50 px-4 py-3 dark:bg-slate-800/60">
                  <span className="text-xs text-slate-500">Estimated storage</span>
                  <p className="text-lg font-semibold text-slate-900 dark:text-white">
                    {retention.estimated_storage_mb_per_month} MB/month
                  </p>
                </div>
                <div className="grid gap-4 md:grid-cols-3">
                  <div>
                    <p className="mb-1 text-xs font-medium text-slate-500">Fields Captured</p>
                    <div className="flex flex-wrap gap-1">
                      {retention.fields_captured.map((item) => (
                        <span key={item} className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-medium text-slate-500">Fields Redacted</p>
                    <div className="flex flex-wrap gap-1">
                      {retention.fields_redacted.map((item) => (
                        <span key={item} className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-medium text-slate-500">Compliance Notes</p>
                    <ul className="list-inside list-disc space-y-1 text-xs text-slate-600 dark:text-slate-400">
                      {retention.compliance_notes.map((note) => (
                        <li key={note}>{note}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-400">Unable to load retention preview.</p>
            )}
          </div>
        </div>
      )}

      {tab === 'scoped' && (
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Per-Scope Overrides</p>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Override the global policy for a workspace, API key, route, user, or agent context.</p>
            </div>
            <button
              onClick={() => (showScopeForm ? resetScopeForm() : setShowScopeForm(true))}
              className="flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
            >
              {showScopeForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
              {showScopeForm ? 'Cancel' : 'Add Scope'}
            </button>
          </div>

          {showScopeForm && (
            <div className="mb-6 grid gap-3 rounded-xl border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-700 dark:bg-slate-800/40 md:grid-cols-4">
              <label className="text-sm">
                <span className="mb-1 block text-xs text-slate-500">Scope Type</span>
                <select value={scopeType} onChange={(e) => setScopeType(e.target.value)} className={`${inputCls} w-full`} disabled={Boolean(editingScopeKey)}>
                  {SCOPE_TYPES.map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                <span className="mb-1 block text-xs text-slate-500">Scope ID</span>
                <input value={scopeId} onChange={(e) => setScopeId(e.target.value)} className={`${inputCls} w-full`} disabled={Boolean(editingScopeKey)} />
              </label>
              <label className="text-sm">
                <span className="mb-1 block text-xs text-slate-500">Privacy Mode</span>
                <select value={scopeMode} onChange={(e) => setScopeMode(e.target.value)} className={`${inputCls} w-full`}>
                  <option value="METADATA_ONLY">METADATA_ONLY</option>
                  <option value="ERRORS_ONLY">ERRORS_ONLY</option>
                  <option value="SAMPLED">SAMPLED</option>
                  <option value="FULL">FULL</option>
                </select>
              </label>
              <label className="text-sm">
                <span className="mb-1 block text-xs text-slate-500">Sample rate (%)</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value={scopeRate}
                  onChange={(e) => setScopeRate(e.target.value)}
                  className={`${inputCls} w-full`}
                  disabled={scopeMode !== 'SAMPLED'}
                  placeholder="10"
                />
              </label>
              <div className="md:col-span-4 flex gap-2">
                <button onClick={() => void handleSaveScope()} disabled={savingScope || !scopeId.trim()} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                  {savingScope ? 'Saving...' : editingScopeKey ? 'Save Changes' : 'Create Override'}
                </button>
                {editingScopeKey && (
                  <button onClick={resetScopeForm} className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800">
                    Cancel
                  </button>
                )}
              </div>
            </div>
          )}

          {loadingScopes ? (
            <p className="text-sm text-slate-400">Loading...</p>
          ) : scopes.length === 0 ? (
            <p className="text-sm text-slate-400">No scoped overrides. The global policy applies everywhere.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th className="pb-2 font-medium text-slate-500">Scope</th>
                    <th className="pb-2 font-medium text-slate-500">Privacy Mode</th>
                    <th className="pb-2 font-medium text-slate-500">Sample Rate</th>
                    <th className="pb-2 text-right font-medium text-slate-500">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {scopes.map((scope) => (
                    <tr key={`${scope.scope_type}:${scope.scope_id}`} className="border-b border-slate-100 dark:border-slate-800">
                      <td className="py-3">
                        <p className="font-mono text-xs text-slate-700 dark:text-slate-200">{scope.scope_type}</p>
                        <p className="font-mono text-xs text-slate-500">{scope.scope_id}</p>
                      </td>
                      <td className="py-3">
                        <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                          {scope.privacy_mode}
                        </span>
                      </td>
                      <td className="py-3 text-slate-500">{sampledRatePct(scope.sampled_rate)}</td>
                      <td className="py-3">
                        <div className="flex justify-end gap-2">
                          <button onClick={() => handleEditScope(scope)} className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button onClick={() => void handleDeleteScope(scope)} className="rounded-lg border border-red-200 p-2 text-red-600 hover:bg-red-50 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/30">
                            <Trash2 className="h-4 w-4" />
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
      )}

      {tab === 'pii' && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Test PII Redaction</p>
            <p className="mb-3 text-sm text-slate-500">
              Paste sample text to see how RunLedger detects and redacts personally identifiable information.
            </p>
            <textarea
              value={piiText}
              onChange={(e) => setPiiText(e.target.value)}
              rows={4}
              className={`w-full resize-none ${inputCls}`}
              placeholder="My email is john@example.com and my SSN is 123-45-6789"
            />
            <button
              onClick={() => void handleTestPii()}
              disabled={testingPii || !piiText.trim()}
              className="mt-3 flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {testingPii ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Test Redaction
            </button>
          </div>

          {piiResult && (
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Detected PII ({piiResult.detected_pii.length})
                </p>
                {piiResult.detected_pii.length === 0 ? (
                  <p className="text-sm text-emerald-600 dark:text-emerald-400">No PII detected in the input text.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {piiResult.detected_pii.map((item, index) => (
                      <div key={`${item.type}-${index}`} className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 dark:border-red-900 dark:bg-red-950/30">
                        <span className="text-xs font-semibold text-red-700 dark:text-red-400">{item.type}</span>
                        <p className="mt-0.5 font-mono text-xs text-red-600 dark:text-red-300">{item.value}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Redacted Output</p>
                <pre className="overflow-x-auto rounded-lg bg-slate-50 p-4 text-sm text-slate-800 dark:bg-slate-800 dark:text-slate-200">
                  {piiResult.redacted_text}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
