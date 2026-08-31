'use client'

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Building2, Layers, Link2, Pencil, Radio, RefreshCw, Shield, Trash2, X } from 'lucide-react'
import Link from 'next/link'
import { useRole } from '@/components/rbac/useRole'
import {
  createIpAclRule,
  createOidcProvider,
  deleteIpAclRule,
  deleteOidcProvider,
  getSecuritySettings,
  listIpAclRules,
  listOidcProviders,
  testIpAcl,
  updateIpAclRule,
  updateOidcProvider,
  updateSecuritySettings,
  getDataProtectionOrgPosture,
  getDataProtectionGatewayPosture,
  getGovernanceInternalPosture,
  getSecurityRuntimePosture,
} from '@/lib/api'
import type { IpAclRuleResponse, OIDCProviderResponse, WorkspaceSecuritySettings, DataProtectionOrgPosture, DataProtectionGatewayPosture, GovernanceInternalPosture, SecurityRuntimePosture } from '@/types/api'

const inputCls =
  'rounded border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder:text-gray-500 dark:focus:ring-indigo-400'

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

  const [editingOidcId, setEditingOidcId] = useState<string | null>(null)
  const [oidcName, setOidcName] = useState('')
  const [oidcIssuerUrl, setOidcIssuerUrl] = useState('')
  const [oidcAudience, setOidcAudience] = useState('')
  const [oidcDiscoveryUrl, setOidcDiscoveryUrl] = useState('')
  const [oidcJwksUri, setOidcJwksUri] = useState('')
  const [oidcClaimMappingsStr, setOidcClaimMappingsStr] = useState('{"workspace_id":"workspace_id"}')
  const [oidcIsActive, setOidcIsActive] = useState(true)

  const [editingAclId, setEditingAclId] = useState<string | null>(null)
  const [scopeType, setScopeType] = useState('workspace')
  const [cidr, setCidr] = useState('')
  const [aclAction, setAclAction] = useState('allow')
  const [apiKeyId, setApiKeyId] = useState('')
  const [priority, setPriority] = useState('100')
  const [description, setDescription] = useState('')

  const [testIp, setTestIp] = useState('')
  const [testResult, setTestResult] = useState<string | null>(null)
  const [orgPosture, setOrgPosture] = useState<DataProtectionOrgPosture | null>(null)
  const [gatewayPosture, setGatewayPosture] = useState<DataProtectionGatewayPosture | null>(null)
  const [govInternal, setGovInternal] = useState<GovernanceInternalPosture | null>(null)
  const [runtimePosture, setRuntimePosture] = useState<SecurityRuntimePosture | null>(null)

  const resetOidcForm = useCallback(() => {
    setEditingOidcId(null)
    setOidcName('')
    setOidcIssuerUrl('')
    setOidcAudience('')
    setOidcDiscoveryUrl('')
    setOidcJwksUri('')
    setOidcClaimMappingsStr('{"workspace_id":"workspace_id"}')
    setOidcIsActive(true)
  }, [])

  const resetAclForm = useCallback(() => {
    setEditingAclId(null)
    setScopeType('workspace')
    setCidr('')
    setAclAction('allow')
    setApiKeyId('')
    setPriority('100')
    setDescription('')
  }, [])

  const load = useCallback(async () => {
    if (!apiKey || !canManage) return
    setLoading(true)
    try {
      const [settingsData, providersData, rulesData, orgP, gwP, govInt, rtP] = await Promise.all([
        getSecuritySettings(apiKey),
        listOidcProviders(apiKey),
        listIpAclRules(apiKey),
        getDataProtectionOrgPosture(apiKey).catch(() => null),
        getDataProtectionGatewayPosture(apiKey).catch(() => null),
        getGovernanceInternalPosture(apiKey).catch(() => null),
        getSecurityRuntimePosture(apiKey).catch(() => null),
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
      setOrgPosture(orgP)
      setGatewayPosture(gwP)
      setGovInternal(govInt)
      setRuntimePosture(rtP)
    } catch {
      toast.error('Failed to load enterprise security settings')
    } finally {
      setLoading(false)
    }
  }, [apiKey, canManage])

  useEffect(() => {
    void load()
  }, [load])

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

  async function handleSaveOidcProvider(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    const claimMappings = parseJsonOrToast(oidcClaimMappingsStr, 'OIDC claim mappings')
    if (!claimMappings) return
    try {
      if (editingOidcId) {
        const updated = await updateOidcProvider(apiKey, editingOidcId, {
          name: oidcName.trim(),
          issuer_url: oidcIssuerUrl.trim(),
          audience: oidcAudience.trim() || null,
          discovery_url: oidcDiscoveryUrl.trim() || null,
          jwks_uri: oidcJwksUri.trim() || null,
          claim_mappings: claimMappings,
          is_active: oidcIsActive,
        })
        setOidcProviders((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
        toast.success('OIDC provider updated')
      } else {
        const created = await createOidcProvider(apiKey, {
          name: oidcName.trim(),
          issuer_url: oidcIssuerUrl.trim(),
          audience: oidcAudience.trim() || null,
          discovery_url: oidcDiscoveryUrl.trim() || null,
          jwks_uri: oidcJwksUri.trim() || null,
          claim_mappings: claimMappings,
          is_active: oidcIsActive,
        })
        setOidcProviders((prev) => [...prev, created])
        toast.success('OIDC provider added')
      }
      resetOidcForm()
    } catch {
      toast.error(editingOidcId ? 'Failed to update OIDC provider' : 'Failed to add OIDC provider')
    }
  }

  function startEditOidcProvider(provider: OIDCProviderResponse) {
    setEditingOidcId(provider.id)
    setOidcName(provider.name)
    setOidcIssuerUrl(provider.issuer_url)
    setOidcAudience(provider.audience ?? '')
    setOidcDiscoveryUrl(provider.discovery_url ?? '')
    setOidcJwksUri(provider.jwks_uri ?? '')
    setOidcClaimMappingsStr(JSON.stringify(provider.claim_mappings ?? {}, null, 2))
    setOidcIsActive(provider.is_active)
  }

  async function handleDeleteOidcProvider(id: string) {
    if (!apiKey || !confirm('Delete this OIDC provider?')) return
    try {
      await deleteOidcProvider(apiKey, id)
      setOidcProviders((prev) => prev.filter((item) => item.id !== id))
      if (editingOidcId === id) resetOidcForm()
      toast.success('OIDC provider deleted')
    } catch {
      toast.error('Failed to delete OIDC provider')
    }
  }

  async function handleSaveIpAclRule(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    try {
      if (editingAclId) {
        const updated = await updateIpAclRule(apiKey, editingAclId, {
          api_key_id: apiKeyId.trim() || null,
          cidr: cidr.trim(),
          action: aclAction,
          priority: parseInt(priority, 10) || 100,
          description: description.trim() || null,
        })
        setIpAclRules((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
        toast.success('IP ACL rule updated')
      } else {
        const created = await createIpAclRule(apiKey, {
          scope_type: scopeType,
          cidr: cidr.trim(),
          action: aclAction,
          api_key_id: apiKeyId.trim() || null,
          priority: parseInt(priority, 10) || 100,
          description: description.trim() || null,
        })
        setIpAclRules((prev) => [...prev, created])
        toast.success('IP ACL rule created')
      }
      resetAclForm()
    } catch {
      toast.error(editingAclId ? 'Failed to update IP ACL rule' : 'Failed to create IP ACL rule')
    }
  }

  function startEditIpAclRule(rule: IpAclRuleResponse) {
    setEditingAclId(rule.id)
    setScopeType(rule.scope_type)
    setCidr(rule.cidr)
    setAclAction(rule.action)
    setApiKeyId(rule.api_key_id ?? '')
    setPriority(String(rule.priority))
    setDescription(rule.description ?? '')
  }

  async function handleDeleteIpAclRule(id: string) {
    if (!apiKey || !confirm('Delete this IP ACL rule?')) return
    try {
      await deleteIpAclRule(apiKey, id)
      setIpAclRules((prev) => prev.filter((item) => item.id !== id))
      if (editingAclId === id) resetAclForm()
      toast.success('IP ACL rule deleted')
    } catch {
      toast.error('Failed to delete IP ACL rule')
    }
  }

  async function handleTestIp() {
    if (!apiKey || !testIp.trim()) return
    try {
      const result = await testIpAcl(apiKey, { ip: testIp.trim(), api_key_id: apiKeyId.trim() || null })
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
    <div className="max-w-6xl space-y-8 p-8">
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
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
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
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Access Groups</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.access_group_context.total_groups}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Security Events (30d)</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.security_context.security_events_30d}</p>
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
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Audit Events 30d</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.audit_context.audit_events_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Active Tags</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.tags_context.active_tags}</p>
              <p className="text-xs text-slate-500">{govInternal.tags_context.total_tags} total</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/tool-registry" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tool Registry</Link>
            <Link href="/tool-policies" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tool Policies</Link>
            <Link href="/approvals" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Approvals</Link>
            <Link href="/data-capture" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Data Capture</Link>
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
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Security Events 30d</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.identity_context.security_events_30d}</p>
              <p className="text-xs text-slate-500">{runtimePosture.identity_context.workspace_users} workspace users</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Guardrail Events 30d</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.gateway_posture.guardrail_events_30d}</p>
              <p className="text-xs text-slate-500">{runtimePosture.gateway_posture.guardrail_rules} rules active</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Alert Firings 30d</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.monitoring_context.alert_firings_30d}</p>
              <p className="text-xs text-slate-500">{runtimePosture.monitoring_context.active_alert_rules} rules active</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-cyan-700 dark:text-cyan-300">Chargeback Rules</p>
              <p className="mt-1 text-2xl font-bold text-cyan-900 dark:text-cyan-50">{runtimePosture.finops_context.chargeback_rules}</p>
              <p className="text-xs text-slate-500">{runtimePosture.finops_context.ledger_snapshots} ledger snapshots</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/organization" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Organization</Link>
            <Link href="/workspaces" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Workspaces</Link>
            <Link href="/api-keys" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">API Keys</Link>
            <Link href="/model-gateway" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Model Gateway</Link>
            <Link href="/guardrails" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Guardrails</Link>
            <Link href="/alert-rules" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Alert Rules</Link>
            <Link href="/chargeback" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Chargeback</Link>
            <Link href="/ledger" className="text-cyan-700 underline underline-offset-2 hover:text-cyan-900 dark:text-cyan-300 dark:hover:text-cyan-100">Ledger</Link>
          </div>
        </div>
      )}

      <section className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800/40 lg:grid-cols-2">
        <div className="lg:col-span-2">
          <h2 className="text-base font-semibold dark:text-white">Workspace Security Posture</h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Set request metadata enforcement, callback routing defaults, branding, and residency constraints.
          </p>
        </div>
        <label className="text-sm">
          <span className="mb-1 block text-xs text-slate-500 dark:text-slate-400">Required metadata fields</span>
          <input value={requiredFields} onChange={(e) => setRequiredFields(e.target.value)} className={`${inputCls} w-full`} placeholder="user_id, session_id, workflow_id" />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs text-slate-500 dark:text-slate-400">Enforcement mode</span>
          <select value={requiredMode} onChange={(e) => setRequiredMode(e.target.value)} className={`${inputCls} w-full`}>
            <option value="warn">Warn only</option>
            <option value="reject">Reject request</option>
          </select>
        </label>
        <label className="text-sm lg:col-span-2">
          <span className="mb-1 block text-xs text-slate-500 dark:text-slate-400">Residency regions</span>
          <input value={residencyRegions} onChange={(e) => setResidencyRegions(e.target.value)} className={`${inputCls} w-full`} placeholder="us, eu-west-1" />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs text-slate-500 dark:text-slate-400">Callback config JSON</span>
          <textarea value={callbackConfigStr} onChange={(e) => setCallbackConfigStr(e.target.value)} className={`${inputCls} min-h-[150px] w-full`} />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs text-slate-500 dark:text-slate-400">Brand config JSON</span>
          <textarea value={brandConfigStr} onChange={(e) => setBrandConfigStr(e.target.value)} className={`${inputCls} min-h-[150px] w-full`} />
        </label>
        <label className="text-sm lg:col-span-2">
          <span className="mb-1 block text-xs text-slate-500 dark:text-slate-400">OIDC session config JSON</span>
          <textarea value={oidcSessionConfigStr} onChange={(e) => setOidcSessionConfigStr(e.target.value)} className={`${inputCls} min-h-[120px] w-full`} />
        </label>
        <div className="lg:col-span-2">
          <button onClick={() => void handleSaveSettings()} disabled={saving || !settings} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
            {saving ? 'Saving...' : 'Save security settings'}
          </button>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800/40">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold dark:text-white">OIDC Providers</h2>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                Manage external issuers for gateway-level bearer auth and claim mapping.
              </p>
            </div>
            {editingOidcId && (
              <button onClick={resetOidcForm} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700">
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          <form onSubmit={handleSaveOidcProvider} className="grid gap-3">
            <input value={oidcName} onChange={(e) => setOidcName(e.target.value)} className={inputCls} placeholder="Okta production" required />
            <input value={oidcIssuerUrl} onChange={(e) => setOidcIssuerUrl(e.target.value)} className={inputCls} placeholder="https://issuer.example.com" required />
            <input value={oidcAudience} onChange={(e) => setOidcAudience(e.target.value)} className={inputCls} placeholder="Audience (optional)" />
            <input value={oidcDiscoveryUrl} onChange={(e) => setOidcDiscoveryUrl(e.target.value)} className={inputCls} placeholder="Discovery URL (optional)" />
            <input value={oidcJwksUri} onChange={(e) => setOidcJwksUri(e.target.value)} className={inputCls} placeholder="JWKS URI (optional)" />
            <textarea value={oidcClaimMappingsStr} onChange={(e) => setOidcClaimMappingsStr(e.target.value)} className={`${inputCls} min-h-[100px]`} />
            <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <input type="checkbox" checked={oidcIsActive} onChange={(e) => setOidcIsActive(e.target.checked)} />
              Active
            </label>
            <button type="submit" className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">
              {editingOidcId ? 'Save OIDC provider' : 'Add OIDC provider'}
            </button>
          </form>
          <div className="space-y-2">
            {oidcProviders.length === 0 ? (
              <p className="text-sm text-slate-400">No OIDC providers configured.</p>
            ) : (
              oidcProviders.map((provider) => (
                <div key={provider.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                  <div className="min-w-0">
                    <p className="font-medium dark:text-slate-100">{provider.name}</p>
                    <p className="mt-1 break-all font-mono text-xs text-slate-500 dark:text-slate-400">{provider.issuer_url}</p>
                    <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                      audience {provider.audience ?? 'unset'} · {provider.is_active ? 'active' : 'inactive'}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => startEditOidcProvider(provider)} className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700">
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button onClick={() => void handleDeleteOidcProvider(provider.id)} className="rounded-lg border border-red-200 p-2 text-red-600 hover:bg-red-50 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/30">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800/40">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold dark:text-white">IP ACLs</h2>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                Allow or deny traffic by workspace, key, or global scope, then simulate request outcomes.
              </p>
            </div>
            {editingAclId && (
              <button onClick={resetAclForm} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700">
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          <form onSubmit={handleSaveIpAclRule} className="grid gap-3 sm:grid-cols-2">
            <select value={scopeType} onChange={(e) => setScopeType(e.target.value)} className={inputCls} disabled={Boolean(editingAclId)}>
              <option value="workspace">workspace</option>
              <option value="api_key">api_key</option>
              <option value="global">global</option>
            </select>
            <select value={aclAction} onChange={(e) => setAclAction(e.target.value)} className={inputCls}>
              <option value="allow">allow</option>
              <option value="deny">deny</option>
            </select>
            <input value={cidr} onChange={(e) => setCidr(e.target.value)} className={`${inputCls} sm:col-span-2`} placeholder="203.0.113.0/24" required />
            <input value={apiKeyId} onChange={(e) => setApiKeyId(e.target.value)} className={`${inputCls} sm:col-span-2`} placeholder="API key ID (optional)" />
            <input value={priority} onChange={(e) => setPriority(e.target.value)} className={inputCls} placeholder="100" />
            <input value={description} onChange={(e) => setDescription(e.target.value)} className={inputCls} placeholder="Description" />
            <div className="sm:col-span-2">
              <button type="submit" className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">
                {editingAclId ? 'Save ACL rule' : 'Add ACL rule'}
              </button>
            </div>
          </form>

          <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Policy Simulator</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <input value={testIp} onChange={(e) => setTestIp(e.target.value)} className={`${inputCls} min-w-[220px]`} placeholder="198.51.100.10" />
              <button onClick={() => void handleTestIp()} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700">
                Simulate
              </button>
              {testResult && (
                <span className={`rounded-full px-2 py-1 text-xs font-semibold ${testResult === 'Allowed' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'}`}>
                  {testResult}
                </span>
              )}
            </div>
          </div>

          <div className="space-y-2">
            {ipAclRules.length === 0 ? (
              <p className="text-sm text-slate-400">No IP ACL rules configured.</p>
            ) : (
              ipAclRules.map((rule) => (
                <div key={rule.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                  <div>
                    <p className="font-mono text-sm dark:text-slate-100">{rule.cidr}</p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {rule.action} · {rule.scope_type} · priority {rule.priority}
                    </p>
                    {rule.description && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{rule.description}</p>}
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => startEditIpAclRule(rule)} className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700">
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button onClick={() => void handleDeleteIpAclRule(rule.id)} className="rounded-lg border border-red-200 p-2 text-red-600 hover:bg-red-50 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/30">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
