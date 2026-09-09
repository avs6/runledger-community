'use client'

import { useSession } from 'next-auth/react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { CheckCircle2, Database, Eye, Info, Layers, Link2, Loader2, Pencil, Plus, Radio, Search, Shield, Trash2, X, Building2, Zap, Lock, Globe, Server, Activity } from 'lucide-react'
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
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500'

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

const MODE_COLORS: Record<string, string> = {
  METADATA_ONLY: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  ERRORS_ONLY: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  SAMPLED: 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
  FULL: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
}

export default function DataCapturePage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''
  const { canManageOrgSettings } = useRole()

  const [tab, setTab] = useState<Tab>('global')
  const [capturePolicy, setCapturePolicy] = useState<CapturePolicyResponse | null>(null)
  const [privacyMode, setPrivacyMode] = useState('FULL')
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

  const compliance = COMPLIANCE_NOTES[privacyMode]
  const ComplianceIcon = compliance?.icon ?? Info

  const postures = useMemo(() => {
    const items: { label: string; value: string | number; sub?: string; color: string }[] = []
    if (orgPosture) {
      items.push(
        { label: 'Workspace Users', value: orgPosture.user_context.total_users, color: 'text-blue-400' },
        { label: 'Capture Policies', value: orgPosture.capture_context.active_policies, sub: `${orgPosture.capture_context.total_policies} total`, color: 'text-blue-400' },
        { label: 'Security Events', value: orgPosture.security_context.security_events_30d, sub: '30d', color: 'text-blue-400' },
      )
    }
    if (gatewayPosture) {
      items.push(
        { label: 'Gateway Routes', value: gatewayPosture.provider_context.total_routes, sub: `${gatewayPosture.provider_context.total_providers} providers`, color: 'text-violet-400' },
        { label: 'Guardrails', value: gatewayPosture.guardrail_context.total_guardrails, sub: `${gatewayPosture.guardrail_context.guardrail_events_30d} events`, color: 'text-violet-400' },
      )
    }
    if (runtimePosture) {
      items.push(
        { label: 'Provider Calls', value: runtimePosture.gateway_evidence.provider_calls_30d, sub: '30d', color: 'text-cyan-400' },
        { label: 'Runs', value: runtimePosture.observe_evidence.runs_30d, sub: '30d', color: 'text-cyan-400' },
        { label: 'Budgets', value: runtimePosture.budget_context.total_budgets, color: 'text-cyan-400' },
      )
    }
    return items
  }, [orgPosture, gatewayPosture, runtimePosture])

  if (!canManageOrgSettings) {
    return (
      <div className="p-8">
        <h1 className="text-lg font-bold text-slate-900 dark:text-white">Data Capture</h1>
        <p className="mt-2 text-xs text-slate-500">Data capture policy is an organization-admin function.</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4">
      {/* Hero header */}
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 ring-1 ring-emerald-200 dark:bg-emerald-500/20 dark:ring-emerald-400/30">
              <Database className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-950 dark:text-white">Data Capture Policy Studio</h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">Privacy mode, per-scope overrides, PII redaction &amp; compliance controls</p>
            </div>
          </div>
          {capturePolicy && (
            <div className="flex items-center gap-2">
              <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${MODE_COLORS[capturePolicy.privacy_mode] ?? 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300'}`}>
                {capturePolicy.privacy_mode}
              </span>
              {capturePolicy.sampled_rate && (
                <span className="text-xs text-emerald-600 dark:text-emerald-300">{sampledRatePct(capturePolicy.sampled_rate)}</span>
              )}
            </div>
          )}
        </div>

        {/* KPI strip */}
        {postures.length > 0 && (
          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
            {postures.map((p) => (
              <div key={p.label} className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-lg font-bold text-slate-900 dark:text-white">{p.value}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">{p.label}</p>
                {p.sub && <p className="text-[10px] text-slate-400 dark:text-slate-500">{p.sub}</p>}
              </div>
            ))}
          </div>
        )}

        {/* Posture chips */}
        {govInternal && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {[
              { label: `${govInternal.tool_registry_context.total_tools} Tools`, sub: `${govInternal.tool_registry_context.enforced_tools} enforced` },
              { label: `${govInternal.tool_policies_context.active_policies} Policies`, sub: 'active' },
              { label: `${govInternal.approvals_context.pending_approvals} Pending`, sub: 'approvals' },
              { label: `${govInternal.audit_context.audit_events_30d} Audit`, sub: '30d' },
            ].map((c) => (
              <span key={c.label} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                <span className="font-semibold text-slate-900 dark:text-white">{c.label}</span> {c.sub}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-lg bg-slate-100 p-1 dark:bg-slate-800/80">
        {[
          { key: 'global' as Tab, label: 'Global Policy', icon: Shield },
          { key: 'scoped' as Tab, label: 'Scoped Overrides', icon: Eye },
          { key: 'pii' as Tab, label: 'PII Testing', icon: Search },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === key
                ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Global Policy tab */}
      {tab === 'global' && (
        <div className="space-y-3">
          <form onSubmit={handleSavePrivacy} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center gap-2 mb-3">
              <Lock className="h-4 w-4 text-emerald-500" />
              <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Privacy Mode</p>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <div className="flex-1 min-w-[200px]">
                <select value={privacyMode} onChange={(e) => setPrivacyMode(e.target.value)} className={inputCls}>
                  <option value="METADATA_ONLY">METADATA_ONLY</option>
                  <option value="ERRORS_ONLY">ERRORS_ONLY</option>
                  <option value="SAMPLED">SAMPLED</option>
                  <option value="FULL">FULL</option>
                </select>
              </div>
              {privacyMode === 'SAMPLED' && (
                <div className="w-24">
                  <label className="mb-1 block text-[10px] text-slate-500">Sample %</label>
                  <input type="number" min="0" max="100" step="1" value={sampledRate} onChange={(e) => setSampledRate(e.target.value)} className={inputCls} required />
                </div>
              )}
              <button type="submit" disabled={savingPrivacy} className="rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 px-4 py-1.5 text-xs font-semibold text-white shadow-sm hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50">
                {savingPrivacy ? 'Saving...' : 'Save Policy'}
              </button>
            </div>

            <div className="mt-3 flex items-start gap-2 rounded-lg border border-slate-100 bg-slate-50/60 p-2.5 dark:border-slate-700 dark:bg-slate-800/40">
              <ComplianceIcon className={`mt-0.5 h-3.5 w-3.5 flex-shrink-0 ${compliance.color}`} />
              <p className={`text-[11px] leading-relaxed ${compliance.color}`}>{compliance.note}</p>
            </div>
          </form>

          {/* Retention preview */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="h-4 w-4 text-emerald-500" />
              <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Retention Preview</p>
            </div>
            {loadingRetention ? (
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading preview...
              </div>
            ) : retention ? (
              <div className="space-y-3">
                <div className="inline-flex items-baseline gap-2 rounded-lg bg-emerald-50 px-3 py-2 dark:bg-emerald-950/30">
                  <span className="text-xl font-bold text-emerald-700 dark:text-emerald-300">{retention.estimated_storage_mb_per_month}</span>
                  <span className="text-xs text-emerald-600 dark:text-emerald-400">MB/month est.</span>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  <div>
                    <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Fields Captured</p>
                    <div className="flex flex-wrap gap-1">
                      {retention.fields_captured.map((item) => (
                        <span key={item} className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">{item}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Fields Redacted</p>
                    <div className="flex flex-wrap gap-1">
                      {retention.fields_redacted.map((item) => (
                        <span key={item} className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">{item}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Compliance</p>
                    <ul className="space-y-0.5 text-[11px] text-slate-600 dark:text-slate-400">
                      {retention.compliance_notes.map((note) => (
                        <li key={note} className="flex items-start gap-1"><CheckCircle2 className="mt-0.5 h-3 w-3 flex-shrink-0 text-emerald-500" />{note}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400">Unable to load retention preview.</p>
            )}
          </div>
        </div>
      )}

      {/* Scoped Overrides tab */}
      {tab === 'scoped' && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-emerald-500" />
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Per-Scope Overrides</p>
              </div>
              <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">Override global policy for a workspace, API key, route, user, or agent.</p>
            </div>
            <button
              onClick={() => (showScopeForm ? resetScopeForm() : setShowScopeForm(true))}
              className="flex items-center gap-1 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 px-3 py-1.5 text-xs font-semibold text-white hover:from-emerald-500 hover:to-teal-500"
            >
              {showScopeForm ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
              {showScopeForm ? 'Cancel' : 'Add Scope'}
            </button>
          </div>

          {showScopeForm && (
            <div className="mb-4 grid gap-2 rounded-lg border border-emerald-200 bg-emerald-50/40 p-3 dark:border-emerald-800 dark:bg-emerald-950/20 md:grid-cols-4">
              <label className="text-xs">
                <span className="mb-1 block text-[10px] font-medium text-slate-500">Scope Type</span>
                <select value={scopeType} onChange={(e) => setScopeType(e.target.value)} className={inputCls} disabled={Boolean(editingScopeKey)}>
                  {SCOPE_TYPES.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
              <label className="text-xs">
                <span className="mb-1 block text-[10px] font-medium text-slate-500">Scope ID</span>
                <input value={scopeId} onChange={(e) => setScopeId(e.target.value)} className={inputCls} disabled={Boolean(editingScopeKey)} />
              </label>
              <label className="text-xs">
                <span className="mb-1 block text-[10px] font-medium text-slate-500">Privacy Mode</span>
                <select value={scopeMode} onChange={(e) => setScopeMode(e.target.value)} className={inputCls}>
                  <option value="METADATA_ONLY">METADATA_ONLY</option>
                  <option value="ERRORS_ONLY">ERRORS_ONLY</option>
                  <option value="SAMPLED">SAMPLED</option>
                  <option value="FULL">FULL</option>
                </select>
              </label>
              <label className="text-xs">
                <span className="mb-1 block text-[10px] font-medium text-slate-500">Sample rate (%)</span>
                <input type="number" min="0" max="100" step="1" value={scopeRate} onChange={(e) => setScopeRate(e.target.value)} className={inputCls} disabled={scopeMode !== 'SAMPLED'} placeholder="10" />
              </label>
              <div className="md:col-span-4 flex gap-2">
                <button onClick={() => void handleSaveScope()} disabled={savingScope || !scopeId.trim()} className="rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 px-4 py-1.5 text-xs font-semibold text-white hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50">
                  {savingScope ? 'Saving...' : editingScopeKey ? 'Save Changes' : 'Create Override'}
                </button>
                {editingScopeKey && (
                  <button onClick={resetScopeForm} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">Cancel</button>
                )}
              </div>
            </div>
          )}

          {loadingScopes ? (
            <p className="text-xs text-slate-400">Loading...</p>
          ) : scopes.length === 0 ? (
            <p className="text-xs text-slate-400">No scoped overrides. The global policy applies everywhere.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th className="px-3 py-2 font-medium text-slate-500">Scope</th>
                    <th className="px-3 py-2 font-medium text-slate-500">Privacy Mode</th>
                    <th className="px-3 py-2 font-medium text-slate-500">Sample Rate</th>
                    <th className="px-3 py-2 text-right font-medium text-slate-500">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {scopes.map((scope) => (
                    <tr key={`${scope.scope_type}:${scope.scope_id}`} className="border-b border-slate-100 dark:border-slate-800 hover:bg-emerald-50/30 dark:hover:bg-emerald-950/10">
                      <td className="px-3 py-2">
                        <p className="font-mono text-[11px] font-medium text-slate-700 dark:text-slate-200">{scope.scope_type}</p>
                        <p className="font-mono text-[10px] text-slate-500">{scope.scope_id}</p>
                      </td>
                      <td className="px-3 py-2">
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${MODE_COLORS[scope.privacy_mode] ?? 'bg-slate-100 text-slate-700'}`}>
                          {scope.privacy_mode}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-slate-500">{sampledRatePct(scope.sampled_rate)}</td>
                      <td className="px-3 py-2">
                        <div className="flex justify-end gap-1">
                          <button onClick={() => handleEditScope(scope)} className="rounded-md border border-slate-200 p-1.5 text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">
                            <Pencil className="h-3 w-3" />
                          </button>
                          <button onClick={() => void handleDeleteScope(scope)} className="rounded-md border border-red-200 p-1.5 text-red-500 hover:bg-red-50 dark:border-red-900/40 dark:hover:bg-red-950/30">
                            <Trash2 className="h-3 w-3" />
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

      {/* PII Testing tab */}
      {tab === 'pii' && (
        <div className="space-y-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center gap-2 mb-3">
              <Search className="h-4 w-4 text-emerald-500" />
              <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Test PII Redaction</p>
            </div>
            <p className="mb-2 text-[11px] text-slate-500">Paste sample text to see how RunLedger detects and redacts personally identifiable information.</p>
            <textarea
              value={piiText}
              onChange={(e) => setPiiText(e.target.value)}
              rows={3}
              className={`resize-none ${inputCls}`}
              placeholder="My email is john@example.com and my SSN is 123-45-6789"
            />
            <button
              onClick={() => void handleTestPii()}
              disabled={testingPii || !piiText.trim()}
              className="mt-2 flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 px-4 py-1.5 text-xs font-semibold text-white hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50"
            >
              {testingPii ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
              Test Redaction
            </button>
          </div>

          {piiResult && (
            <div className="grid gap-3 lg:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">
                  Detected PII ({piiResult.detected_pii.length})
                </p>
                {piiResult.detected_pii.length === 0 ? (
                  <p className="text-xs text-emerald-600 dark:text-emerald-400">No PII detected in the input text.</p>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {piiResult.detected_pii.map((item, index) => (
                      <div key={`${item.type}-${index}`} className="rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 dark:border-red-900 dark:bg-red-950/30">
                        <span className="text-[10px] font-bold text-red-700 dark:text-red-400">{item.type}</span>
                        <p className="font-mono text-[11px] text-red-600 dark:text-red-300">{item.value}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">Redacted Output</p>
                <pre className="overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-800 dark:bg-slate-800 dark:text-slate-200">{piiResult.redacted_text}</pre>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Quick nav footer */}
      <div className="flex flex-wrap gap-1.5 pt-2">
        {[
          { href: '/security', label: 'Security' },
          { href: '/approvals', label: 'Approvals' },
          { href: '/audit', label: 'Audit Log' },
          { href: '/tool-registry', label: 'Tool Governance' },
          { href: '/alert-rules', label: 'Alert Rules' },
          { href: '/tags', label: 'Tags' },
          { href: '/governance-pack', label: 'Audit Pack' },
        ].map((l) => (
          <Link key={l.href} href={l.href} className="rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-medium text-emerald-700 ring-1 ring-emerald-200 hover:bg-emerald-100 dark:bg-emerald-950/30 dark:text-emerald-400 dark:ring-emerald-800 dark:hover:bg-emerald-950/50">
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  )
}
