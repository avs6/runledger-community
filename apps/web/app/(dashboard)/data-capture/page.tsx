'use client'

import { useSession } from 'next-auth/react'
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import { useRole } from '@/components/rbac/useRole'
import {
  getCapturePolicy,
  upsertCapturePolicy,
  getRetentionPreview,
  testPiiRedaction,
  listCapturePolicyScopes,
  upsertCapturePolicyScope,
} from '@/lib/api'
import type {
  CapturePolicyResponse,
  CapturePolicyScope,
  RetentionPreview,
  PiiTestResult,
} from '@/types/api'
import {
  Database,
  Shield,
  Eye,
  Search,
  Plus,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Info,
} from 'lucide-react'

const inputCls =
  'rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-1.5 text-sm placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

type Tab = 'global' | 'scoped' | 'pii'

const SCOPE_TYPES = ['org', 'workspace', 'api_key', 'model_route', 'user', 'intent', 'agent'] as const

const COMPLIANCE_NOTES: Record<string, { icon: typeof CheckCircle2; color: string; note: string }> = {
  METADATA_ONLY: {
    icon: CheckCircle2,
    color: 'text-emerald-600 dark:text-emerald-400',
    note: 'Compliant with GDPR Art. 5(1)(c) data minimization. No personal data stored.',
  },
  ERRORS_ONLY: {
    icon: AlertTriangle,
    color: 'text-amber-600 dark:text-amber-400',
    note: 'Error messages may contain PII. Review retention policy.',
  },
  SAMPLED: {
    icon: AlertTriangle,
    color: 'text-amber-600 dark:text-amber-400',
    note: 'Sampled payloads are subject to data retention policies.',
  },
  FULL: {
    icon: AlertTriangle,
    color: 'text-red-600 dark:text-red-400',
    note: 'Full capture requires user consent under GDPR/CCPA. Ensure DPA is in place.',
  },
}

export default function DataCapturePage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''
  const { canManageOrgSettings } = useRole()

  const [tab, setTab] = useState<Tab>('global')

  // Global policy
  const [capturePolicy, setCapturePolicy] = useState<CapturePolicyResponse | null>(null)
  const [privacyMode, setPrivacyMode] = useState('METADATA_ONLY')
  const [sampledRate, setSampledRate] = useState('')
  const [savingPrivacy, setSavingPrivacy] = useState(false)
  const [retention, setRetention] = useState<RetentionPreview | null>(null)
  const [loadingRetention, setLoadingRetention] = useState(false)

  // Scoped policies
  const [scopes, setScopes] = useState<CapturePolicyScope[]>([])
  const [loadingScopes, setLoadingScopes] = useState(false)
  const [showScopeForm, setShowScopeForm] = useState(false)
  const [scopeType, setScopeType] = useState<string>(SCOPE_TYPES[0])
  const [scopeId, setScopeId] = useState('')
  const [scopeMode, setScopeMode] = useState('METADATA_ONLY')
  const [scopeRate, setScopeRate] = useState('')
  const [savingScope, setSavingScope] = useState(false)

  // PII Testing
  const [piiText, setPiiText] = useState('')
  const [piiResult, setPiiResult] = useState<PiiTestResult | null>(null)
  const [testingPii, setTestingPii] = useState(false)

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

  useEffect(() => { loadPolicy() }, [loadPolicy])

  useEffect(() => {
    if (!apiKey || !canManageOrgSettings) return
    setLoadingRetention(true)
    getRetentionPreview(apiKey, privacyMode)
      .then(setRetention)
      .catch(() => setRetention(null))
      .finally(() => setLoadingRetention(false))
  }, [apiKey, canManageOrgSettings, privacyMode])

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
    if (tab === 'scoped') loadScopes()
  }, [tab, loadScopes])

  async function handleSavePrivacy(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setSavingPrivacy(true)
    try {
      const rate =
        privacyMode === 'SAMPLED' && sampledRate.trim()
          ? parseFloat(sampledRate) / 100
          : null
      const updated = await upsertCapturePolicy(apiKey, {
        privacy_mode: privacyMode,
        sampled_rate: rate,
      })
      setCapturePolicy(updated)
      toast.success('Capture policy saved')
    } catch {
      toast.error('Failed to save capture policy')
    } finally {
      setSavingPrivacy(false)
    }
  }

  async function handleCreateScope() {
    if (!apiKey || !scopeId.trim()) return
    setSavingScope(true)
    try {
      await upsertCapturePolicyScope(apiKey, {
        scope_type: scopeType,
        scope_id: scopeId.trim(),
        privacy_mode: scopeMode,
        sampled_rate: scopeMode === 'SAMPLED' && scopeRate.trim() ? parseFloat(scopeRate) / 100 : null,
      })
      toast.success('Scoped policy saved')
      setShowScopeForm(false)
      setScopeId('')
      loadScopes()
    } catch {
      toast.error('Failed to save scoped policy')
    } finally {
      setSavingScope(false)
    }
  }

  async function handleTestPii() {
    if (!apiKey || !piiText.trim()) return
    setTestingPii(true)
    setPiiResult(null)
    try {
      const result = await testPiiRedaction(apiKey, piiText)
      setPiiResult(result)
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
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 dark:bg-indigo-900/40">
          <Database className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Data Capture Policy Studio</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Controls what payload data RunLedger stores. Affects privacy, storage, and compliance.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-slate-100 p-1 dark:bg-slate-800">
        {([
          { key: 'global' as Tab, label: 'Global Policy', icon: Shield },
          { key: 'scoped' as Tab, label: 'Scoped Policies', icon: Eye },
          { key: 'pii' as Tab, label: 'PII Testing', icon: Search },
        ]).map(({ key, label, icon: Icon }) => (
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

      {/* ── Global Policy Tab ──────────────────────────────────────────── */}
      {tab === 'global' && (
        <div className="space-y-4">
          {capturePolicy && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Current:</span>
              <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                {capturePolicy.privacy_mode}
              </span>
              {capturePolicy.sampled_rate && (
                <span className="text-xs text-slate-500">
                  @ {(parseFloat(capturePolicy.sampled_rate) * 100).toFixed(0)}% sample rate
                </span>
              )}
            </div>
          )}

          <form onSubmit={handleSavePrivacy} className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
              Privacy Mode
            </p>
            <div className="flex flex-wrap items-end gap-3">
              <div className="flex flex-col gap-1">
                <select value={privacyMode} onChange={(e) => setPrivacyMode(e.target.value)} className={inputCls}>
                  <option value="METADATA_ONLY">METADATA_ONLY — tokens, model, latency only</option>
                  <option value="ERRORS_ONLY">ERRORS_ONLY — metadata + error messages</option>
                  <option value="SAMPLED">SAMPLED — full payload on a % of runs</option>
                  <option value="FULL">FULL — complete request/response payloads</option>
                </select>
              </div>
              {privacyMode === 'SAMPLED' && (
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-500">Sample rate (%)</label>
                  <input
                    type="number" min="0" max="100" step="1" placeholder="10"
                    value={sampledRate} onChange={(e) => setSampledRate(e.target.value)}
                    className={`w-24 ${inputCls}`} required
                  />
                </div>
              )}
            </div>

            {/* Compliance note */}
            {compliance && (
              <div className="mt-4 flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50/60 p-3 dark:border-slate-700 dark:bg-slate-800/40">
                <ComplianceIcon className={`mt-0.5 h-4 w-4 flex-shrink-0 ${compliance.color}`} />
                <p className={`text-xs ${compliance.color}`}>{compliance.note}</p>
              </div>
            )}

            {privacyMode === 'FULL' && (
              <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
                <strong>FULL</strong> mode stores raw prompts and completions. Ensure you have user consent and appropriate data retention policies before enabling.
              </div>
            )}

            <button type="submit" disabled={savingPrivacy} className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
              {savingPrivacy ? 'Saving…' : 'Save Policy'}
            </button>
          </form>

          {/* Retention Preview */}
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
              Retention Preview
            </p>
            {loadingRetention ? (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading preview…
              </div>
            ) : retention ? (
              <div className="space-y-4">
                <div className="rounded-lg bg-slate-50 px-4 py-3 dark:bg-slate-800/60">
                  <span className="text-xs text-slate-500">Estimated storage</span>
                  <p className="text-lg font-semibold text-slate-900 dark:text-white">
                    {retention.estimated_storage_mb_per_month} MB/month
                  </p>
                </div>
                <div className="flex flex-wrap gap-4">
                  <div>
                    <p className="mb-1 text-xs font-medium text-slate-500">Fields Captured</p>
                    <div className="flex flex-wrap gap-1">
                      {retention.fields_captured.map((f) => (
                        <span key={f} className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-medium text-slate-500">Fields Redacted</p>
                    <div className="flex flex-wrap gap-1">
                      {retention.fields_redacted.map((f) => (
                        <span key={f} className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
                {retention.compliance_notes.length > 0 && (
                  <div>
                    <p className="mb-1 text-xs font-medium text-slate-500">Compliance Notes</p>
                    <ul className="list-inside list-disc space-y-1 text-xs text-slate-600 dark:text-slate-400">
                      {retention.compliance_notes.map((n, i) => (
                        <li key={i}>{n}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-slate-400">Unable to load retention preview.</p>
            )}
          </div>
        </div>
      )}

      {/* ── Scoped Policies Tab ────────────────────────────────────────── */}
      {tab === 'scoped' && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <div className="mb-4 flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                Per-Scope Overrides
              </p>
              <button
                onClick={() => setShowScopeForm(!showScopeForm)}
                className="flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
              >
                <Plus className="h-4 w-4" />
                {showScopeForm ? 'Cancel' : 'Add Scope'}
              </button>
            </div>

            {showScopeForm && (
              <div className="mb-4 flex flex-wrap items-end gap-3 border-b border-slate-200 pb-4 dark:border-slate-700">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-500">Scope Type</label>
                  <select value={scopeType} onChange={(e) => setScopeType(e.target.value)} className={inputCls}>
                    {SCOPE_TYPES.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-500">Scope ID</label>
                  <input
                    type="text" placeholder="e.g. ws_abc123"
                    value={scopeId} onChange={(e) => setScopeId(e.target.value)}
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-500">Privacy Mode</label>
                  <select value={scopeMode} onChange={(e) => setScopeMode(e.target.value)} className={inputCls}>
                    <option value="METADATA_ONLY">METADATA_ONLY</option>
                    <option value="ERRORS_ONLY">ERRORS_ONLY</option>
                    <option value="SAMPLED">SAMPLED</option>
                    <option value="FULL">FULL</option>
                  </select>
                </div>
                {scopeMode === 'SAMPLED' && (
                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-500">Rate (%)</label>
                    <input
                      type="number" min="0" max="100" step="1" placeholder="10"
                      value={scopeRate} onChange={(e) => setScopeRate(e.target.value)}
                      className={`w-20 ${inputCls}`}
                    />
                  </div>
                )}
                <button onClick={handleCreateScope} disabled={savingScope} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                  {savingScope ? 'Saving…' : 'Save'}
                </button>
              </div>
            )}

            {loadingScopes ? (
              <p className="text-sm text-slate-400">Loading…</p>
            ) : scopes.length === 0 ? (
              <p className="text-sm text-slate-400">No scoped overrides. The global policy applies everywhere.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      <th className="pb-2 font-medium text-slate-500">Scope Type</th>
                      <th className="pb-2 font-medium text-slate-500">Scope ID</th>
                      <th className="pb-2 font-medium text-slate-500">Privacy Mode</th>
                      <th className="pb-2 font-medium text-slate-500">Sample Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scopes.map((s, i) => (
                      <tr key={`${s.scope_type}-${s.scope_id}-${i}`} className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-3 font-mono text-xs">{s.scope_type}</td>
                        <td className="py-3 font-mono text-xs">{s.scope_id}</td>
                        <td className="py-3">
                          <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                            {s.privacy_mode}
                          </span>
                        </td>
                        <td className="py-3 text-slate-500">
                          {s.sampled_rate ? `${(parseFloat(s.sampled_rate) * 100).toFixed(0)}%` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── PII Testing Tab ────────────────────────────────────────────── */}
      {tab === 'pii' && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
              Test PII Redaction
            </p>
            <p className="mb-3 text-sm text-slate-500">
              Paste sample text to see how RunLedger detects and redacts personally identifiable information.
            </p>
            <textarea
              value={piiText}
              onChange={(e) => setPiiText(e.target.value)}
              placeholder="e.g. My email is john@example.com and my SSN is 123-45-6789"
              rows={4}
              className={`w-full resize-none ${inputCls}`}
            />
            <button
              onClick={handleTestPii}
              disabled={testingPii || !piiText.trim()}
              className="mt-3 flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {testingPii ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Test Redaction
            </button>
          </div>

          {piiResult && (
            <div className="space-y-4">
              {/* Detected PII */}
              <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Detected PII ({piiResult.detected_pii.length} items)
                </p>
                {piiResult.detected_pii.length === 0 ? (
                  <p className="text-sm text-emerald-600 dark:text-emerald-400">No PII detected in the input text.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {piiResult.detected_pii.map((d, i) => (
                      <div key={i} className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 dark:border-red-900 dark:bg-red-950/30">
                        <span className="text-xs font-semibold text-red-700 dark:text-red-400">{d.type}</span>
                        <p className="mt-0.5 font-mono text-xs text-red-600 dark:text-red-300">{d.value}</p>
                        <p className="mt-0.5 text-xs text-red-400">
                          Confidence: {(Number(d.confidence) * 100).toFixed(0)}%
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Redacted output */}
              <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Redacted Output
                </p>
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
