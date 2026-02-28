'use client'

import { useSession } from 'next-auth/react'
import { useTheme } from 'next-themes'
import { useState, useEffect, useCallback } from 'react'
import type { ApiKeyResponse, ProviderPricingResponse } from '@/types/api'
import {
  listApiKeys,
  createApiKey,
  revokeApiKey,
  listProviderPricing,
  createProviderPricing,
  deleteProviderPricing,
  testSlackWebhook,
} from '@/lib/api'

export default function SettingsPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey as string | undefined
  const { theme, setTheme } = useTheme()

  // ── API Keys state ─────────────────────────────────────────────────────────
  const [apiKeys, setApiKeys] = useState<ApiKeyResponse[]>([])
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyEnv, setNewKeyEnv] = useState('dev')
  const [creatingKey, setCreatingKey] = useState(false)
  const [newRawKey, setNewRawKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  // ── Integrations state ─────────────────────────────────────────────────────
  const [slackWebhookUrl, setSlackWebhookUrl] = useState('')
  const [slackTestResult, setSlackTestResult] = useState<{ ok: boolean; error: string | null } | null>(null)
  const [testingSlack, setTestingSlack] = useState(false)

  // ── Provider pricing state ─────────────────────────────────────────────────
  const [pricing, setPricing] = useState<ProviderPricingResponse[]>([])
  const [newProvider, setNewProvider] = useState('')
  const [newModel, setNewModel] = useState('')
  const [newInputCost, setNewInputCost] = useState('')
  const [newOutputCost, setNewOutputCost] = useState('')
  const [newCachedCost, setNewCachedCost] = useState('')
  const [addingPricing, setAddingPricing] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey) return
    try {
      const [keys, pricingData] = await Promise.all([
        listApiKeys(apiKey),
        listProviderPricing(apiKey),
      ])
      setApiKeys(keys)
      setPricing(pricingData.items)
    } catch (_) {
      // ignore
    }
  }, [apiKey])

  useEffect(() => {
    load()
  }, [load])

  // ── API Key handlers ───────────────────────────────────────────────────────

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
    } finally {
      setCreatingKey(false)
    }
  }

  async function handleRevoke(keyId: string) {
    if (!apiKey) return
    await revokeApiKey(apiKey, keyId)
    setApiKeys((prev) => prev.filter((k) => k.id !== keyId))
    if (newRawKey) setNewRawKey(null)
  }

  async function handleCopy() {
    if (!newRawKey) return
    await navigator.clipboard.writeText(newRawKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // ── Provider pricing handlers ──────────────────────────────────────────────

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
    } finally {
      setAddingPricing(false)
    }
  }

  async function handleDeletePricing(pricingId: string) {
    if (!apiKey) return
    await deleteProviderPricing(apiKey, pricingId)
    setPricing((prev) => prev.filter((p) => p.id !== pricingId))
  }

  // ── Integrations handlers ──────────────────────────────────────────────────

  async function handleTestSlack(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !slackWebhookUrl.trim()) return
    setTestingSlack(true)
    setSlackTestResult(null)
    try {
      const result = await testSlackWebhook(apiKey, slackWebhookUrl.trim())
      setSlackTestResult(result)
    } catch (err) {
      setSlackTestResult({ ok: false, error: String(err) })
    } finally {
      setTestingSlack(false)
    }
  }

  return (
    <div className="space-y-10 p-6">
      <h1 className="text-2xl font-semibold">Settings</h1>

      {/* ── API Keys ────────────────────────────────────────────────────────── */}
      <section>
        <h2 className="mb-4 text-lg font-medium">API Keys</h2>

        {/* One-time key banner */}
        {newRawKey && (
          <div className="mb-4 rounded border border-amber-300 bg-amber-50 p-4">
            <p className="mb-2 text-sm font-medium text-amber-800">
              Save this key — it won&apos;t be shown again.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded bg-white px-3 py-1.5 font-mono text-xs text-gray-800 shadow-inner">
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
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* Create form */}
        <form onSubmit={handleCreateKey} className="mb-4 flex flex-wrap gap-2">
          <input
            type="text"
            placeholder="Key name (optional)"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm"
          />
          <select
            value={newKeyEnv}
            onChange={(e) => setNewKeyEnv(e.target.value)}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm"
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

        <div className="overflow-x-auto rounded border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-2 text-left">Prefix</th>
                <th className="px-4 py-2 text-left">Name</th>
                <th className="px-4 py-2 text-left">Created</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {apiKeys.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-gray-400">
                    No active API keys.
                  </td>
                </tr>
              ) : (
                apiKeys.map((k) => (
                  <tr key={k.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs">{k.key_prefix}…</td>
                    <td className="px-4 py-2 text-gray-600">{k.name ?? '—'}</td>
                    <td className="px-4 py-2 text-xs text-gray-500">
                      {new Date(k.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button
                        onClick={() => handleRevoke(k.id)}
                        className="text-xs text-red-500 hover:underline"
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
        <h2 className="mb-4 text-lg font-medium">Provider Profiles</h2>

        {/* Add form */}
        <form onSubmit={handleAddPricing} className="mb-4 flex flex-wrap gap-2">
          <input
            type="text"
            placeholder="Provider (e.g. openai)"
            value={newProvider}
            onChange={(e) => setNewProvider(e.target.value)}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm"
            required
          />
          <input
            type="text"
            placeholder="Model (e.g. gpt-4o)"
            value={newModel}
            onChange={(e) => setNewModel(e.target.value)}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm"
            required
          />
          <input
            type="number"
            step="any"
            min="0"
            placeholder="Input $/1M"
            value={newInputCost}
            onChange={(e) => setNewInputCost(e.target.value)}
            className="w-28 rounded border border-gray-300 px-3 py-1.5 text-sm"
            required
          />
          <input
            type="number"
            step="any"
            min="0"
            placeholder="Output $/1M"
            value={newOutputCost}
            onChange={(e) => setNewOutputCost(e.target.value)}
            className="w-28 rounded border border-gray-300 px-3 py-1.5 text-sm"
            required
          />
          <input
            type="number"
            step="any"
            min="0"
            placeholder="Cached $/1M (opt)"
            value={newCachedCost}
            onChange={(e) => setNewCachedCost(e.target.value)}
            className="w-36 rounded border border-gray-300 px-3 py-1.5 text-sm"
          />
          <button
            type="submit"
            disabled={addingPricing}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {addingPricing ? 'Adding…' : 'Add Profile'}
          </button>
        </form>

        <div className="overflow-x-auto rounded border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-2 text-left">Provider</th>
                <th className="px-4 py-2 text-left">Model</th>
                <th className="px-4 py-2 text-right">Input $/1M</th>
                <th className="px-4 py-2 text-right">Output $/1M</th>
                <th className="px-4 py-2 text-right">Cached $/1M</th>
                <th className="px-4 py-2 text-left">Effective From</th>
                <th className="px-4 py-2 text-left">Scope</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {pricing.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-6 text-center text-gray-400">
                    No pricing profiles. Add a workspace override above.
                  </td>
                </tr>
              ) : (
                pricing.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs">{p.provider}</td>
                    <td className="px-4 py-2 font-mono text-xs">{p.model}</td>
                    <td className="px-4 py-2 text-right font-mono text-xs">
                      ${parseFloat(p.input_cost_per_1m).toFixed(4)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-xs">
                      ${parseFloat(p.output_cost_per_1m).toFixed(4)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-xs">
                      {p.cached_input_cost_per_1m
                        ? `$${parseFloat(p.cached_input_cost_per_1m).toFixed(4)}`
                        : '—'}
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500">
                      {new Date(p.effective_from).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-2">
                      {p.workspace_id ? (
                        <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs text-indigo-700">
                          workspace
                        </span>
                      ) : (
                        <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                          global
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-right">
                      {p.workspace_id && (
                        <button
                          onClick={() => handleDeletePricing(p.id)}
                          className="text-xs text-red-500 hover:underline"
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Appearance ──────────────────────────────────────────────────────── */}
      <section>
        <h2 className="mb-4 text-lg font-medium">Appearance</h2>
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-600">Theme</label>
          <select
            value={theme ?? 'system'}
            onChange={(e) => setTheme(e.target.value)}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm"
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">System</option>
          </select>
        </div>
      </section>

      {/* ── Integrations ────────────────────────────────────────────────────── */}
      <section>
        <h2 className="mb-4 text-lg font-medium">Integrations</h2>

        <div className="mb-3 rounded border border-blue-100 bg-blue-50 p-3 text-sm text-blue-700">
          Configure budget notifications via{' '}
          <code className="rounded bg-blue-100 px-1 font-mono text-xs">
            POST /budgets/{'{id}'}/notifications
          </code>{' '}
          with <code className="rounded bg-blue-100 px-1 font-mono text-xs">channel: &quot;slack&quot;</code>.
        </div>

        <div className="mb-2 text-sm font-medium text-gray-700">Slack Webhook</div>
        <p className="mb-3 text-xs text-gray-500">
          Paste an incoming webhook URL to test connectivity before configuring budget notifications.
        </p>

        <form onSubmit={handleTestSlack} className="flex flex-wrap gap-2">
          <input
            type="url"
            placeholder="https://hooks.slack.com/services/..."
            value={slackWebhookUrl}
            onChange={(e) => setSlackWebhookUrl(e.target.value)}
            className="flex-1 rounded border border-gray-300 px-3 py-1.5 text-sm"
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
                ? 'border-green-200 bg-green-50 text-green-700'
                : 'border-red-200 bg-red-50 text-red-700'
            }`}
          >
            {slackTestResult.ok ? (
              '✓ Test message sent successfully.'
            ) : (
              <>✗ Failed: {slackTestResult.error}</>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
