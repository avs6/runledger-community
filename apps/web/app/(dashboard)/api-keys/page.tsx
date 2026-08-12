'use client'

import { useSession } from 'next-auth/react'
import { useState, useEffect, useCallback, useMemo } from 'react'
import { toast } from 'sonner'
import { Key, Pencil, Save, Search, SlidersHorizontal, X } from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'
import {
  listApiKeys,
  createApiKey,
  revokeApiKey,
  listOrgWorkspaces,
  getApiKeyRotationHistory,
  rotateApiKey,
  updateApiKey,
} from '@/lib/api'
import type { ApiKeyResponse, KeyRotationEventResponse } from '@/types/api'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

export default function ApiKeysPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { isOrgElevated, isPlatformAdmin, isWorkspaceAdmin } = useRole()
  const canManageKeys = isWorkspaceAdmin

  const workspaceId = (session as Record<string, unknown> | null)?.workspaceId as string | undefined
  const workspaceName = (session as Record<string, unknown> | null)?.workspaceName as string | undefined
  const tenantName = ((session as Record<string, unknown> | null)?.tenantName ?? (session as Record<string, unknown> | null)?.orgName) as string | undefined

  const [apiKeys, setApiKeys] = useState<ApiKeyResponse[]>([])
  const [keySearch, setKeySearch] = useState('')
  const [keyUserFilter, setKeyUserFilter] = useState('')
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyWs, setNewKeyWs] = useState('')
  const [newOwnershipType, setNewOwnershipType] = useState('user')
  const [newOwnerReference, setNewOwnerReference] = useState('')
  const [orgWorkspaces, setOrgWorkspaces] = useState<{ id: string; name: string }[]>([])
  const [creatingKey, setCreatingKey] = useState(false)
  const [newRawKey, setNewRawKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [editingKeyId, setEditingKeyId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editOwnershipType, setEditOwnershipType] = useState('user')
  const [editOwnerReference, setEditOwnerReference] = useState('')
  const [savingKeyId, setSavingKeyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!apiKey || !canManageKeys) return
    try {
      const keys = await listApiKeys(apiKey)
      const orgWs = isOrgElevated || isPlatformAdmin
        ? await listOrgWorkspaces(apiKey)
        : workspaceId
          ? [{ id: workspaceId, name: workspaceName ?? 'Current workspace' }]
          : []
      setOrgWorkspaces(orgWs)
      setApiKeys(keys.filter((k) => !k.is_session))
    } catch (err) {
      console.error(err)
      toast.error('Failed to load API keys')
    }
  }, [apiKey, canManageKeys, isOrgElevated, isPlatformAdmin, workspaceId, workspaceName])

  useEffect(() => { void load() }, [load])

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
      setNewRawKey(created.key)
      setCopied(false)
      setApiKeys((prev) => [created, ...prev])
      setNewKeyName('')
      setNewOwnershipType('user')
      setNewOwnerReference('')
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

  function startEdit(key: ApiKeyResponse) {
    setEditingKeyId(key.id)
    setEditName(key.name ?? '')
    setEditOwnershipType(key.ownership_type)
    setEditOwnerReference(key.owner_reference ?? '')
  }

  async function handleSaveEdit(key: ApiKeyResponse) {
    if (!apiKey) return
    setSavingKeyId(key.id)
    try {
      const updated = await updateApiKey(apiKey, key.id, {
        name: editName.trim() || null,
        ownership_type: editOwnershipType,
        owner_reference: editOwnerReference.trim() || null,
      })
      setApiKeys((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
      setEditingKeyId(null)
      toast.success('API key updated')
    } catch (err) {
      console.error(err)
      toast.error('Failed to update API key')
    } finally {
      setSavingKeyId(null)
    }
  }

  const filteredApiKeys = useMemo(() => {
    let rows = apiKeys
    if (keyUserFilter.trim()) {
      const userQuery = keyUserFilter.toLowerCase()
      rows = rows.filter((k) => (k.created_by ?? '').toLowerCase().includes(userQuery))
    }
    if (keySearch.trim()) {
      const query = keySearch.toLowerCase()
      rows = rows.filter(
        (k) =>
          (k.name ?? '').toLowerCase().includes(query) ||
          k.key_prefix.toLowerCase().includes(query) ||
          (k.created_by ?? '').toLowerCase().includes(query) ||
          (k.owner_reference ?? '').toLowerCase().includes(query)
      )
    }
    return rows
  }, [apiKeys, keySearch, keyUserFilter])

  if (!canManageKeys) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">API Keys</h1>
        <p className="mt-4 text-sm text-slate-500">API key management requires workspace-admin access.</p>
      </div>
    )
  }

  return (
    <div className="max-w-5xl space-y-6 p-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">API Keys</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Manage workspace-scoped keys for SDK, gateway, and MCP authentication.
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
            Save this key. It will not be shown again.
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

      <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-700 dark:bg-slate-800/40">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Create new key <span className="text-violet-600 dark:text-violet-400">{isOrgElevated || isPlatformAdmin ? '— pick a workspace in your org' : '— current workspace only'}</span>
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
          <select value={newKeyWs} onChange={(e) => setNewKeyWs(e.target.value)} disabled={!isOrgElevated && !isPlatformAdmin} className={`${inputCls} disabled:cursor-not-allowed disabled:opacity-60`}>
            <option value="">Current workspace ({workspaceName ?? 'default'})</option>
            {orgWorkspaces.map((workspace) => (
              <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
            ))}
          </select>
          <button type="submit" disabled={creatingKey} className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
            {creatingKey ? 'Creating…' : 'Create Key'}
          </button>
        </form>
      </div>

      <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 space-y-3 dark:border-slate-700 dark:bg-slate-800/50">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          <SlidersHorizontal className="h-3.5 w-3.5" /> Filters
        </div>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <div className="flex items-center gap-2">
            <span className="w-16 shrink-0 text-xs text-slate-500 dark:text-slate-400">Created by</span>
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
          {keyUserFilter && (
            <button
              onClick={() => setKeyUserFilter('')}
              className="ml-auto flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-white"
            >
              <X className="h-3.5 w-3.5" /> Clear filters
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <input
            value={keySearch}
            onChange={(e) => setKeySearch(e.target.value)}
            placeholder={`Search within ${filteredApiKeys.length} key${filteredApiKeys.length !== 1 ? 's' : ''}…`}
            className={`${inputCls} w-full pl-8`}
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
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-gray-400 dark:text-gray-500">
                  {apiKeys.length === 0 ? 'No active API keys.' : 'No keys match your filters.'}
                </td>
              </tr>
            ) : (
              filteredApiKeys.map((key) => (
                <tr key={key.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                  <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">{key.key_prefix}…</td>
                  <td className="px-4 py-2 text-gray-600 dark:text-gray-400">
                    {editingKeyId === key.id ? (
                      <input value={editName} onChange={(e) => setEditName(e.target.value)} className={`${inputCls} w-full`} />
                    ) : (key.name ?? '—')}
                  </td>
                  <td className="px-4 py-2 text-xs text-violet-600 dark:text-violet-400">{key.workspace_name ?? '—'}</td>
                  <td className="px-4 py-2 text-xs text-slate-500 dark:text-slate-400">
                    {editingKeyId === key.id ? (
                      <div className="flex flex-col gap-2">
                        <select value={editOwnershipType} onChange={(e) => setEditOwnershipType(e.target.value)} className={inputCls}>
                          <option value="user">User</option>
                          <option value="service_account">Service account</option>
                          <option value="agent">Agent</option>
                          <option value="org">Org</option>
                        </select>
                        <input value={editOwnerReference} onChange={(e) => setEditOwnerReference(e.target.value)} placeholder="Owner reference" className={inputCls} />
                      </div>
                    ) : (
                      <>
                        <span className="font-medium">{key.ownership_type}</span>
                        {key.owner_reference ? ` · ${key.owner_reference}` : ''}
                      </>
                    )}
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-500">{new Date(key.created_at).toLocaleString()}</td>
                  <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">{key.created_by ?? '—'}</td>
                  <td className="px-4 py-2 text-right">
                    <div className="flex items-center justify-end gap-3">
                      {editingKeyId === key.id ? (
                        <>
                          <button onClick={() => void handleSaveEdit(key)} disabled={savingKeyId === key.id} className="inline-flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-800 dark:text-emerald-400">
                            <Save className="h-3.5 w-3.5" />
                            {savingKeyId === key.id ? 'Saving…' : 'Save'}
                          </button>
                          <button onClick={() => setEditingKeyId(null)} className="text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400">Cancel</button>
                        </>
                      ) : (
                        <>
                          <button onClick={() => startEdit(key)} className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 dark:text-slate-300">
                            <Pencil className="h-3.5 w-3.5" />
                            Edit
                          </button>
                          <button onClick={() => handleRevoke(key.id)} className="text-xs text-red-500 hover:text-red-700 hover:underline dark:text-red-400">Revoke</button>
                        </>
                      )}
                    </div>
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
