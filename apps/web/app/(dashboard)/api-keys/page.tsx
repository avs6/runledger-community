'use client'

import { useSession } from 'next-auth/react'
import { useState, useEffect, useCallback, useMemo } from 'react'
import { toast } from 'sonner'
import { Key, Search, X, SlidersHorizontal, CheckCheck } from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'
import {
  listApiKeys,
  createApiKey,
  revokeApiKey,
  listOrgWorkspaces,
  getApiKeyRotationHistory,
  rotateApiKey,
  listProjects,
  assignProjectKey,
} from '@/lib/api'
import type { ApiKeyResponse, KeyRotationEventResponse, ProjectResponse } from '@/types/api'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

export default function ApiKeysPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { isOrgAdmin, isPlatformAdmin, isWorkspaceAdmin } = useRole()
  const canManageKeys = isWorkspaceAdmin

  const currentUserEmail = (session as Record<string, unknown> | null)?.email as string | undefined
  const workspaceId = (session as Record<string, unknown> | null)?.workspaceId as string | undefined
  const workspaceName = (session as Record<string, unknown> | null)?.workspaceName as string | undefined
  const tenantName = ((session as Record<string, unknown> | null)?.tenantName ?? (session as Record<string, unknown> | null)?.orgName) as string | undefined

  const [apiKeys, setApiKeys] = useState<ApiKeyResponse[]>([])
  const [keySearch, setKeySearch] = useState('')
  const [keyUserFilter, setKeyUserFilter] = useState('')
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyWs, setNewKeyWs] = useState('')
  const [newProjectId, setNewProjectId] = useState('')
  const [newOwnershipType, setNewOwnershipType] = useState('user')
  const [newOwnerReference, setNewOwnerReference] = useState('')
  const [orgWorkspaces, setOrgWorkspaces] = useState<{ id: string; name: string }[]>([])
  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [creatingKey, setCreatingKey] = useState(false)
  const [newRawKey, setNewRawKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey || !canManageKeys) return
    try {
      const [keys, projRes] = await Promise.all([
        listApiKeys(apiKey),
        listProjects(apiKey).catch(() => ({ items: [] })),
      ])
      const orgWs = isOrgAdmin || isPlatformAdmin
        ? await listOrgWorkspaces(apiKey)
        : workspaceId
          ? [{ id: workspaceId, name: workspaceName ?? 'Current workspace' }]
          : []
      setOrgWorkspaces(orgWs)
      setProjects(projRes.items || [])
      setApiKeys(keys.filter((k) => !k.is_session))
    } catch (err) {
      console.error(err)
      toast.error('Failed to load API keys')
    }
  }, [apiKey, canManageKeys, isOrgAdmin, isPlatformAdmin, workspaceId, workspaceName])

  useEffect(() => { load() }, [load])

  async function handleCreateKey(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setCreatingKey(true)
    try {
      const created = await createApiKey(apiKey, {
        name: newKeyName.trim() || null,
        workspace_id: newKeyWs || undefined,
        scopes: [],
        ownership_type: newOwnershipType,
        owner_reference: newOwnerReference.trim() || null,
      })
      if (newProjectId) {
        await assignProjectKey(apiKey, newProjectId, { api_key_id: created.id }).catch(() => {})
      }
      setNewRawKey(created.key)
      setCopied(false)
      setApiKeys((prev) => [created, ...prev])
      setNewKeyName('')
      setNewProjectId('')
      setNewOwnershipType('user')
      setNewOwnerReference('')
      toast.success(`API key created${newProjectId ? ' and bound to project' : ''} — save it now`)
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

  const filteredApiKeys = useMemo(() => {
    let rows = apiKeys
    if (!canManageKeys && currentUserEmail) {
      rows = rows.filter((k) => k.created_by === currentUserEmail)
    }
    if (keyUserFilter.trim()) {
      const u = keyUserFilter.toLowerCase()
      rows = rows.filter((k) => (k.created_by ?? '').toLowerCase().includes(u))
    }
    if (keySearch.trim()) {
      const q = keySearch.toLowerCase()
      rows = rows.filter(
        (k) =>
          (k.name ?? '').toLowerCase().includes(q) ||
          k.key_prefix.toLowerCase().includes(q) ||
          (k.created_by ?? '').toLowerCase().includes(q)
      )
    }
    return rows
  }, [apiKeys, keySearch, keyUserFilter, canManageKeys, currentUserEmail])

  if (!canManageKeys) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">API Keys</h1>
        <p className="mt-4 text-sm text-slate-500">API key management requires workspace-admin access.</p>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6 max-w-4xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">API Keys</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Manage API keys for SDK and MCP authentication. Each key is scoped to a workspace.
          </p>
        </div>
        {workspaceName && (
          <div className="shrink-0 flex flex-col items-end gap-0.5">
            {tenantName && <span className="text-[10px] text-slate-400 dark:text-slate-500">{tenantName}</span>}
            <span className="rounded-full bg-violet-100 px-2.5 py-1 text-xs font-semibold text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
              {workspaceName}
            </span>
          </div>
        )}
      </div>

      {newRawKey && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 dark:border-amber-700 dark:bg-amber-950">
          <p className="mb-1 text-sm font-medium text-amber-800 dark:text-amber-200">
            Save this key — it won&apos;t be shown again.
          </p>
          <p className="mb-3 text-xs text-amber-600 dark:text-amber-400">
            This key is scoped to <strong>{workspaceName ?? 'your workspace'}</strong>.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 rounded bg-white px-3 py-1.5 font-mono text-xs text-gray-800 shadow-inner dark:bg-gray-900 dark:text-gray-100">
              {newRawKey}
            </code>
            <button onClick={handleCopy} className="rounded bg-amber-600 px-3 py-1.5 text-xs text-white hover:bg-amber-700">
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <a href="/mcp" className="rounded bg-violet-600 px-3 py-1.5 text-xs text-white hover:bg-violet-700">
              Set up MCP →
            </a>
            <button onClick={() => setNewRawKey(null)} className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
              Dismiss
            </button>
          </div>
        </div>
      )}

      {canManageKeys ? (
        <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-700 dark:bg-slate-800/40">
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3">
            Create new key <span className="text-violet-600 dark:text-violet-400">{isOrgAdmin || isPlatformAdmin ? '— pick a workspace in your org' : '— current workspace only'}</span>
          </p>
          <form onSubmit={handleCreateKey} className="flex flex-wrap gap-2">
            <input type="text" placeholder="Key name (optional)" value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)} className={inputCls} />
            <select value={newOwnershipType} onChange={(e) => setNewOwnershipType(e.target.value)} className={inputCls}>
              <option value="user">User</option>
              <option value="service_account">Service account</option>
              <option value="agent">Agent</option>
              <option value="org">Org</option>
            </select>
            <input type="text" placeholder="Owner reference (optional)" value={newOwnerReference} onChange={(e) => setNewOwnerReference(e.target.value)} className={inputCls} />
            <select value={newKeyWs} onChange={(e) => setNewKeyWs(e.target.value)} disabled={!isOrgAdmin && !isPlatformAdmin} className={`${inputCls} disabled:cursor-not-allowed disabled:opacity-60`}>
              <option value="">Current workspace ({workspaceName ?? 'default'})</option>
              {orgWorkspaces.map((w) => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
            <select value={newProjectId} onChange={(e) => setNewProjectId(e.target.value)} className={inputCls}>
              <option value="">Project (Optional)</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>Project: {p.name}</option>
              ))}
            </select>
            <button type="submit" disabled={creatingKey} className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
              {creatingKey ? 'Creating…' : 'Create Key'}
            </button>
          </form>
        </div>
      ) : (
        <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800/40 dark:text-slate-400">
          API key management requires <span className="font-medium">workspace-admin</span> access.
        </div>
      )}

      {/* Filter bar */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 px-4 py-3 space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
          <SlidersHorizontal className="h-3.5 w-3.5" /> Filters
        </div>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          {canManageKeys && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 dark:text-slate-400 w-16 shrink-0">Created by</span>
              <div className="relative">
                <input
                  value={keyUserFilter}
                  onChange={(e) => setKeyUserFilter(e.target.value)}
                  placeholder="email…"
                  className={`${inputCls} w-44`}
                />
                {keyUserFilter && (
                  <button onClick={() => setKeyUserFilter('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </div>
          )}
          {keyUserFilter && (
            <button onClick={() => { setKeyUserFilter('') }}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-white ml-auto">
              <X className="h-3.5 w-3.5" /> Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Search */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
          <input
            value={keySearch}
            onChange={(e) => setKeySearch(e.target.value)}
            placeholder={`Search within ${filteredApiKeys.length} key${filteredApiKeys.length !== 1 ? 's' : ''}…`}
            className={`${inputCls} pl-8 w-full`}
          />
          {keySearch && (
            <button onClick={() => setKeySearch('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        {filteredApiKeys.length !== apiKeys.length && (
          <span className="text-xs font-medium text-violet-600 dark:text-violet-400">
            {filteredApiKeys.length} of {apiKeys.length} keys
          </span>
        )}
        {!canManageKeys && (
          <span className="text-xs text-slate-400 italic">Showing your keys only</span>
        )}
      </div>

      <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
            <tr>
              <th className="px-4 py-2 text-left">Prefix</th>
              <th className="px-4 py-2 text-left">Name</th>
              <th className="px-4 py-2 text-left">Workspace</th>
              <th className="px-4 py-2 text-left">Ownership</th>
              <th className="px-4 py-2 text-left">Created</th>
              <th className="px-4 py-2 text-left">Created By</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {filteredApiKeys.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-400 dark:text-gray-500">
                {apiKeys.length === 0 ? 'No active API keys.' : 'No keys match your filters.'}
              </td></tr>
            ) : (
              filteredApiKeys.map((k) => (
                <tr key={k.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                  <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">{k.key_prefix}…</td>
                  <td className="px-4 py-2 text-gray-600 dark:text-gray-400">{k.name ?? '—'}</td>
                  <td className="px-4 py-2 text-xs text-violet-600 dark:text-violet-400">{k.workspace_name ?? '—'}</td>
                  <td className="px-4 py-2 text-xs text-slate-500 dark:text-slate-400">
                    <span className="font-medium">{k.ownership_type}</span>
                    {k.owner_reference ? ` · ${k.owner_reference}` : ''}
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-500">{new Date(k.created_at).toLocaleString()}</td>
                  <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">{k.created_by ?? '—'}</td>
                  <td className="px-4 py-2 text-right">
                    <button onClick={() => handleRevoke(k.id)} className="text-xs text-red-500 hover:text-red-700 hover:underline dark:text-red-400">Revoke</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {apiKey && canManageKeys && <KeyRotationPanel apiKey={apiKey} apiKeys={apiKeys} />}
    </div>
  )
}

function KeyRotationPanel({ apiKey, apiKeys }: { apiKey: string; apiKeys: ApiKeyResponse[] }) {
  const [selectedKeyId, setSelectedKeyId] = useState('')
  const [history, setHistory] = useState<KeyRotationEventResponse[]>([])
  const [loading, setLoading] = useState(false)
  const [rotating, setRotating] = useState(false)
  const [graceHours, setGraceHours] = useState('24')
  const [latestKey, setLatestKey] = useState<string | null>(null)

  async function loadHistory(keyId: string) {
    if (!keyId) {
      setHistory([])
      return
    }
    setLoading(true)
    try {
      const data = await getApiKeyRotationHistory(apiKey, keyId)
      setHistory(data.items)
    } catch {
      toast.error('Failed to load rotation history')
    } finally {
      setLoading(false)
    }
  }

  async function handleRotate() {
    if (!selectedKeyId) return
    setRotating(true)
    try {
      const result = await rotateApiKey(apiKey, selectedKeyId, parseInt(graceHours, 10) || 24)
      setLatestKey(result.key)
      await loadHistory(selectedKeyId)
      toast.success(`Replacement key issued. Old key expires ${result.expires_old_at ? new Date(result.expires_old_at).toLocaleString() : 'immediately'}.`)
    } catch {
      toast.error('Failed to rotate API key')
    } finally {
      setRotating(false)
    }
  }

  return (
    <div className="space-y-4 rounded-xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-700 dark:bg-slate-800/40">
      <div>
        <h2 className="text-base font-semibold text-slate-900 dark:text-white">Rotation Automation</h2>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Issue a replacement key with a grace period, then inspect the rotation chain for auditability.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <select
          value={selectedKeyId}
          onChange={(e) => {
            const keyId = e.target.value
            setSelectedKeyId(keyId)
            void loadHistory(keyId)
          }}
          className={inputCls + ' min-w-[260px]'}
        >
          <option value="">Select a key...</option>
          {apiKeys.map((key) => (
            <option key={key.id} value={key.id}>
              {key.key_prefix}... {key.name ?? 'unnamed'}{key.owner_reference ? ` · ${key.owner_reference}` : ''}
            </option>
          ))}
        </select>
        <input
          value={graceHours}
          onChange={(e) => setGraceHours(e.target.value)}
          className={inputCls + ' w-32'}
          placeholder="Grace hours"
        />
        <button
          onClick={() => void handleRotate()}
          disabled={!selectedKeyId || rotating}
          className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {rotating ? 'Rotating...' : 'Rotate key'}
        </button>
      </div>

      {latestKey && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-700 dark:bg-amber-950">
          <p className="font-medium text-amber-800 dark:text-amber-200">New key material</p>
          <code className="mt-2 block break-all rounded bg-white px-3 py-2 text-xs text-slate-800 dark:bg-slate-900 dark:text-slate-100">
            {latestKey}
          </code>
        </div>
      )}

      {!selectedKeyId ? (
        <p className="text-sm text-slate-400">Pick a key to inspect its rotation history.</p>
      ) : loading ? (
        <p className="text-sm text-slate-400">Loading history...</p>
      ) : history.length === 0 ? (
        <p className="text-sm text-slate-400">No rotation events recorded for this key yet.</p>
      ) : (
        <div className="overflow-x-auto rounded border border-slate-200 dark:border-slate-700">
          <table className="w-full text-sm">
            <thead className="bg-white text-xs uppercase text-slate-500 dark:bg-slate-900 dark:text-slate-400">
              <tr>
                <th className="px-4 py-2 text-left">Created</th>
                <th className="px-4 py-2 text-left">From</th>
                <th className="px-4 py-2 text-left">To</th>
                <th className="px-4 py-2 text-left">Triggered By</th>
                <th className="px-4 py-2 text-left">Grace Ends</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {history.map((event) => (
                <tr key={event.id}>
                  <td className="px-4 py-2 text-xs text-slate-500 dark:text-slate-400">{new Date(event.created_at).toLocaleString()}</td>
                  <td className="px-4 py-2 font-mono text-xs dark:text-slate-200">{event.rotated_from_prefix}</td>
                  <td className="px-4 py-2 font-mono text-xs dark:text-slate-200">{event.rotated_to_prefix}</td>
                  <td className="px-4 py-2 text-xs text-slate-500 dark:text-slate-400">{event.triggered_by ?? 'system'}</td>
                  <td className="px-4 py-2 text-xs text-slate-500 dark:text-slate-400">{event.grace_expires_at ? new Date(event.grace_expires_at).toLocaleString() : 'immediate'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
