'use client'

import { useSession } from 'next-auth/react'
import { useTheme } from 'next-themes'
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import type { ApiKeyResponse, ProviderPricingResponse, TenantResponse, AdminWorkspaceResponse, CapturePolicyResponse } from '@/types/api'
import {
  listApiKeys,
  createApiKey,
  revokeApiKey,
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

  const load = useCallback(async () => {
    if (!apiKey) return
    try {
      const [keys, pricingData, policy] = await Promise.all([
        listApiKeys(apiKey),
        listProviderPricing(apiKey),
        getCapturePolicy(apiKey),
      ])
      setApiKeys(keys)
      setPricing(pricingData.items)
      if (policy) {
        setCapturePolicy(policy)
        setPrivacyMode(policy.privacy_mode)
        setSampledRate(policy.sampled_rate ? String(parseFloat(policy.sampled_rate) * 100) : '')
      }
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
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {apiKeys.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-gray-400 dark:text-gray-500">
                    No active API keys.
                  </td>
                </tr>
              ) : (
                apiKeys.map((k) => (
                  <tr key={k.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">{k.key_prefix}…</td>
                    <td className="px-4 py-2 text-gray-600 dark:text-gray-400">{k.name ?? '—'}</td>
                    <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-500">
                      {new Date(k.created_at).toLocaleDateString()}
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
                          <span className="text-xs text-gray-300 dark:text-gray-600" title="Authenticate as admin (Tenant Management section) to edit global profiles">
                            admin only
                          </span>
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
