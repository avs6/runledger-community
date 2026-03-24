'use client'

import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import { Plus, Trash2, Copy, Check } from 'lucide-react'

interface SsoConfig {
  id: string
  provider: string
  issuer_url: string
  client_id: string
  scopes: string
  default_role: string
  enabled: boolean
  created_at: string
}

interface ScimToken {
  id: string
  token_prefix: string
  label: string
  enabled: boolean
  last_used_at: string | null
  created_at: string
}

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

const PROVIDERS = ['google', 'okta', 'azure', 'github', 'generic']

export default function SsoTab({ apiKey, apiBase }: { apiKey: string; apiBase: string }) {
  const [configs, setConfigs] = useState<SsoConfig[]>([])
  const [tokens, setTokens] = useState<ScimToken[]>([])
  const [loading, setLoading] = useState(false)
  const [newRawToken, setNewRawToken] = useState<string | null>(null)
  const [tokenCopied, setTokenCopied] = useState(false)
  const [showSsoForm, setShowSsoForm] = useState(false)
  const [ssoForm, setSsoForm] = useState({
    provider: 'google',
    issuer_url: '',
    client_id: '',
    client_secret: '',
    scopes: 'openid email profile',
    default_role: 'member',
    enabled: true,
  })
  const [creatingSso, setCreatingSso] = useState(false)
  const [scimLabel, setScimLabel] = useState('SCIM provisioning')
  const [creatingToken, setCreatingToken] = useState(false)

  const headers = { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' }

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [cfgRes, tokRes] = await Promise.all([
        fetch(`${apiBase}/sso/configs`, { headers }),
        fetch(`${apiBase}/sso/tokens`, { headers }),
      ])
      if (cfgRes.ok) {
        const d = await cfgRes.json()
        setConfigs(d.items ?? [])
      }
      if (tokRes.ok) {
        const d = await tokRes.json()
        setTokens(d.items ?? [])
      }
    } catch {
      toast.error('Failed to load SSO data')
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey, apiBase])

  useEffect(() => { load() }, [load])

  async function handleCreateSso(e: React.FormEvent) {
    e.preventDefault()
    if (!ssoForm.issuer_url || !ssoForm.client_id || !ssoForm.client_secret) {
      toast.error('Please fill in all required fields')
      return
    }
    setCreatingSso(true)
    try {
      const res = await fetch(`${apiBase}/sso/configs`, {
        method: 'POST',
        headers,
        body: JSON.stringify(ssoForm),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail ?? 'Failed to create SSO config')
      }
      toast.success('SSO configuration created')
      setShowSsoForm(false)
      setSsoForm({
        provider: 'google', issuer_url: '', client_id: '', client_secret: '',
        scopes: 'openid email profile', default_role: 'member', enabled: true,
      })
      await load()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error creating SSO config')
    } finally {
      setCreatingSso(false)
    }
  }

  async function handleDeleteSso(id: string) {
    if (!confirm('Delete this SSO configuration? Users who sign in via SSO will need to use a password.')) return
    try {
      await fetch(`${apiBase}/sso/configs/${id}`, { method: 'DELETE', headers })
      toast.success('SSO config deleted')
      await load()
    } catch {
      toast.error('Failed to delete SSO config')
    }
  }

  async function handleToggleSso(cfg: SsoConfig) {
    try {
      const res = await fetch(`${apiBase}/sso/configs/${cfg.id}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({ enabled: !cfg.enabled }),
      })
      if (!res.ok) throw new Error()
      toast.success(cfg.enabled ? 'SSO disabled' : 'SSO enabled')
      await load()
    } catch {
      toast.error('Failed to update SSO config')
    }
  }

  async function handleCreateScimToken(e: React.FormEvent) {
    e.preventDefault()
    setCreatingToken(true)
    try {
      const res = await fetch(`${apiBase}/sso/tokens`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ label: scimLabel }),
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setNewRawToken(data.raw_token)
      setScimLabel('SCIM provisioning')
      await load()
    } catch {
      toast.error('Failed to create SCIM token')
    } finally {
      setCreatingToken(false)
    }
  }

  async function handleDeleteToken(id: string) {
    if (!confirm('Revoke this SCIM token?')) return
    try {
      await fetch(`${apiBase}/sso/tokens/${id}`, { method: 'DELETE', headers })
      toast.success('SCIM token revoked')
      await load()
    } catch {
      toast.error('Failed to revoke token')
    }
  }

  async function copyToken() {
    if (!newRawToken) return
    await navigator.clipboard.writeText(newRawToken)
    setTokenCopied(true)
    setTimeout(() => setTokenCopied(false), 2000)
  }

  const PROVIDER_HINTS: Record<string, string> = {
    google: 'https://accounts.google.com',
    okta: 'https://your-org.okta.com/oauth2/default',
    azure: 'https://login.microsoftonline.com/{tenant}/v2.0',
    github: 'https://token.actions.githubusercontent.com',
    generic: 'https://your-idp.example.com',
  }

  return (
    <div className="space-y-10 max-w-3xl">
      {/* ── SSO Configurations ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Single Sign-On (OIDC)</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              Connect an Identity Provider for enterprise SSO login.
            </p>
          </div>
          <button
            onClick={() => setShowSsoForm((v) => !v)}
            className="flex items-center gap-1.5 rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600"
          >
            <Plus className="h-4 w-4" />
            Add Provider
          </button>
        </div>

        {showSsoForm && (
          <form onSubmit={handleCreateSso} className="mb-6 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-5 space-y-4">
            <h3 className="text-sm font-medium text-gray-800 dark:text-gray-200">New SSO Provider</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-gray-600 dark:text-gray-400">Provider</label>
                <select
                  className={inputCls + ' w-full'}
                  value={ssoForm.provider}
                  onChange={(e) => setSsoForm((f) => ({
                    ...f, provider: e.target.value,
                    issuer_url: PROVIDER_HINTS[e.target.value] ?? '',
                  }))}
                >
                  {PROVIDERS.map((p) => (
                    <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-gray-600 dark:text-gray-400">Default Role</label>
                <select
                  className={inputCls + ' w-full'}
                  value={ssoForm.default_role}
                  onChange={(e) => setSsoForm((f) => ({ ...f, default_role: e.target.value }))}
                >
                  <option value="member">Member</option>
                  <option value="editor">Editor</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-gray-600 dark:text-gray-400">Issuer URL *</label>
              <input
                className={inputCls + ' w-full'}
                placeholder={PROVIDER_HINTS[ssoForm.provider]}
                value={ssoForm.issuer_url}
                onChange={(e) => setSsoForm((f) => ({ ...f, issuer_url: e.target.value }))}
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-gray-600 dark:text-gray-400">Client ID *</label>
                <input
                  className={inputCls + ' w-full'}
                  placeholder="client_id"
                  value={ssoForm.client_id}
                  onChange={(e) => setSsoForm((f) => ({ ...f, client_id: e.target.value }))}
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-gray-600 dark:text-gray-400">Client Secret *</label>
                <input
                  className={inputCls + ' w-full'}
                  type="password"
                  placeholder="client_secret"
                  value={ssoForm.client_secret}
                  onChange={(e) => setSsoForm((f) => ({ ...f, client_secret: e.target.value }))}
                  required
                />
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-gray-600 dark:text-gray-400">Scopes</label>
              <input
                className={inputCls + ' w-full'}
                value={ssoForm.scopes}
                onChange={(e) => setSsoForm((f) => ({ ...f, scopes: e.target.value }))}
              />
            </div>
            <div className="flex gap-2 pt-1">
              <button
                type="submit"
                disabled={creatingSso}
                className="rounded bg-indigo-600 px-4 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {creatingSso ? 'Creating…' : 'Create'}
              </button>
              <button
                type="button"
                onClick={() => setShowSsoForm(false)}
                className="rounded border border-gray-300 dark:border-gray-600 px-4 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {loading ? (
          <div className="text-sm text-gray-500 dark:text-gray-400">Loading…</div>
        ) : configs.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-200 dark:border-gray-700 p-8 text-center text-sm text-gray-400 dark:text-gray-500">
            No SSO providers configured yet.
          </div>
        ) : (
          <div className="space-y-2">
            {configs.map((cfg) => (
              <div
                key={cfg.id}
                className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100 capitalize">{cfg.provider}</span>
                    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${cfg.enabled ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'}`}>
                      {cfg.enabled ? 'Active' : 'Disabled'}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">{cfg.issuer_url}</p>
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    Default role: <span className="font-medium">{cfg.default_role}</span>
                    {' · '}Authorize URL:{' '}
                    <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 rounded">
                      /auth/sso/authorize/{cfg.id}
                    </code>
                  </p>
                </div>
                <div className="flex items-center gap-2 ml-4 shrink-0">
                  <button
                    onClick={() => handleToggleSso(cfg)}
                    className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    {cfg.enabled ? 'Disable' : 'Enable'}
                  </button>
                  <button
                    onClick={() => handleDeleteSso(cfg.id)}
                    className="text-red-500 hover:text-red-700 dark:text-red-400"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── SCIM Tokens ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">SCIM 2.0 Provisioning</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              Bearer tokens for automated user provisioning from your IdP.
              Endpoint: <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 rounded">/scim/v2/Users</code>
            </p>
          </div>
        </div>

        {newRawToken && (
          <div className="mb-4 rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-4">
            <p className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-2">
              Copy your SCIM token now — it won&apos;t be shown again.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded bg-white dark:bg-gray-800 border border-amber-200 dark:border-amber-700 px-3 py-2 text-xs break-all font-mono">
                {newRawToken}
              </code>
              <button
                onClick={copyToken}
                className="shrink-0 rounded border border-amber-200 dark:border-amber-700 bg-white dark:bg-gray-800 px-2 py-2 text-amber-700 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-900/30"
              >
                {tokenCopied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              </button>
            </div>
            <button
              onClick={() => setNewRawToken(null)}
              className="mt-2 text-xs text-amber-600 dark:text-amber-400 hover:underline"
            >
              I have saved this token
            </button>
          </div>
        )}

        <form onSubmit={handleCreateScimToken} className="flex items-center gap-2 mb-4">
          <input
            className={inputCls}
            placeholder="Label"
            value={scimLabel}
            onChange={(e) => setScimLabel(e.target.value)}
          />
          <button
            type="submit"
            disabled={creatingToken}
            className="flex items-center gap-1.5 rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <Plus className="h-4 w-4" />
            {creatingToken ? 'Creating…' : 'Generate Token'}
          </button>
        </form>

        {tokens.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-200 dark:border-gray-700 p-6 text-center text-sm text-gray-400 dark:text-gray-500">
            No SCIM tokens yet.
          </div>
        ) : (
          <div className="space-y-2">
            {tokens.map((tok) => (
              <div
                key={tok.id}
                className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded font-mono">
                      {tok.token_prefix}…
                    </code>
                    <span className="text-sm text-gray-800 dark:text-gray-200">{tok.label}</span>
                  </div>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                    Created {new Date(tok.created_at).toLocaleDateString()}
                    {tok.last_used_at && ` · Last used ${new Date(tok.last_used_at).toLocaleDateString()}`}
                  </p>
                </div>
                <button
                  onClick={() => handleDeleteToken(tok.id)}
                  className="text-red-500 hover:text-red-700 dark:text-red-400"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
