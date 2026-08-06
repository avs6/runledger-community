'use client'

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Shield, RefreshCw, Trash2 } from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'
import {
  getSecuritySettings,
  updateSecuritySettings,
  listOidcProviders,
  createOidcProvider,
  deleteOidcProvider,
  listIpAclRules,
  createIpAclRule,
  deleteIpAclRule,
  testIpAcl,
} from '@/lib/api'
import type {
  WorkspaceSecuritySettings,
  OIDCProviderResponse,
  IpAclRuleResponse,
} from '@/types/api'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

function parseJsonOrToast(value: string, label: string): Record<string, unknown> | null {
  try {
    return JSON.parse(value || '{}') as Record<string, unknown>
  } catch {
    toast.error(`${label} must be valid JSON`)
    return null
  }
}

export default function SecurityPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { isOrgAdmin, isPlatformAdmin } = useRole()
  const canManage = isOrgAdmin || isPlatformAdmin

  const [settings, setSettings] = useState<WorkspaceSecuritySettings | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [oidcProviders, setOidcProviders] = useState<OIDCProviderResponse[]>([])
  const [ipAclRules, setIpAclRules] = useState<IpAclRuleResponse[]>([])

  const [requiredFields, setRequiredFields] = useState('')
  const [requiredMode, setRequiredMode] = useState('warn')
  const [residencyRegions, setResidencyRegions] = useState('')
  const [callbackConfigStr, setCallbackConfigStr] = useState('{}')
  const [brandConfigStr, setBrandConfigStr] = useState('{}')
  const [oidcSessionConfigStr, setOidcSessionConfigStr] = useState('{}')

  const [oidcName, setOidcName] = useState('')
  const [oidcIssuerUrl, setOidcIssuerUrl] = useState('')
  const [oidcAudience, setOidcAudience] = useState('')
  const [oidcDiscoveryUrl, setOidcDiscoveryUrl] = useState('')
  const [oidcJwksUri, setOidcJwksUri] = useState('')
  const [oidcClaimMappingsStr, setOidcClaimMappingsStr] = useState('{"workspace_id":"workspace_id"}')

  const [scopeType, setScopeType] = useState('workspace')
  const [cidr, setCidr] = useState('')
  const [aclAction, setAclAction] = useState('allow')
  const [teamName, setTeamName] = useState('')
  const [apiKeyId, setApiKeyId] = useState('')
  const [priority, setPriority] = useState('100')
  const [description, setDescription] = useState('')

  const [testIp, setTestIp] = useState('')
  const [testResult, setTestResult] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!apiKey || !canManage) return
    setLoading(true)
    try {
      const [settingsData, providersData, rulesData] = await Promise.all([
        getSecuritySettings(apiKey),
        listOidcProviders(apiKey),
        listIpAclRules(apiKey),
      ])
      setSettings(settingsData)
      setRequiredFields(settingsData.required_metadata_fields.join(', '))
      setRequiredMode(settingsData.required_metadata_mode)
      setResidencyRegions(settingsData.data_residency_regions.join(', '))
      setCallbackConfigStr(JSON.stringify(settingsData.callback_config ?? {}, null, 2))
      setBrandConfigStr(JSON.stringify(settingsData.brand_config ?? {}, null, 2))
      setOidcSessionConfigStr(JSON.stringify(settingsData.oidc_session_config ?? {}, null, 2))
      setOidcProviders(providersData.items)
      setIpAclRules(rulesData.items)
    } catch {
      toast.error('Failed to load enterprise security settings')
    } finally {
      setLoading(false)
    }
  }, [apiKey, canManage])

  useEffect(() => { void load() }, [load])

  async function handleSaveSettings() {
    if (!apiKey) return
    const callbackConfig = parseJsonOrToast(callbackConfigStr, 'Callback config')
    const brandConfig = parseJsonOrToast(brandConfigStr, 'Brand config')
    const oidcSessionConfig = parseJsonOrToast(oidcSessionConfigStr, 'OIDC session config')
    if (!callbackConfig || !brandConfig || !oidcSessionConfig) return
    setSaving(true)
    try {
      const updated = await updateSecuritySettings(apiKey, {
        required_metadata_fields: requiredFields.split(',').map((v) => v.trim()).filter(Boolean),
        required_metadata_mode: requiredMode,
        data_residency_regions: residencyRegions.split(',').map((v) => v.trim()).filter(Boolean),
        callback_config: callbackConfig,
        brand_config: brandConfig,
        oidc_session_config: oidcSessionConfig,
      })
      setSettings(updated)
      toast.success('Security settings saved')
    } catch {
      toast.error('Failed to save security settings')
    } finally {
      setSaving(false)
    }
  }

  async function handleCreateOidcProvider(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    const claimMappings = parseJsonOrToast(oidcClaimMappingsStr, 'OIDC claim mappings')
    if (!claimMappings) return
    try {
      const created = await createOidcProvider(apiKey, {
        name: oidcName.trim(),
        issuer_url: oidcIssuerUrl.trim(),
        audience: oidcAudience.trim() || null,
        discovery_url: oidcDiscoveryUrl.trim() || null,
        jwks_uri: oidcJwksUri.trim() || null,
        claim_mappings: claimMappings,
      })
      setOidcProviders((prev) => [...prev, created])
      setOidcName('')
      setOidcIssuerUrl('')
      setOidcAudience('')
      setOidcDiscoveryUrl('')
      setOidcJwksUri('')
      setOidcClaimMappingsStr('{"workspace_id":"workspace_id"}')
      toast.success('OIDC provider added')
    } catch {
      toast.error('Failed to add OIDC provider')
    }
  }

  async function handleDeleteOidcProvider(id: string) {
    if (!apiKey || !confirm('Delete this OIDC provider?')) return
    try {
      await deleteOidcProvider(apiKey, id)
      setOidcProviders((prev) => prev.filter((item) => item.id !== id))
    } catch {
      toast.error('Failed to delete OIDC provider')
    }
  }

  async function handleCreateIpAclRule(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    try {
      const created = await createIpAclRule(apiKey, {
        scope_type: scopeType,
        cidr: cidr.trim(),
        action: aclAction,
        team_name: teamName.trim() || null,
        api_key_id: apiKeyId.trim() || null,
        priority: parseInt(priority, 10) || 100,
        description: description.trim() || null,
      })
      setIpAclRules((prev) => [...prev, created])
      setCidr('')
      setTeamName('')
      setApiKeyId('')
      setPriority('100')
      setDescription('')
      toast.success('IP ACL rule created')
    } catch {
      toast.error('Failed to create IP ACL rule')
    }
  }

  async function handleDeleteIpAclRule(id: string) {
    if (!apiKey || !confirm('Delete this IP ACL rule?')) return
    try {
      await deleteIpAclRule(apiKey, id)
      setIpAclRules((prev) => prev.filter((item) => item.id !== id))
    } catch {
      toast.error('Failed to delete IP ACL rule')
    }
  }

  async function handleTestIp() {
    if (!apiKey || !testIp.trim()) return
    try {
      const result = await testIpAcl(apiKey, { ip: testIp.trim() })
      setTestResult(result.allowed ? 'Allowed' : 'Denied')
    } catch {
      toast.error('Failed to run ACL simulation')
    }
  }

  if (!canManage) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Security</h1>
        <p className="mt-4 text-sm text-slate-500">Enterprise security controls require org-admin access.</p>
      </div>
    )
  }

  return (
    <div className="space-y-8 p-8 max-w-6xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            <h1 className="text-2xl font-bold tracking-tight dark:text-white">Enterprise Security</h1>
          </div>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Control OIDC gateway auth, IP allow and deny policies, required metadata, callback routing, and residency posture.
          </p>
        </div>
        <button
          onClick={() => void load()}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <section className="grid gap-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4 lg:grid-cols-2">
        <div className="lg:col-span-2">
          <h2 className="text-base font-semibold dark:text-white">Workspace Security Posture</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Set request metadata enforcement, team callback routing defaults, branding, and residency constraints.
          </p>
        </div>
        <label className="text-sm">
          <span className="mb-1 block text-xs text-slate-500 dark:text-slate-400">Required metadata fields</span>
          <input value={requiredFields} onChange={(e) => setRequiredFields(e.target.value)} className={inputCls + ' w-full'} placeholder="user_id, session_id, team" />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs text-slate-500 dark:text-slate-400">Enforcement mode</span>
          <select value={requiredMode} onChange={(e) => setRequiredMode(e.target.value)} className={inputCls + ' w-full'}>
            <option value="warn">Warn only</option>
            <option value="reject">Reject request</option>
          </select>
        </label>
        <label className="text-sm lg:col-span-2">
          <span className="mb-1 block text-xs text-slate-500 dark:text-slate-400">Residency regions</span>
          <input value={residencyRegions} onChange={(e) => setResidencyRegions(e.target.value)} className={inputCls + ' w-full'} placeholder="us, eu-west-1" />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs text-slate-500 dark:text-slate-400">Callback config JSON</span>
          <textarea value={callbackConfigStr} onChange={(e) => setCallbackConfigStr(e.target.value)} className={inputCls + ' min-h-[150px] w-full'} />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs text-slate-500 dark:text-slate-400">Brand config JSON</span>
          <textarea value={brandConfigStr} onChange={(e) => setBrandConfigStr(e.target.value)} className={inputCls + ' min-h-[150px] w-full'} />
        </label>
        <label className="text-sm lg:col-span-2">
          <span className="mb-1 block text-xs text-slate-500 dark:text-slate-400">OIDC session config JSON</span>
          <textarea value={oidcSessionConfigStr} onChange={(e) => setOidcSessionConfigStr(e.target.value)} className={inputCls + ' min-h-[120px] w-full'} />
        </label>
        <div className="lg:col-span-2">
          <button onClick={() => void handleSaveSettings()} disabled={saving || !settings} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
            {saving ? 'Saving...' : 'Save security settings'}
          </button>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
          <div>
            <h2 className="text-base font-semibold dark:text-white">OIDC Providers</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Add external issuers for gateway-level bearer auth with custom claim mapping.
            </p>
          </div>
          <form onSubmit={handleCreateOidcProvider} className="grid gap-3">
            <input value={oidcName} onChange={(e) => setOidcName(e.target.value)} className={inputCls} placeholder="Okta production" required />
            <input value={oidcIssuerUrl} onChange={(e) => setOidcIssuerUrl(e.target.value)} className={inputCls} placeholder="https://issuer.example.com" required />
            <input value={oidcAudience} onChange={(e) => setOidcAudience(e.target.value)} className={inputCls} placeholder="Audience (optional)" />
            <input value={oidcDiscoveryUrl} onChange={(e) => setOidcDiscoveryUrl(e.target.value)} className={inputCls} placeholder="Discovery URL (optional)" />
            <input value={oidcJwksUri} onChange={(e) => setOidcJwksUri(e.target.value)} className={inputCls} placeholder="JWKS URI (optional)" />
            <textarea value={oidcClaimMappingsStr} onChange={(e) => setOidcClaimMappingsStr(e.target.value)} className={inputCls + ' min-h-[100px]'} />
            <button type="submit" className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">
              Add OIDC provider
            </button>
          </form>
          <div className="space-y-2">
            {oidcProviders.length === 0 ? (
              <p className="text-sm text-slate-400">No OIDC providers configured.</p>
            ) : (
              oidcProviders.map((provider) => (
                <div key={provider.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 dark:border-slate-700 p-3">
                  <div className="min-w-0">
                    <p className="font-medium dark:text-slate-100">{provider.name}</p>
                    <p className="mt-1 text-xs font-mono text-slate-500 dark:text-slate-400 break-all">{provider.issuer_url}</p>
                    <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                      audience {provider.audience ?? 'unset'} · {provider.is_active ? 'active' : 'inactive'}
                    </p>
                  </div>
                  <button onClick={() => void handleDeleteOidcProvider(provider.id)} className="rounded-lg border border-red-200 p-2 text-red-600 hover:bg-red-50 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/30">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="space-y-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
          <div>
            <h2 className="text-base font-semibold dark:text-white">IP ACLs</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Allow or deny by workspace, key, or team, then simulate request outcomes before you roll changes out.
            </p>
          </div>
          <form onSubmit={handleCreateIpAclRule} className="grid gap-3 sm:grid-cols-2">
            <select value={scopeType} onChange={(e) => setScopeType(e.target.value)} className={inputCls}>
              <option value="workspace">workspace</option>
              <option value="team">team</option>
              <option value="api_key">api_key</option>
              <option value="global">global</option>
            </select>
            <select value={aclAction} onChange={(e) => setAclAction(e.target.value)} className={inputCls}>
              <option value="allow">allow</option>
              <option value="deny">deny</option>
            </select>
            <input value={cidr} onChange={(e) => setCidr(e.target.value)} className={inputCls + ' sm:col-span-2'} placeholder="203.0.113.0/24" required />
            <input value={teamName} onChange={(e) => setTeamName(e.target.value)} className={inputCls} placeholder="Team name (optional)" />
            <input value={apiKeyId} onChange={(e) => setApiKeyId(e.target.value)} className={inputCls} placeholder="API key ID (optional)" />
            <input value={priority} onChange={(e) => setPriority(e.target.value)} className={inputCls} placeholder="100" />
            <input value={description} onChange={(e) => setDescription(e.target.value)} className={inputCls} placeholder="Description" />
            <div className="sm:col-span-2">
              <button type="submit" className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">
                Add ACL rule
              </button>
            </div>
          </form>

          <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Policy Simulator</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <input value={testIp} onChange={(e) => setTestIp(e.target.value)} className={inputCls + ' min-w-[220px]'} placeholder="198.51.100.10" />
              <button onClick={() => void handleTestIp()} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                Simulate
              </button>
              {testResult && <span className={`rounded-full px-2 py-1 text-xs font-semibold ${testResult === 'Allowed' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'}`}>{testResult}</span>}
            </div>
          </div>

          <div className="space-y-2">
            {ipAclRules.length === 0 ? (
              <p className="text-sm text-slate-400">No IP ACL rules configured.</p>
            ) : (
              ipAclRules.map((rule) => (
                <div key={rule.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 dark:border-slate-700 p-3">
                  <div>
                    <p className="font-mono text-sm dark:text-slate-100">{rule.cidr}</p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {rule.action} · {rule.scope_type} · priority {rule.priority}{rule.team_name ? ` · team ${rule.team_name}` : ''}
                    </p>
                    {rule.description && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{rule.description}</p>}
                  </div>
                  <button onClick={() => void handleDeleteIpAclRule(rule.id)} className="rounded-lg border border-red-200 p-2 text-red-600 hover:bg-red-50 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/30">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
