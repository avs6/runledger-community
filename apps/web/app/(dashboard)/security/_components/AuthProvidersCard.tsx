'use client'

import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Pencil, Plus, Trash2, X } from 'lucide-react'
import { AsyncCard } from '@/components/ui/async-card'
import { useConfirm } from '@/components/ui/confirm-dialog'
import {
  deleteAuthProvider,
  listAuthProviders,
  saveAuthProvider,
  type LDAPProvider,
  type OAuth2Provider,
  type ProviderKind,
} from '@/lib/api'
import { SecretInput } from './SecretInput'

type Provider = OAuth2Provider | LDAPProvider

interface FieldDef {
  key: string
  label: string
  placeholder?: string
  required?: boolean
  type?: 'text' | 'checkbox'
}

const FIELDS: Record<ProviderKind, FieldDef[]> = {
  oauth2: [
    { key: 'name', label: 'Name', placeholder: 'GitHub SSO', required: true },
    { key: 'authorization_endpoint', label: 'Authorization endpoint', placeholder: 'https://idp/authorize', required: true },
    { key: 'token_endpoint', label: 'Token endpoint', placeholder: 'https://idp/token', required: true },
    { key: 'userinfo_endpoint', label: 'Userinfo endpoint', placeholder: 'https://idp/userinfo', required: true },
    { key: 'client_id', label: 'Client ID', required: true },
    { key: 'scopes', label: 'Scopes', placeholder: 'openid email profile' },
    { key: 'auto_provision', label: 'Auto-provision users', type: 'checkbox' },
    { key: 'is_active', label: 'Active', type: 'checkbox' },
  ],
  ldap: [
    { key: 'name', label: 'Name', placeholder: 'Corporate AD', required: true },
    { key: 'server_url', label: 'Server URL', placeholder: 'ldaps://ldap.example.com', required: true },
    { key: 'bind_dn', label: 'Service bind DN', placeholder: 'cn=svc,dc=example,dc=com' },
    { key: 'user_search_base', label: 'User search base', placeholder: 'ou=people,dc=example,dc=com', required: true },
    { key: 'user_search_filter', label: 'User search filter', placeholder: '(uid={username})' },
    { key: 'use_ssl', label: 'Use SSL', type: 'checkbox' },
    { key: 'start_tls', label: 'StartTLS', type: 'checkbox' },
    { key: 'auto_provision', label: 'Auto-provision users', type: 'checkbox' },
    { key: 'is_active', label: 'Active', type: 'checkbox' },
  ],
}

const SECRET_FIELD: Record<ProviderKind, { key: 'client_secret' | 'bind_password'; label: string }> = {
  oauth2: { key: 'client_secret', label: 'Client secret' },
  ldap: { key: 'bind_password', label: 'Bind password' },
}

const TITLES: Record<ProviderKind, { title: string; description: string }> = {
  oauth2: { title: 'OAuth2 providers', description: 'Authorization-code sign-in with PKCE. The client secret is write-only.' },
  ldap: { title: 'LDAP providers', description: 'Directory sign-in. Binds never run anonymously; the bind password is write-only.' },
}

function emptyForm(kind: ProviderKind): Record<string, string | boolean> {
  const form: Record<string, string | boolean> = {}
  for (const f of FIELDS[kind]) form[f.key] = f.type === 'checkbox' ? f.key === 'is_active' : ''
  return form
}

/** Full CRUD for OAuth2 or LDAP providers, with masked "replace" secret fields. */
export function AuthProvidersCard({ apiKey, kind }: { apiKey: string; kind: ProviderKind }) {
  const { confirm, dialog } = useConfirm()
  const [items, setItems] = useState<Provider[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<Provider | null>(null)
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<Record<string, string | boolean>>(() => emptyForm(kind))
  const [secret, setSecret] = useState<string | undefined>(undefined)
  const [saving, setSaving] = useState(false)
  const secretField = SECRET_FIELD[kind]

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setItems(await listAuthProviders<Provider>(apiKey, kind))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load providers')
    } finally {
      setLoading(false)
    }
  }, [apiKey, kind])

  useEffect(() => { void load() }, [load])

  function startCreate() {
    setEditing(null)
    setForm(emptyForm(kind))
    setSecret(undefined)
    setOpen(true)
  }

  function startEdit(p: Provider) {
    const next = emptyForm(kind)
    const record = p as unknown as Record<string, unknown>
    for (const f of FIELDS[kind]) {
      const v = record[f.key]
      next[f.key] = f.type === 'checkbox' ? Boolean(v) : v == null ? '' : String(v)
    }
    setEditing(p)
    setForm(next)
    setSecret(undefined)
    setOpen(true)
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    const body: Record<string, unknown> = {}
    for (const f of FIELDS[kind]) {
      const v = form[f.key]
      body[f.key] = f.type === 'checkbox' ? Boolean(v) : (typeof v === 'string' && v.trim()) || null
    }
    if (secret) body[secretField.key] = secret // omitted = keep the stored value
    try {
      await saveAuthProvider<Provider>(apiKey, kind, body, editing?.id)
      toast.success(editing ? 'Provider updated' : 'Provider added')
      setOpen(false)
      void load()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function remove(p: Provider) {
    const ok = await confirm({
      title: `Delete ${p.name}?`,
      description: 'Users can no longer sign in through this provider. The stored secret is deleted.',
      confirmLabel: 'Delete',
      destructive: true,
    })
    if (!ok) return
    try {
      await deleteAuthProvider(apiKey, kind, p.id)
      toast.success('Provider deleted')
      void load()
    } catch {
      toast.error('Delete failed')
    }
  }

  const storedSecret = editing ? (editing as unknown as Record<string, string | null>)[secretField.key] : null

  return (
    <AsyncCard
      title={TITLES[kind].title}
      description={TITLES[kind].description}
      loading={loading}
      error={error}
      onRetry={() => void load()}
      empty={!open && items.length === 0}
      emptyTitle="None configured"
      emptyDescription="Add a provider to let users sign in with it."
      actions={
        <button
          type="button"
          onClick={open ? () => setOpen(false) : startCreate}
          aria-label={open ? 'Close the provider form' : `Add ${kind === 'ldap' ? 'LDAP' : 'OAuth2'} provider`}
          className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          {open ? <X className="h-4 w-4" aria-hidden="true" /> : <Plus className="h-4 w-4" aria-hidden="true" />}
        </button>
      }
    >
      {dialog}
      {open && (
        <form onSubmit={submit} className="mb-4 grid gap-3 rounded-lg border border-slate-200 p-3 sm:grid-cols-2 dark:border-slate-700">
          {FIELDS[kind].map((f) =>
            f.type === 'checkbox' ? (
              <label key={f.key} className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={Boolean(form[f.key])}
                  onChange={(e) => setForm((prev) => ({ ...prev, [f.key]: e.target.checked }))}
                />
                {f.label}
              </label>
            ) : (
              <label key={f.key} className="block text-xs text-slate-500 dark:text-slate-400">
                {f.label}
                <input
                  value={String(form[f.key] ?? '')}
                  onChange={(e) => setForm((prev) => ({ ...prev, [f.key]: e.target.value }))}
                  placeholder={f.placeholder}
                  required={f.required}
                  className="mt-1 w-full rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                />
              </label>
            ),
          )}
          <div className="sm:col-span-2">
            <SecretInput
              key={editing?.id ?? 'new'}
              id={`${kind}-secret`}
              label={secretField.label}
              stored={storedSecret}
              value={secret}
              onChange={setSecret}
              required={kind === 'oauth2' || Boolean(form.bind_dn)}
            />
          </div>
          <div className="sm:col-span-2">
            <button type="submit" disabled={saving} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
              {saving ? 'Saving…' : editing ? 'Save provider' : 'Add provider'}
            </button>
          </div>
        </form>
      )}
      <ul className="space-y-2">
        {items.map((p) => (
          <li key={p.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
            <div className="min-w-0">
              <p className="font-medium text-slate-900 dark:text-slate-100">{p.name}</p>
              <p className="mt-0.5 break-all font-mono text-xs text-slate-500 dark:text-slate-400">
                {'server_url' in p ? p.server_url : p.authorization_endpoint}
              </p>
              <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                {p.is_active ? 'active' : 'inactive'} · {secretField.label.toLowerCase()}{' '}
                {(p as unknown as Record<string, string | null>)[secretField.key] ? 'stored' : 'not set'}
              </p>
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={() => startEdit(p)} aria-label={`Edit ${p.name}`} className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700">
                <Pencil className="h-4 w-4" aria-hidden="true" />
              </button>
              <button type="button" onClick={() => void remove(p)} aria-label={`Delete ${p.name}`} className="rounded-lg border border-rose-200 p-2 text-rose-600 hover:bg-rose-50 dark:border-rose-900/40 dark:text-rose-300 dark:hover:bg-rose-950/30">
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </li>
        ))}
      </ul>
    </AsyncCard>
  )
}
