'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import * as DialogPrimitive from '@radix-ui/react-dialog'
import { toast } from 'sonner'
import { History, KeyRound, RefreshCw, RotateCw, ShieldCheck } from 'lucide-react'
import { AsyncCard } from '@/components/ui/async-card'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import {
  listAuditPage,
  listSecrets,
  rewrapAllSecrets,
  rewrapSecret,
  rotateSecret,
  type AuditRow,
  type SecretAgeStatus,
  type SecretInventory,
  type SecretRecord,
} from '@/lib/api'
import type { StaticRoute } from '@/lib/routes'

const AUDIT_ROUTE: StaticRoute = '/audit'

const KIND_LABELS: Record<string, string> = {
  oidc_client_secret: 'OIDC client secret',
  oauth2_client_secret: 'OAuth2 client secret',
  ldap_bind_password: 'LDAP bind password',
  search_provider_auth: 'Search provider',
  passthrough_auth: 'Pass-through auth',
  passthrough_headers: 'Pass-through headers',
  notification_webhook: 'Notification webhook',
  evaluator_api_key: 'Evaluator key',
}

const AGE_STYLES: Record<SecretAgeStatus, string> = {
  fresh: 'bg-status-success/15 text-status-success',
  aging: 'bg-status-warning/15 text-status-warning',
  stale: 'bg-status-error/15 text-status-error',
}

function relative(iso: string): string {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
  if (days <= 0) return 'today'
  if (days === 1) return 'yesterday'
  return `${days} days ago`
}

export function AgeBadge({ record }: { record: SecretRecord }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${AGE_STYLES[record.age_status]}`}
      title={`Last rotated ${new Date(record.rotated_at).toLocaleString()}`}
    >
      {record.age_days}d · {record.age_status}
    </span>
  )
}

/**
 * Secret inventory (review ENH): every stored credential with its age and
 * last-rotated badges, the key that wraps it, "Rotate" (new value), "Re-wrap"
 * (re-encrypt with the current master key) and a per-secret audit timeline.
 * The age filter lives in the URL (`?secret_age=`).
 */
export function SecretsInventory({ apiKey }: { apiKey: string }) {
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()
  const ageFilter = (params.get('secret_age') ?? '') as SecretAgeStatus | ''
  const { confirm, dialog } = useConfirm()

  const [data, setData] = useState<SecretInventory | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [rotating, setRotating] = useState<SecretRecord | null>(null)
  const [timelineFor, setTimelineFor] = useState<SecretRecord | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await listSecrets(apiKey))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load secrets')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { void load() }, [load])

  const setAgeFilter = (value: string) => {
    const next = new URLSearchParams(params.toString())
    if (value) next.set('secret_age', value)
    else next.delete('secret_age')
    router.replace(`${pathname}${next.toString() ? `?${next}` : ''}`, { scroll: false })
  }

  const rows = useMemo(
    () => (data?.items ?? []).filter((r) => !ageFilter || r.age_status === ageFilter),
    [data, ageFilter],
  )
  const counts = useMemo(() => {
    const c = { fresh: 0, aging: 0, stale: 0, rewrap: 0 }
    for (const r of data?.items ?? []) {
      c[r.age_status] += 1
      if (!r.key_current) c.rewrap += 1
    }
    return c
  }, [data])

  async function handleRewrap(record: SecretRecord) {
    try {
      await rewrapSecret(apiKey, record.id)
      toast.success('Secret re-encrypted with the current key')
      void load()
    } catch {
      toast.error('Re-wrap failed')
    }
  }

  async function handleRewrapAll() {
    const ok = await confirm({
      title: 'Re-encrypt all secrets?',
      description: `${counts.rewrap} secret(s) are wrapped by an older key. Values do not change; each re-wrap is audited.`,
      confirmLabel: 'Re-wrap all',
    })
    if (!ok) return
    try {
      const res = await rewrapAllSecrets(apiKey)
      toast.success(`Re-wrapped ${res.rewrapped} secret(s)`)
      void load()
    } catch {
      toast.error('Re-wrap failed')
    }
  }

  const columns: DataTableColumn<SecretRecord>[] = [
    {
      key: 'label',
      header: 'Secret',
      sortable: true,
      value: (r) => r.label ?? r.kind,
      render: (r) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-slate-900 dark:text-slate-100">{r.label ?? r.kind}</p>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">{KIND_LABELS[r.kind] ?? r.kind}</p>
        </div>
      ),
    },
    {
      key: 'age_days',
      header: 'Age',
      sortable: true,
      value: (r) => r.age_days,
      render: (r) => <AgeBadge record={r} />,
    },
    {
      key: 'rotated_at',
      header: 'Last rotated',
      sortable: true,
      value: (r) => r.rotated_at,
      render: (r) => (
        <span className="text-xs text-slate-600 dark:text-slate-300" title={new Date(r.rotated_at).toLocaleString()}>
          {relative(r.rotated_at)}
          {r.rotated_by_label ? <span className="text-slate-400"> · {r.rotated_by_label}</span> : null}
        </span>
      ),
    },
    {
      key: 'rotation_count',
      header: 'Rotations',
      sortable: true,
      defaultHidden: true,
    },
    {
      key: 'key_id',
      header: 'Key',
      value: (r) => r.key_id ?? '',
      render: (r) => (
        <span
          className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[11px] ${r.key_current ? 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300' : 'bg-status-warning/15 text-status-warning'}`}
          title={r.key_current ? 'Wrapped by the current master key' : 'Wrapped by an older key: re-wrap'}
        >
          {r.key_current ? <ShieldCheck className="h-3 w-3" aria-hidden="true" /> : <KeyRound className="h-3 w-3" aria-hidden="true" />}
          {r.key_id ?? 'legacy'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (r) => (
        <div className="flex justify-end gap-1.5">
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); setRotating(r) }}
            aria-label={`Rotate ${r.label ?? r.kind}`}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            <RotateCw className="h-3 w-3" aria-hidden="true" /> Rotate
          </button>
          {!r.key_current && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); void handleRewrap(r) }}
              aria-label={`Re-wrap ${r.label ?? r.kind} with the current key`}
              className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              Re-wrap
            </button>
          )}
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); setTimelineFor(r) }}
            aria-label={`Audit timeline for ${r.label ?? r.kind}`}
            className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            <History className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>
      ),
    },
  ]

  return (
    <AsyncCard
      title="Secrets"
      description={`Every stored credential, encrypted at rest. Rotate anything older than ${data?.max_age_days ?? 90} days.`}
      loading={loading && !data}
      error={error}
      onRetry={() => void load()}
      empty={Boolean(data) && data!.items.length === 0}
      emptyTitle="No stored secrets"
      emptyDescription="Auth-provider secrets, search and pass-through credentials, webhook URLs and evaluator keys appear here once configured."
      actions={
        <div className="flex items-center gap-2">
          {counts.rewrap > 0 && (
            <button
              type="button"
              onClick={() => void handleRewrapAll()}
              className="rounded-lg border border-status-warning/40 px-2.5 py-1 text-xs font-medium text-status-warning hover:bg-status-warning/10"
            >
              Re-wrap {counts.rewrap}
            </button>
          )}
          <button
            type="button"
            onClick={() => void load()}
            aria-label="Refresh secrets"
            className="rounded-lg border border-slate-200 p-1.5 text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
          </button>
        </div>
      }
    >
      {dialog}
      {data?.using_derived_key && (
        <p role="note" className="mb-3 rounded-lg border border-status-warning/40 bg-status-warning/10 px-3 py-2 text-xs text-status-warning">
          Secrets are encrypted with a key derived from SECRET_KEY. Set SECRETS_MASTER_KEY (or SECRETS_KMS_KEY_ID) in
          production, then re-wrap.
        </p>
      )}
      <div role="group" aria-label="Filter secrets by age" className="mb-3 flex flex-wrap gap-1.5 text-xs">
        {([['', `All ${data?.items.length ?? 0}`], ['fresh', `Fresh ${counts.fresh}`], ['aging', `Aging ${counts.aging}`], ['stale', `Stale ${counts.stale}`]] as const).map(([value, text]) => (
          <button
            key={value || 'all'}
            type="button"
            aria-pressed={ageFilter === value}
            onClick={() => setAgeFilter(value)}
            className={`rounded-full border px-2.5 py-0.5 ${ageFilter === value ? 'border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-200' : 'border-slate-200 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800'}`}
          >
            {text}
          </button>
        ))}
      </div>
      <DataTable
        label="Stored secrets"
        urlPrefix="secrets_"
        rows={rows}
        rowKey={(r) => r.id}
        columns={columns}
        searchPlaceholder="Search secrets…"
        csvFileName="secrets-inventory.csv"
        emptyTitle="No secrets match this filter"
        onRowClick={(r) => setTimelineFor(r)}
      />
      <RotateDialog
        apiKey={apiKey}
        record={rotating}
        onClose={() => setRotating(null)}
        onRotated={() => { setRotating(null); void load() }}
      />
      <SecretTimeline apiKey={apiKey} record={timelineFor} onClose={() => setTimelineFor(null)} />
    </AsyncCard>
  )
}

function RotateDialog({
  apiKey,
  record,
  onClose,
  onRotated,
}: {
  apiKey: string
  record: SecretRecord | null
  onClose: () => void
  onRotated: () => void
}) {
  const [values, setValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  useEffect(() => { setValues({}) }, [record])
  const fields = record?.fields.length ? record.fields : ['value']

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!record) return
    setSaving(true)
    try {
      const body = record.fields.length ? { values } : { value: values.value }
      await rotateSecret(apiKey, record.id, body)
      toast.success('Secret rotated')
      onRotated()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Rotation failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <DialogPrimitive.Root open={record !== null} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40" />
        <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border border-slate-200 bg-white p-5 shadow-xl dark:border-slate-700 dark:bg-slate-900">
          <DialogPrimitive.Title className="text-base font-semibold text-slate-900 dark:text-white">
            Rotate {record?.label ?? record?.kind}
          </DialogPrimitive.Title>
          <DialogPrimitive.Description className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Paste the new value from the provider. The old value stops being used immediately; the change is audited.
          </DialogPrimitive.Description>
          <form onSubmit={submit} className="mt-4 space-y-3">
            {fields.map((field) => (
              <label key={field} className="block text-xs text-slate-500 dark:text-slate-400">
                {field === 'value' ? 'New value' : `New ${field}`}
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  value={values[field] ?? ''}
                  onChange={(e) => setValues((prev) => ({ ...prev, [field]: e.target.value }))}
                  className="mt-1 w-full rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                />
              </label>
            ))}
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800">
                Cancel
              </button>
              <button type="submit" disabled={saving} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                {saving ? 'Rotating…' : 'Rotate secret'}
              </button>
            </div>
          </form>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}

function SecretTimeline({ apiKey, record, onClose }: { apiKey: string; record: SecretRecord | null; onClose: () => void }) {
  const [events, setEvents] = useState<AuditRow[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!record) return
    setLoading(true)
    setError(null)
    try {
      const page = await listAuditPage(apiKey, { target_type: 'secret', target_id: record.id }, 100, 0)
      setEvents(page.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load the timeline')
    } finally {
      setLoading(false)
    }
  }, [apiKey, record])

  useEffect(() => { void load() }, [load])

  return (
    <Sheet open={record !== null} onOpenChange={(o) => { if (!o) onClose() }}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{record?.label ?? 'Secret'}</SheetTitle>
          <SheetDescription>Audit timeline: creation, rotations, re-wraps and deletion.</SheetDescription>
        </SheetHeader>
        {record && (
          <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <dt className="text-slate-500">Age</dt><dd><AgeBadge record={record} /></dd>
            <dt className="text-slate-500">Created</dt><dd>{new Date(record.created_at).toLocaleString()}</dd>
            <dt className="text-slate-500">Fingerprint</dt><dd className="font-mono">{record.fingerprint ?? '—'}</dd>
            <dt className="text-slate-500">Rotations</dt><dd>{record.rotation_count}</dd>
          </dl>
        )}
        <AsyncCard
          title="Events"
          loading={loading}
          error={error}
          onRetry={() => void load()}
          empty={!loading && events.length === 0}
          emptyTitle="No audit events yet"
        >
          <ol className="relative space-y-3 border-l border-slate-200 pl-4 dark:border-slate-700">
            {events.map((e) => (
              <li key={e.id} className="text-xs">
                <span className="absolute -left-1.5 mt-1 h-3 w-3 rounded-full border-2 border-white bg-indigo-500 dark:border-slate-900" aria-hidden="true" />
                <p className="font-medium text-slate-900 dark:text-slate-100">{e.action}</p>
                <p className="text-slate-500 dark:text-slate-400">
                  {new Date(e.created_at).toLocaleString()} · {e.actor_label ?? e.actor_type ?? 'system'}
                </p>
                {e.after && 'key_id' in e.after ? (
                  <p className="font-mono text-[11px] text-slate-400">key {String(e.after.key_id)}</p>
                ) : null}
              </li>
            ))}
          </ol>
        </AsyncCard>
        {record && (
          <Link
            href={`${AUDIT_ROUTE}?target_type=secret&target_id=${record.id}`}
            className="mt-3 inline-block text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
          >
            Open in the audit log
          </Link>
        )}
      </SheetContent>
    </Sheet>
  )
}
