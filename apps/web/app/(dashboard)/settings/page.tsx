'use client'

import { useSession } from 'next-auth/react'
import { useTheme } from 'next-themes'
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import type { AlertRule, AlertFiring, ApiKeyResponse, ProviderPricingResponse, TenantResponse, AdminWorkspaceResponse, CapturePolicyResponse, GatewayRoute, GatewayStats } from '@/types/api'
import {
  listApiKeys,
  createApiKey,
  revokeApiKey,
  repriceProvider,
  listProviderPricing,
  createProviderPricing,
  updateProviderPricing,
  deleteProviderPricing,
  createGlobalPricing,
  updateGlobalPricing,
  deleteGlobalPricing,
  testSlackWebhook,
  getCapturePolicy,
  upsertCapturePolicy,
  listTenants,
  createTenant,
  listAdminWorkspaces,
  createAdminWorkspace,
  listAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  listAlertHistory,
  listGatewayRoutes,
  createGatewayRoute,
  updateGatewayRoute,
  deleteGatewayRoute,
  getGatewayStats,
} from '@/lib/api'

interface EditState {
  id: string
  isGlobal: boolean
  input: string
  output: string
  cached: string
}

// Shared input/select class with full dark mode support
const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

export default function SettingsPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { theme, setTheme } = useTheme()

  // ── API Keys ────────────────────────────────────────────────────────────────
  const [apiKeys, setApiKeys] = useState<ApiKeyResponse[]>([])
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyEnv, setNewKeyEnv] = useState('dev')
  const [creatingKey, setCreatingKey] = useState(false)
  const [newRawKey, setNewRawKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  // ── Provider pricing ────────────────────────────────────────────────────────
  const [pricing, setPricing] = useState<ProviderPricingResponse[]>([])
  const [newProvider, setNewProvider] = useState('')
  const [newModel, setNewModel] = useState('')
  const [newInputCost, setNewInputCost] = useState('')
  const [newOutputCost, setNewOutputCost] = useState('')
  const [newCachedCost, setNewCachedCost] = useState('')
  const [addingPricing, setAddingPricing] = useState(false)
  const [editState, setEditState] = useState<EditState | null>(null)
  const [savingEdit, setSavingEdit] = useState(false)

  // ── Integrations ────────────────────────────────────────────────────────────
  const [slackWebhookUrl, setSlackWebhookUrl] = useState('')
  const [slackTestResult, setSlackTestResult] = useState<{ ok: boolean; error: string | null } | null>(null)
  const [testingSlack, setTestingSlack] = useState(false)

  // ── Privacy capture policy ──────────────────────────────────────────────────
  const [capturePolicy, setCapturePolicy] = useState<CapturePolicyResponse | null>(null)
  const [privacyMode, setPrivacyMode] = useState('METADATA_ONLY')
  const [sampledRate, setSampledRate] = useState('')
  const [savingPrivacy, setSavingPrivacy] = useState(false)

  // ── Tenant management ───────────────────────────────────────────────────────
  const [adminSecret, setAdminSecret] = useState(process.env.NEXT_PUBLIC_ADMIN_SECRET ?? '')
  const [adminAuthed, setAdminAuthed] = useState(false)
  const [tenants, setTenants] = useState<TenantResponse[]>([])
  const [newTenantSlug, setNewTenantSlug] = useState('')
  const [newTenantName, setNewTenantName] = useState('')
  const [newTenantPlan, setNewTenantPlan] = useState('free')
  const [creatingTenant, setCreatingTenant] = useState(false)
  // Workspace management (within tenant management)
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null)
  const [workspaces, setWorkspaces] = useState<AdminWorkspaceResponse[]>([])
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false)
  const [newWorkspaceName, setNewWorkspaceName] = useState('')
  const [creatingWorkspace, setCreatingWorkspace] = useState(false)

  // ── Alert Rules ──────────────────────────────────────────────────────────────
  const [alertRules, setAlertRules] = useState<AlertRule[]>([])
  const [alertHistory, setAlertHistory] = useState<AlertFiring[]>([])
  const [newAlertName, setNewAlertName] = useState('')
  const [newAlertMetric, setNewAlertMetric] = useState('error_rate')
  const [newAlertOperator, setNewAlertOperator] = useState('gt')
  const [newAlertThreshold, setNewAlertThreshold] = useState('')
  const [newAlertWindow, setNewAlertWindow] = useState('60')
  const [creatingAlert, setCreatingAlert] = useState(false)

  // ── Model Gateway ─────────────────────────────────────────────────────────────
  const [gatewayRoutes, setGatewayRoutes] = useState<GatewayRoute[]>([])
  const [gatewayStats, setGatewayStats] = useState<GatewayStats | null>(null)
  const [newRouteAlias, setNewRouteAlias] = useState('')
  const [newRouteProvider, setNewRouteProvider] = useState('openai')
  const [newRouteTargetModel, setNewRouteTargetModel] = useState('')
  const [newRouteBaseUrl, setNewRouteBaseUrl] = useState('')
  const [newRouteApiKeyEnvVar, setNewRouteApiKeyEnvVar] = useState('OPENAI_API_KEY')
  const [newRoutePriority, setNewRoutePriority] = useState('10')
  const [creatingRoute, setCreatingRoute] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey) return
    try {
      const [keys, pricingData, policy, alertsData, historyData, routesData, statsData] = await Promise.all([
        listApiKeys(apiKey),
        listProviderPricing(apiKey),
        getCapturePolicy(apiKey),
        listAlertRules(apiKey, true),
        listAlertHistory(apiKey, 10),
        listGatewayRoutes(apiKey, true),
        getGatewayStats(apiKey),
      ])
      setApiKeys(keys.filter((k) => !k.is_session))
      setPricing(pricingData.items)
      if (policy) {
        setCapturePolicy(policy)
        setPrivacyMode(policy.privacy_mode)
        setSampledRate(policy.sampled_rate ? String(parseFloat(policy.sampled_rate) * 100) : '')
      }
      setAlertRules(alertsData.items)
      setAlertHistory(historyData.items)
      setGatewayRoutes(routesData.items)
      setGatewayStats(statsData)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load settings')
    }
  }, [apiKey])

  useEffect(() => {
    load()
  }, [load])

  // ── API Key handlers ────────────────────────────────────────────────────────

  async function handleCreateKey(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setCreatingKey(true)
    try {
      const created = await createApiKey(apiKey, {
        name: newKeyName.trim() || null,
        environment: newKeyEnv,
        scopes: [],
        created_by: session?.user?.email ?? null,
      })
      setNewRawKey(created.key)
      setCopied(false)
      setApiKeys((prev) => [created, ...prev])
      setNewKeyName('')
      setNewKeyEnv('dev')
      toast.success('API key created — save it now')
    } catch (err) {
      console.error(err)
      toast.error('Failed to create API key')
    } finally {
      setCreatingKey(false)
    }
  }

  async function handleRevoke(keyId: string) {
    if (!apiKey) return
    if (!confirm('Revoke this API key? This cannot be undone.')) return
    try {
      await revokeApiKey(apiKey, keyId)
      setApiKeys((prev) => prev.filter((k) => k.id !== keyId))
      if (newRawKey) setNewRawKey(null)
      toast.success('API key revoked')
    } catch (err) {
      console.error(err)
      toast.error('Failed to revoke API key')
    }
  }

  async function handleCopy() {
    if (!newRawKey) return
    await navigator.clipboard.writeText(newRawKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // ── Provider pricing handlers ───────────────────────────────────────────────

  async function handleAddPricing(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !newProvider.trim() || !newModel.trim()) return
    setAddingPricing(true)
    try {
      const created = await createProviderPricing(apiKey, {
        provider: newProvider.trim(),
        model: newModel.trim(),
        input_cost_per_1m: newInputCost,
        output_cost_per_1m: newOutputCost,
        cached_input_cost_per_1m: newCachedCost.trim() || null,
      })
      setPricing((prev) => [created, ...prev])
      setNewProvider('')
      setNewModel('')
      setNewInputCost('')
      setNewOutputCost('')
      setNewCachedCost('')
      toast.success('Provider profile added')
    } catch (err) {
      console.error(err)
      toast.error('Failed to add provider profile')
    } finally {
      setAddingPricing(false)
    }
  }

  function startEdit(p: ProviderPricingResponse) {
    setEditState({
      id: p.id,
      isGlobal: !p.workspace_id,
      input: parseFloat(p.input_cost_per_1m).toString(),
      output: parseFloat(p.output_cost_per_1m).toString(),
      cached: p.cached_input_cost_per_1m ? parseFloat(p.cached_input_cost_per_1m).toString() : '',
    })
  }

  async function handleSaveEdit() {
    if (!editState) return
    setSavingEdit(true)
    try {
      const body = {
        input_cost_per_1m: editState.input,
        output_cost_per_1m: editState.output,
        cached_input_cost_per_1m: editState.cached.trim() || null,
      }
      const updated = editState.isGlobal
        ? await updateGlobalPricing(adminSecret, editState.id, body)
        : await updateProviderPricing(apiKey!, editState.id, body)
      setPricing((prev) => prev.map((p) => (p.id === updated.id ? updated : p)))
      setEditState(null)
      toast.success('Provider profile updated')
    } catch (err) {
      console.error(err)
      toast.error('Failed to update provider profile')
    } finally {
      setSavingEdit(false)
    }
  }

  async function handleReprice(provider: string, model: string) {
    if (!apiKey) return
    if (!confirm(`Reset all ${provider}/${model} costs to NULL and re-enrich? This may take a minute.`)) return
    try {
      const result = await repriceProvider(apiKey, { provider, model })
      toast.success(`Reprice queued — ${result.reset} calls reset`)
    } catch (err) {
      console.error(err)
      toast.error('Failed to queue reprice')
    }
  }

  async function handleDeletePricing(pricingId: string, isGlobal: boolean) {
    if (!confirm('Delete this pricing profile?')) return
    try {
      if (isGlobal) {
        await deleteGlobalPricing(adminSecret, pricingId)
      } else {
        await deleteProviderPricing(apiKey!, pricingId)
      }
      setPricing((prev) => prev.filter((p) => p.id !== pricingId))
      toast.success('Provider profile deleted')
    } catch (err) {
      console.error(err)
      toast.error('Failed to delete provider profile')
    }
  }

  // ── Integrations handlers ───────────────────────────────────────────────────

  async function handleTestSlack(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !slackWebhookUrl.trim()) return
    setTestingSlack(true)
    setSlackTestResult(null)
    try {
      const result = await testSlackWebhook(apiKey, slackWebhookUrl.trim())
      setSlackTestResult(result)
      if (result.ok) {
        toast.success('Test message sent to Slack')
      } else {
        toast.error(`Slack test failed: ${result.error}`)
      }
    } catch (err) {
      const msg = String(err)
      setSlackTestResult({ ok: false, error: msg })
      toast.error(`Slack test failed: ${msg}`)
    } finally {
      setTestingSlack(false)
    }
  }

  // ── Privacy handlers ────────────────────────────────────────────────────────

  async function handleSavePrivacy(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setSavingPrivacy(true)
    try {
      const rate = privacyMode === 'SAMPLED' && sampledRate.trim()
        ? parseFloat(sampledRate) / 100
        : null
      const updated = await upsertCapturePolicy(apiKey, {
        privacy_mode: privacyMode,
        sampled_rate: rate,
      })
      setCapturePolicy(updated)
      toast.success('Capture policy saved')
    } catch (err) {
      console.error(err)
      toast.error('Failed to save capture policy')
    } finally {
      setSavingPrivacy(false)
    }
  }

  // ── Alert rule handlers ──────────────────────────────────────────────────────

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
      })
      setAlertRules((prev) => [rule, ...prev])
      setNewAlertName('')
      setNewAlertThreshold('')
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

  // ── Model Gateway handlers ────────────────────────────────────────────────────

  async function handleCreateRoute(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !newRouteAlias || !newRouteTargetModel) return
    setCreatingRoute(true)
    try {
      const route = await createGatewayRoute(apiKey, {
        alias: newRouteAlias.trim(),
        provider: newRouteProvider,
        target_model: newRouteTargetModel.trim(),
        base_url: newRouteBaseUrl.trim() || null,
        api_key_env_var: newRouteApiKeyEnvVar.trim() || null,
        priority: parseInt(newRoutePriority, 10) || 10,
      })
      setGatewayRoutes((prev) => [...prev, route])
      setNewRouteAlias('')
      setNewRouteTargetModel('')
      setNewRouteBaseUrl('')
      setNewRouteApiKeyEnvVar('OPENAI_API_KEY')
      setNewRoutePriority('10')
      toast.success('Gateway route created')
    } catch (err) {
      console.error(err)
      toast.error('Failed to create gateway route')
    } finally {
      setCreatingRoute(false)
    }
  }

  async function handleToggleRoute(route: GatewayRoute) {
    if (!apiKey) return
    try {
      const updated = await updateGatewayRoute(apiKey, route.id, { is_active: !route.is_active })
      setGatewayRoutes((prev) => prev.map((r) => (r.id === route.id ? updated : r)))
      toast.success(updated.is_active ? 'Route enabled' : 'Route disabled')
    } catch (err) {
      console.error(err)
      toast.error('Failed to update route')
    }
  }

  async function handleDeleteRoute(routeId: string) {
    if (!apiKey || !confirm('Delete this gateway route?')) return
    try {
      await deleteGatewayRoute(apiKey, routeId)
      setGatewayRoutes((prev) => prev.filter((r) => r.id !== routeId))
      toast.success('Gateway route deleted')
    } catch (err) {
      console.error(err)
      toast.error('Failed to delete route')
    }
  }

  // ── Tenant management handlers ──────────────────────────────────────────────

  async function handleAdminAuth(e: React.FormEvent) {
    e.preventDefault()
    if (!adminSecret.trim()) return
    try {
      const data = await listTenants(adminSecret.trim())
      setTenants(data)
      setAdminAuthed(true)
    } catch {
      toast.error('Invalid admin secret or server error')
    }
  }

  async function handleCreateTenant(e: React.FormEvent) {
    e.preventDefault()
    if (!adminSecret.trim() || !newTenantSlug.trim() || !newTenantName.trim()) return
    setCreatingTenant(true)
    try {
      const tenant = await createTenant(adminSecret.trim(), {
        slug: newTenantSlug.trim(),
        name: newTenantName.trim(),
        plan: newTenantPlan,
      })
      setTenants((prev) => [tenant, ...prev])
      setNewTenantSlug('')
      setNewTenantName('')
      setNewTenantPlan('free')
      toast.success(`Tenant "${tenant.name}" created`)
    } catch (err) {
      console.error(err)
      toast.error('Failed to create tenant')
    } finally {
      setCreatingTenant(false)
    }
  }

  async function handleSelectTenant(tenantId: string) {
    if (selectedTenantId === tenantId) {
      setSelectedTenantId(null)
      setWorkspaces([])
      return
    }
    setSelectedTenantId(tenantId)
    setLoadingWorkspaces(true)
    try {
      const ws = await listAdminWorkspaces(adminSecret, tenantId)
      setWorkspaces(ws)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load workspaces')
    } finally {
      setLoadingWorkspaces(false)
    }
  }

  async function handleCreateWorkspace(e: React.FormEvent) {
    e.preventDefault()
    if (!adminSecret.trim() || !selectedTenantId || !newWorkspaceName.trim()) return
    setCreatingWorkspace(true)
    try {
      const ws = await createAdminWorkspace(adminSecret, {
        tenant_id: selectedTenantId,
        name: newWorkspaceName.trim(),
      })
      setWorkspaces((prev) => [...prev, ws])
      setNewWorkspaceName('')
      toast.success(`Workspace "${ws.name}" created`)
    } catch (err) {
      console.error(err)
      toast.error('Failed to create workspace')
    } finally {
      setCreatingWorkspace(false)
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-10 p-6">
      <h1 className="text-2xl font-semibold dark:text-white">Settings</h1>

      {/* ── API Keys ────────────────────────────────────────────────────────── */}
      <section>
        <h2 className="mb-4 text-lg font-medium dark:text-gray-100">API Keys</h2>

        {newRawKey && (
          <div className="mb-4 rounded border border-amber-300 bg-amber-50 p-4 dark:border-amber-700 dark:bg-amber-950">
            <p className="mb-2 text-sm font-medium text-amber-800 dark:text-amber-200">
              Save this key — it won&apos;t be shown again.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded bg-white px-3 py-1.5 font-mono text-xs text-gray-800 shadow-inner dark:bg-gray-900 dark:text-gray-100">
                {newRawKey}
              </code>
              <button
                onClick={handleCopy}
                className="rounded bg-amber-600 px-3 py-1.5 text-xs text-white hover:bg-amber-700"
              >
                {copied ? 'Copied!' : 'Copy'}
              </button>
              <button
                onClick={() => setNewRawKey(null)}
                className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        <form onSubmit={handleCreateKey} className="mb-4 flex flex-wrap gap-2">
          <input
            type="text"
            placeholder="Key name (optional)"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            className={inputCls}
          />
          <select
            value={newKeyEnv}
            onChange={(e) => setNewKeyEnv(e.target.value)}
            className={inputCls}
          >
            <option value="dev">dev</option>
            <option value="staging">staging</option>
            <option value="prod">prod</option>
          </select>
          <button
            type="submit"
            disabled={creatingKey}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {creatingKey ? 'Creating…' : 'Create Key'}
          </button>
        </form>

        <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
              <tr>
                <th className="px-4 py-2 text-left">Prefix</th>
                <th className="px-4 py-2 text-left">Name</th>
                <th className="px-4 py-2 text-left">Created</th>
                <th className="px-4 py-2 text-left">Created By</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {apiKeys.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-gray-400 dark:text-gray-500">
                    No active API keys.
                  </td>
                </tr>
              ) : (
                apiKeys.map((k) => (
                  <tr key={k.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">{k.key_prefix}…</td>
                    <td className="px-4 py-2 text-gray-600 dark:text-gray-400">{k.name ?? '—'}</td>
                    <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-500">
                      {new Date(k.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">
                      {k.created_by ?? '—'}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button
                        onClick={() => handleRevoke(k.id)}
                        className="text-xs text-red-500 hover:text-red-700 hover:underline dark:text-red-400"
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Provider Profiles ────────────────────────────────────────────────── */}
      <section>
        <h2 className="mb-4 text-lg font-medium dark:text-gray-100">Provider Profiles</h2>

        <form onSubmit={handleAddPricing} className="mb-4 flex flex-wrap gap-2">
          <input
            type="text"
            placeholder="Provider (e.g. openai)"
            value={newProvider}
            onChange={(e) => setNewProvider(e.target.value)}
            className={inputCls}
            required
          />
          <input
            type="text"
            placeholder="Model (e.g. gpt-4o)"
            value={newModel}
            onChange={(e) => setNewModel(e.target.value)}
            className={inputCls}
            required
          />
          <input
            type="number"
            step="any"
            min="0"
            placeholder="Input $/1M"
            value={newInputCost}
            onChange={(e) => setNewInputCost(e.target.value)}
            className={`w-28 ${inputCls}`}
            required
          />
          <input
            type="number"
            step="any"
            min="0"
            placeholder="Output $/1M"
            value={newOutputCost}
            onChange={(e) => setNewOutputCost(e.target.value)}
            className={`w-28 ${inputCls}`}
            required
          />
          <input
            type="number"
            step="any"
            min="0"
            placeholder="Cached $/1M (opt)"
            value={newCachedCost}
            onChange={(e) => setNewCachedCost(e.target.value)}
            className={`w-36 ${inputCls}`}
          />
          <button
            type="submit"
            disabled={addingPricing}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {addingPricing ? 'Adding…' : 'Add Profile'}
          </button>
        </form>

        <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
              <tr>
                <th className="px-4 py-2 text-left">Provider</th>
                <th className="px-4 py-2 text-left">Model</th>
                <th className="px-4 py-2 text-right">Input $/1M</th>
                <th className="px-4 py-2 text-right">Output $/1M</th>
                <th className="px-4 py-2 text-right">Cached $/1M</th>
                <th className="px-4 py-2 text-left">Effective From</th>
                <th className="px-4 py-2 text-left">Scope</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {pricing.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-6 text-center text-gray-400 dark:text-gray-500">
                    No pricing profiles. Add a workspace override above.
                  </td>
                </tr>
              ) : (
                pricing.map((p) => {
                  const isEditing = editState?.id === p.id
                  const isOwned = !!p.workspace_id
                  const miniInput =
                    'w-24 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-2 py-0.5 text-xs text-right focus:outline-none focus:ring-1 focus:ring-indigo-500'

                  return (
                    <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">{p.provider}</td>
                      <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">{p.model}</td>

                      {isEditing ? (
                        <>
                          <td className="px-4 py-1 text-right">
                            <input
                              type="number"
                              step="any"
                              min="0"
                              value={editState.input}
                              onChange={(e) => setEditState({ ...editState, input: e.target.value })}
                              className={miniInput}
                            />
                          </td>
                          <td className="px-4 py-1 text-right">
                            <input
                              type="number"
                              step="any"
                              min="0"
                              value={editState.output}
                              onChange={(e) => setEditState({ ...editState, output: e.target.value })}
                              className={miniInput}
                            />
                          </td>
                          <td className="px-4 py-1 text-right">
                            <input
                              type="number"
                              step="any"
                              min="0"
                              placeholder="—"
                              value={editState.cached}
                              onChange={(e) => setEditState({ ...editState, cached: e.target.value })}
                              className={miniInput}
                            />
                          </td>
                        </>
                      ) : (
                        <>
                          <td className="px-4 py-2 text-right font-mono text-xs dark:text-gray-300">
                            ${parseFloat(p.input_cost_per_1m).toFixed(4)}
                          </td>
                          <td className="px-4 py-2 text-right font-mono text-xs dark:text-gray-300">
                            ${parseFloat(p.output_cost_per_1m).toFixed(4)}
                          </td>
                          <td className="px-4 py-2 text-right font-mono text-xs dark:text-gray-300">
                            {p.cached_input_cost_per_1m
                              ? `$${parseFloat(p.cached_input_cost_per_1m).toFixed(4)}`
                              : '—'}
                          </td>
                        </>
                      )}

                      <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">
                        {new Date(p.effective_from).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-2">
                        {isOwned ? (
                          <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                            workspace
                          </span>
                        ) : (
                          <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                            global
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {(isOwned || adminAuthed) ? (
                          <div className="flex items-center justify-end gap-3">
                            {isEditing ? (
                              <>
                                <button
                                  onClick={handleSaveEdit}
                                  disabled={savingEdit}
                                  className="text-xs font-medium text-indigo-600 hover:underline disabled:opacity-50 dark:text-indigo-400"
                                >
                                  {savingEdit ? 'Saving…' : 'Save'}
                                </button>
                                <button
                                  onClick={() => setEditState(null)}
                                  className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                                >
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  onClick={() => handleReprice(p.provider, p.model)}
                                  className="text-xs text-amber-600 hover:underline dark:text-amber-400"
                                  title="Reset cost_usd to NULL and trigger re-enrichment"
                                >
                                  Reprice
                                </button>
                                <button
                                  onClick={() => startEdit(p)}
                                  className="text-xs text-indigo-600 hover:underline dark:text-indigo-400"
                                >
                                  Edit
                                </button>
                                <button
                                  onClick={() => handleDeletePricing(p.id, !isOwned)}
                                  className="text-xs text-red-500 hover:text-red-700 hover:underline dark:text-red-400"
                                >
                                  Delete
                                </button>
                              </>
                            )}
                          </div>
                        ) : (
                          <div className="flex items-center justify-end gap-3">
                            <button
                              onClick={() => handleReprice(p.provider, p.model)}
                              className="text-xs text-amber-600 hover:underline dark:text-amber-400"
                              title="Reset cost_usd to NULL and trigger re-enrichment"
                            >
                              Reprice
                            </button>
                            <span className="text-xs text-gray-300 dark:text-gray-600" title="Authenticate as admin (Tenant Management section) to edit global profiles">
                              admin only
                            </span>
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Appearance ──────────────────────────────────────────────────────── */}
      <section>
        <h2 className="mb-4 text-lg font-medium dark:text-gray-100">Appearance</h2>
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-600 dark:text-gray-400">Theme</label>
          <select
            value={theme ?? 'system'}
            onChange={(e) => setTheme(e.target.value)}
            className={inputCls}
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">System</option>
          </select>
        </div>
      </section>

      {/* ── Data Capture Policy ─────────────────────────────────────────────── */}
      <section>
        <h2 className="mb-1 text-lg font-medium dark:text-gray-100">Data Capture Policy</h2>
        <p className="mb-4 text-xs text-gray-500 dark:text-gray-400">
          Controls what payload data the SDK sends to the collector. Affects privacy and storage.
        </p>

        {capturePolicy && (
          <div className="mb-4 flex items-center gap-2">
            <span className="text-xs text-gray-500 dark:text-gray-400">Current:</span>
            <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
              {capturePolicy.privacy_mode}
            </span>
            {capturePolicy.sampled_rate && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                @ {(parseFloat(capturePolicy.sampled_rate) * 100).toFixed(0)}% sample rate
              </span>
            )}
          </div>
        )}

        <form onSubmit={handleSavePrivacy} className="space-y-3">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500 dark:text-gray-400">Privacy mode</label>
              <select
                value={privacyMode}
                onChange={(e) => setPrivacyMode(e.target.value)}
                className={inputCls}
              >
                <option value="METADATA_ONLY">METADATA_ONLY — tokens, model, latency only (default)</option>
                <option value="ERRORS_ONLY">ERRORS_ONLY — metadata + error messages</option>
                <option value="SAMPLED">SAMPLED — full payload on a % of runs</option>
                <option value="FULL">FULL — complete request/response payloads</option>
              </select>
            </div>

            {privacyMode === 'SAMPLED' && (
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 dark:text-gray-400">Sample rate (%)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  placeholder="10"
                  value={sampledRate}
                  onChange={(e) => setSampledRate(e.target.value)}
                  className={`w-24 ${inputCls}`}
                  required
                />
              </div>
            )}
          </div>

          <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
            <strong>FULL</strong> mode stores raw prompts and completions. Ensure you have user consent
            and appropriate data retention policies before enabling.
          </div>

          <button
            type="submit"
            disabled={savingPrivacy}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {savingPrivacy ? 'Saving…' : 'Save Policy'}
          </button>
        </form>
      </section>

      {/* ── Integrations ────────────────────────────────────────────────────── */}
      <section>
        <h2 className="mb-4 text-lg font-medium dark:text-gray-100">Integrations</h2>

        <div className="mb-3 rounded border border-blue-100 bg-blue-50 p-3 text-sm text-blue-700 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300">
          Configure budget notifications via{' '}
          <code className="rounded bg-blue-100 px-1 font-mono text-xs dark:bg-blue-900">
            POST /budgets/{'{id}'}/notifications
          </code>{' '}
          with <code className="rounded bg-blue-100 px-1 font-mono text-xs dark:bg-blue-900">channel: &quot;slack&quot;</code>.
        </div>

        <div className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">Slack Webhook</div>
        <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">
          Paste an incoming webhook URL to test connectivity before configuring budget notifications.
        </p>

        <form onSubmit={handleTestSlack} className="flex flex-wrap gap-2">
          <input
            type="url"
            placeholder="https://hooks.slack.com/services/..."
            value={slackWebhookUrl}
            onChange={(e) => setSlackWebhookUrl(e.target.value)}
            className={`flex-1 ${inputCls}`}
            required
          />
          <button
            type="submit"
            disabled={testingSlack || !slackWebhookUrl.trim()}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {testingSlack ? 'Sending…' : 'Test'}
          </button>
        </form>

        {slackTestResult && (
          <div
            className={`mt-3 rounded border px-3 py-2 text-sm ${
              slackTestResult.ok
                ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300'
                : 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300'
            }`}
          >
            {slackTestResult.ok ? '✓ Test message sent successfully.' : <>✗ Failed: {slackTestResult.error}</>}
          </div>
        )}
      </section>

      {/* ── Alert Rules ─────────────────────────────────────────────────────── */}
      <section>
        <h2 className="mb-1 text-lg font-medium dark:text-gray-100">Alert Rules</h2>
        <p className="mb-4 text-xs text-gray-500 dark:text-gray-400">
          Fire Slack notifications when a metric crosses a threshold. Rules are evaluated every 5 minutes.
        </p>

        {/* Create form */}
        <form onSubmit={handleCreateAlert} className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <input
            className={inputCls}
            placeholder="Rule name (e.g. High error rate)"
            value={newAlertName}
            onChange={(e) => setNewAlertName(e.target.value)}
            required
          />
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
            <input
              className={`${inputCls} flex-1`}
              type="number"
              step="any"
              min="0"
              placeholder="Threshold"
              value={newAlertThreshold}
              onChange={(e) => setNewAlertThreshold(e.target.value)}
              required
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              className={`${inputCls} w-24`}
              type="number"
              min="5"
              max="1440"
              placeholder="60"
              value={newAlertWindow}
              onChange={(e) => setNewAlertWindow(e.target.value)}
            />
            <span className="text-sm text-gray-500 dark:text-gray-400">min window</span>
          </div>
          <button
            type="submit"
            disabled={creatingAlert}
            className="rounded bg-indigo-600 px-4 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {creatingAlert ? 'Creating…' : 'Add Rule'}
          </button>
        </form>

        {/* Rules table */}
        {alertRules.length === 0 ? (
          <p className="text-sm text-gray-400 dark:text-gray-500">No alert rules yet.</p>
        ) : (
          <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700 mb-4">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                <tr>
                  <th className="px-4 py-2 text-left">Name</th>
                  <th className="px-4 py-2 text-left">Metric</th>
                  <th className="px-4 py-2 text-left">Condition</th>
                  <th className="px-4 py-2 text-left">Window</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-left" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {alertRules.map((rule) => (
                  <tr key={rule.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-4 py-2 font-medium dark:text-gray-200">{rule.name}</td>
                    <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">{rule.metric}</td>
                    <td className="px-4 py-2 text-xs dark:text-gray-300">
                      {rule.operator === 'gt' ? '>' : '<'} {rule.threshold}
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">{rule.window_minutes}m</td>
                    <td className="px-4 py-2">
                      <button
                        onClick={() => handleToggleAlert(rule)}
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          rule.is_active
                            ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                            : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                        }`}
                      >
                        {rule.is_active ? 'Active' : 'Paused'}
                      </button>
                    </td>
                    <td className="px-4 py-2">
                      <button
                        onClick={() => handleDeleteAlert(rule.id)}
                        className="text-xs text-red-500 hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Recent firings */}
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
                      <td className="px-3 py-2 text-gray-500 dark:text-gray-400">
                        {new Date(f.fired_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      {/* ── Model Gateway ───────────────────────────────────────────────────── */}
      <section>
        <h2 className="mb-1 text-lg font-medium dark:text-gray-100">Model Gateway</h2>
        <p className="mb-4 text-xs text-gray-500 dark:text-gray-400">
          Configure provider routes for the OpenAI-compatible proxy. Point your app&apos;s{' '}
          <code className="font-mono">base_url</code> to{' '}
          <code className="font-mono">/gateway</code> to enable routing, caching, and fallback.
        </p>

        {/* Stats strip */}
        {gatewayStats && gatewayStats.total_requests > 0 && (
          <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: 'Total Requests', value: gatewayStats.total_requests.toLocaleString() },
              { label: 'Cache Hits', value: gatewayStats.cache_hits.toLocaleString() },
              {
                label: 'Cache Hit Rate',
                value: `${(parseFloat(gatewayStats.cache_hit_rate) * 100).toFixed(1)}%`,
              },
              {
                label: 'Avg Latency',
                value: gatewayStats.avg_latency_ms
                  ? `${parseFloat(gatewayStats.avg_latency_ms).toFixed(0)}ms`
                  : '—',
              },
            ].map((s) => (
              <div
                key={s.label}
                className="rounded border border-gray-200 bg-gray-50 px-4 py-3 dark:border-gray-700 dark:bg-gray-800"
              >
                <p className="text-xs text-gray-500 dark:text-gray-400">{s.label}</p>
                <p className="text-lg font-semibold dark:text-gray-100">{s.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Create route form */}
        <form
          onSubmit={handleCreateRoute}
          className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
        >
          <input
            type="text"
            placeholder="Alias (e.g. gpt-4o)"
            value={newRouteAlias}
            onChange={(e) => setNewRouteAlias(e.target.value)}
            className={inputCls}
            required
          />
          <select
            value={newRouteProvider}
            onChange={(e) => setNewRouteProvider(e.target.value)}
            className={inputCls}
          >
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="ollama">Ollama</option>
            <option value="groq">Groq</option>
            <option value="mistral">Mistral</option>
            <option value="custom">Custom</option>
          </select>
          <input
            type="text"
            placeholder="Target model (e.g. gpt-4o-2024-11-20)"
            value={newRouteTargetModel}
            onChange={(e) => setNewRouteTargetModel(e.target.value)}
            className={inputCls}
            required
          />
          <input
            type="text"
            placeholder="Base URL (optional, default: OpenAI)"
            value={newRouteBaseUrl}
            onChange={(e) => setNewRouteBaseUrl(e.target.value)}
            className={inputCls}
          />
          <input
            type="text"
            placeholder="API key env var (e.g. OPENAI_API_KEY)"
            value={newRouteApiKeyEnvVar}
            onChange={(e) => setNewRouteApiKeyEnvVar(e.target.value)}
            className={inputCls}
          />
          <div className="flex items-center gap-2">
            <input
              type="number"
              placeholder="Priority"
              value={newRoutePriority}
              onChange={(e) => setNewRoutePriority(e.target.value)}
              className={`w-24 ${inputCls}`}
              min={1}
              max={100}
            />
            <button
              type="submit"
              disabled={creatingRoute || !newRouteAlias || !newRouteTargetModel}
              className="flex-1 rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 dark:bg-indigo-500 dark:hover:bg-indigo-600"
            >
              {creatingRoute ? 'Adding…' : 'Add Route'}
            </button>
          </div>
        </form>

        {/* Routes table */}
        {gatewayRoutes.length > 0 && (
          <div className="mb-4 overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                <tr>
                  <th className="px-4 py-2 text-left">Alias</th>
                  <th className="px-4 py-2 text-left">Provider</th>
                  <th className="px-4 py-2 text-left">Target Model</th>
                  <th className="px-4 py-2 text-left">Priority</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-left" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {gatewayRoutes.map((route) => (
                  <tr key={route.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-4 py-2 font-mono text-sm dark:text-gray-200">{route.alias}</td>
                    <td className="px-4 py-2 text-xs capitalize dark:text-gray-300">{route.provider}</td>
                    <td className="px-4 py-2 font-mono text-xs text-gray-500 dark:text-gray-400">{route.target_model}</td>
                    <td className="px-4 py-2 text-xs dark:text-gray-300">{route.priority}</td>
                    <td className="px-4 py-2">
                      <button
                        onClick={() => handleToggleRoute(route)}
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          route.is_active
                            ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                            : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                        }`}
                      >
                        {route.is_active ? 'Active' : 'Disabled'}
                      </button>
                    </td>
                    <td className="px-4 py-2">
                      <button
                        onClick={() => handleDeleteRoute(route.id)}
                        className="text-xs text-red-500 hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ── Tenant Management ───────────────────────────────────────────────── */}
      <section>
        <h2 className="mb-1 text-lg font-medium dark:text-gray-100">Tenant Management</h2>
        <p className="mb-4 text-xs text-gray-500 dark:text-gray-400">
          Admin-only. Enter the server&apos;s admin secret (ADMIN_SECRET env var, or SECRET_KEY as fallback) to manage tenants.
        </p>

        {!adminAuthed ? (
          <form onSubmit={handleAdminAuth} className="flex gap-2">
            <input
              type="password"
              placeholder="Admin secret"
              value={adminSecret}
              onChange={(e) => setAdminSecret(e.target.value)}
              className={`max-w-xs flex-1 ${inputCls}`}
              required
            />
            <button
              type="submit"
              className="rounded bg-gray-700 px-3 py-1.5 text-sm text-white hover:bg-gray-800 dark:bg-gray-600 dark:hover:bg-gray-500"
            >
              Authenticate
            </button>
          </form>
        ) : (
          <div className="space-y-6">
            {/* Create tenant */}
            <form onSubmit={handleCreateTenant} className="flex flex-wrap items-end gap-2">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 dark:text-gray-400">Slug</label>
                <input
                  type="text"
                  placeholder="my-org"
                  value={newTenantSlug}
                  onChange={(e) => setNewTenantSlug(e.target.value)}
                  className={inputCls}
                  required
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 dark:text-gray-400">Name</label>
                <input
                  type="text"
                  placeholder="My Organization"
                  value={newTenantName}
                  onChange={(e) => setNewTenantName(e.target.value)}
                  className={inputCls}
                  required
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 dark:text-gray-400">Plan</label>
                <select
                  value={newTenantPlan}
                  onChange={(e) => setNewTenantPlan(e.target.value)}
                  className={inputCls}
                >
                  <option value="free">free</option>
                  <option value="starter">starter</option>
                  <option value="growth">growth</option>
                  <option value="enterprise">enterprise</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={creatingTenant}
                className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {creatingTenant ? 'Creating…' : 'New Tenant'}
              </button>
            </form>

            {/* Tenants table */}
            <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                  <tr>
                    <th className="px-4 py-2 text-left">Name</th>
                    <th className="px-4 py-2 text-left">Slug</th>
                    <th className="px-4 py-2 text-left">Plan</th>
                    <th className="px-4 py-2 text-left">Created</th>
                    <th className="px-4 py-2 text-left">ID</th>
                    <th className="px-4 py-2 text-right">Workspaces</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {tenants.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-6 text-center text-gray-400 dark:text-gray-500">
                        No tenants found.
                      </td>
                    </tr>
                  ) : (
                    tenants.map((t) => (
                      <tr key={t.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="px-4 py-2 font-medium dark:text-gray-200">{t.name}</td>
                        <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">{t.slug}</td>
                        <td className="px-4 py-2">
                          <span
                            className={`rounded px-2 py-0.5 text-xs ${
                              t.plan === 'enterprise'
                                ? 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300'
                                : t.plan === 'growth'
                                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                                  : t.plan === 'starter'
                                    ? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300'
                                    : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                            }`}
                          >
                            {t.plan}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">
                          {new Date(t.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-2 font-mono text-xs text-gray-400 dark:text-gray-500">
                          {t.id}
                        </td>
                        <td className="px-4 py-2 text-right">
                          <button
                            onClick={() => handleSelectTenant(t.id)}
                            className={`text-xs hover:underline ${selectedTenantId === t.id ? 'font-medium text-indigo-600 dark:text-indigo-400' : 'text-gray-500 dark:text-gray-400'}`}
                          >
                            {selectedTenantId === t.id ? 'Hide' : 'Manage'}
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Workspace management panel */}
            {selectedTenantId && (
              <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
                <h3 className="mb-3 text-sm font-semibold dark:text-gray-200">
                  Workspaces for {tenants.find((t) => t.id === selectedTenantId)?.name}
                </h3>

                <form onSubmit={handleCreateWorkspace} className="mb-4 flex gap-2">
                  <input
                    type="text"
                    placeholder="Workspace name"
                    value={newWorkspaceName}
                    onChange={(e) => setNewWorkspaceName(e.target.value)}
                    className={`flex-1 ${inputCls}`}
                    required
                  />
                  <button
                    type="submit"
                    disabled={creatingWorkspace}
                    className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {creatingWorkspace ? 'Creating…' : 'New Workspace'}
                  </button>
                </form>

                {loadingWorkspaces ? (
                  <div className="space-y-1.5">
                    {[1, 2].map((i) => <div key={i} className="h-8 animate-pulse rounded bg-gray-100 dark:bg-gray-700" />)}
                  </div>
                ) : workspaces.length === 0 ? (
                  <p className="text-sm text-gray-400 dark:text-gray-500">No workspaces yet.</p>
                ) : (
                  <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                        <tr>
                          <th className="px-4 py-2 text-left">Name</th>
                          <th className="px-4 py-2 text-left">Created</th>
                          <th className="px-4 py-2 text-left">ID</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                        {workspaces.map((w) => (
                          <tr key={w.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                            <td className="px-4 py-2 font-medium dark:text-gray-200">{w.name}</td>
                            <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">
                              {new Date(w.created_at).toLocaleDateString()}
                            </td>
                            <td className="px-4 py-2 font-mono text-xs text-gray-400 dark:text-gray-500">{w.id}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
