'use client'

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import { Activity, RefreshCw } from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'
import { AsyncCard, SectionError } from '@/components/ui/async-card'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import { EmptyState } from '@/components/ui/empty-state'
import { PageHeader } from '@/components/ui/page-header'
import { apiErrorMessage, getSystemStatus } from '@/lib/api'
import type { OpsQueueStatusItem, SystemBackupRun, SystemCheckState, SystemStatus, SystemVersionComponent, SystemWorker } from '@/types/api'

const REFRESH_MS = 30_000

const STATE_CLASS: Record<string, string> = {
  ok: 'bg-status-success/10 text-status-success',
  success: 'bg-status-success/10 text-status-success',
  starting: 'bg-status-info/10 text-status-info',
  unknown: 'bg-status-neutral/10 text-status-neutral',
  behind: 'bg-status-warning/10 text-status-warning',
  stale: 'bg-status-warning/10 text-status-warning',
  degraded: 'bg-status-error/10 text-status-error',
  error: 'bg-status-error/10 text-status-error',
  failed: 'bg-status-error/10 text-status-error',
}

function StateBadge({ state, label }: { state: SystemCheckState | string | null | undefined; label?: string }) {
  const s = state ?? 'unknown'
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATE_CLASS[s] ?? STATE_CLASS.unknown}`}>
      {label ?? s}
    </span>
  )
}

function age(seconds: number | null | undefined): string {
  if (seconds == null) return '—'
  if (seconds < 90) return `${Math.round(seconds)} s ago`
  if (seconds < 5400) return `${Math.round(seconds / 60)} min ago`
  return `${Math.round(seconds / 3600)} h ago`
}

function duration(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return d ? `${d}d ${h}h` : h ? `${h}h ${m}m` : `${m}m`
}

function bytes(n: number | null): string {
  if (n == null) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let v = n
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v.toFixed(i ? 1 : 0)} ${units[i]}`
}

const shortSha = (sha: string | null | undefined) => (sha ? sha.slice(0, 12) : '—')

const versionColumns: DataTableColumn<SystemVersionComponent>[] = [
  { key: 'component', header: 'Component', sortable: true },
  { key: 'version', header: 'Version', sortable: true },
  { key: 'build_sha', header: 'Build', render: (r) => <code className="text-xs">{shortSha(r.build_sha)}</code>, value: (r) => r.build_sha },
  { key: 'status', header: 'Status', render: (r) => <StateBadge state={r.status} /> },
]

const workerColumns: DataTableColumn<SystemWorker>[] = [
  { key: 'worker', header: 'Worker', sortable: true },
  { key: 'queues', header: 'Queues', render: (r) => r.queues.join(', '), value: (r) => r.queues.join(' ') },
  { key: 'version', header: 'Version', sortable: true },
  { key: 'build_sha', header: 'Build', render: (r) => <code className="text-xs">{shortSha(r.build_sha)}</code>, value: (r) => r.build_sha },
  { key: 'age_seconds', header: 'Last heartbeat', sortable: true, render: (r) => age(r.age_seconds), value: (r) => r.age_seconds },
  { key: 'status', header: 'Status', render: (r) => <StateBadge state={r.status} /> },
  { key: 'pid', header: 'PID', defaultHidden: true },
]

const queueColumns: DataTableColumn<OpsQueueStatusItem>[] = [
  { key: 'queue', header: 'Queue', sortable: true },
  { key: 'depth', header: 'Waiting tasks', sortable: true },
  { key: 'status', header: 'State', render: (r) => <StateBadge state={r.status === 'busy' ? 'stale' : 'ok'} label={r.status} /> },
  { key: 'description', header: 'Handles' },
]

const backupColumns: DataTableColumn<SystemBackupRun>[] = [
  { key: 'created_at', header: 'Started', sortable: true, render: (r) => (r.created_at ? new Date(r.created_at).toLocaleString() : '—') },
  { key: 'scope', header: 'Kind' },
  { key: 'trigger_mode', header: 'Trigger' },
  { key: 'status', header: 'Status', render: (r) => <StateBadge state={r.status} /> },
  { key: 'size_bytes', header: 'Size', render: (r) => bytes(r.size_bytes), value: (r) => r.size_bytes },
  { key: 'target', header: 'Target', defaultHidden: true },
  { key: 'error', header: 'Error', render: (r) => (r.error ? <span className="text-status-error">{r.error}</span> : '—') },
]

/**
 * System status (platform admins): is every moving part of this deployment alive, on
 * the same build, and keeping up? Workers and beat report through heartbeats, queues by
 * depth, migrations against this build's head, and backups by their latest runs.
 */
export default function SystemStatusPage() {
  const { data: session } = useSession()
  const { isPlatformAdmin } = useRole()
  const apiKey = session?.apiKey ?? ''
  const [data, setData] = useState<SystemStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!apiKey) return
    try {
      setData(await getSystemStatus(apiKey))
      setError(null)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not load system status'))
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => {
    if (!isPlatformAdmin) return
    void load()
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') void load()
    }, REFRESH_MS)
    return () => clearInterval(timer)
  }, [load, isPlatformAdmin])

  if (!isPlatformAdmin) {
    return (
      <div className="space-y-4">
        <PageHeader title="System status" icon={Activity} />
        <EmptyState title="Platform admins only" description="System status shows the whole deployment, so only platform admins can open it." />
      </div>
    )
  }

  const health = data?.health

  return (
    <div className="space-y-4">
      <PageHeader
        title="System status"
        icon={Activity}
        description="Workers, queues, beat, migrations, backups and the build each component runs. Refreshes every 30 seconds."
        breadcrumbs={[{ label: 'Platform' }, { label: 'System status' }]}
        actions={
          <button
            type="button"
            onClick={() => void load()}
            aria-label="Refresh system status"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" /> Refresh
          </button>
        }
      />

      {error && !data && <SectionError message={error} onRetry={() => void load()} />}

      <AsyncCard title="Health" description="What GET /health reports to load balancers (503 when degraded)." loading={loading && !data} error={data ? null : error} onRetry={() => void load()}>
        {health && data && (
          <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3 lg:grid-cols-6">
            {(
              [
                ['Overall', health.status],
                ['Database', health.db],
                ['Redis', health.redis],
                ['Migrations', health.migrations],
                ['Celery beat', health.beat],
              ] as const
            ).map(([label, state]) => (
              <div key={label} className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700">
                <div className="text-xs text-slate-500 dark:text-slate-400">{label}</div>
                <div className="mt-1"><StateBadge state={state} /></div>
              </div>
            ))}
            <div className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700">
              <div className="text-xs text-slate-500 dark:text-slate-400">API uptime</div>
              <div className="mt-1 font-semibold text-slate-900 dark:text-slate-100">{duration(data.uptime_seconds)}</div>
            </div>
          </div>
        )}
      </AsyncCard>

      {data && data.config_warnings.length > 0 && (
        <section role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
          <h2 className="font-semibold">Production configuration warnings</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {data.config_warnings.map((w) => <li key={w}>{w}</li>)}
          </ul>
          <p className="mt-2 text-xs">See docs/deployment/configuration.md. The API refuses to start with these unless ALLOW_INSECURE_DEFAULTS is set.</p>
        </section>
      )}

      <AsyncCard
        title="Versions"
        description={
          data?.versions.skew
            ? 'Version skew: components run different builds. Redeploy api, workers and beat from one image tag.'
            : 'Every running component reports the same build.'
        }
        loading={loading && !data}
        error={data ? null : error}
        actions={data && <StateBadge state={data.versions.skew ? 'stale' : 'ok'} label={data.versions.skew ? 'skew' : 'in sync'} />}
      >
        {data && (
          <>
            <DataTable label="Component versions" rows={data.versions.components} columns={versionColumns} rowKey={(r) => r.component} urlPrefix="v_" searchable={false} pageSize={20} />
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Database schema: <StateBadge state={data.migrations.status} /> current {data.migrations.current?.join(', ') || '—'} · this build&apos;s head {data.migrations.head?.join(', ') || '—'}
            </p>
          </>
        )}
      </AsyncCard>

      <AsyncCard
        title="Workers"
        description={`Celery workers seen in the last 5 minutes. Beat: last heartbeat ${age(data?.beat.age_seconds)}.`}
        loading={loading && !data}
        error={data ? null : error}
        empty={!!data && data.workers.length === 0}
        emptyTitle="No worker heartbeats"
        emptyDescription="No worker has run a heartbeat yet. Check that runledger-worker, runledger-worker-ingest and runledger-beat are running."
      >
        {data && <DataTable label="Celery workers" rows={data.workers} columns={workerColumns} rowKey={(r) => r.worker} urlPrefix="w_" csvFileName="workers.csv" />}
      </AsyncCard>

      <AsyncCard title="Queues" description="Tasks waiting in each Celery queue." loading={loading && !data} error={data ? null : error} empty={!!data && data.queues.length === 0}>
        {data && <DataTable label="Celery queues" rows={data.queues} columns={queueColumns} rowKey={(r) => r.queue} urlPrefix="q_" searchable={false} />}
      </AsyncCard>

      <AsyncCard
        title="Backups"
        description={
          data?.backups?.enabled
            ? `Last successful backup: ${data.backups.last_success?.completed_at ? new Date(data.backups.last_success.completed_at).toLocaleString() : 'none yet'}.`
            : 'Backups are disabled for this deployment (BACKUP_ENABLED=false).'
        }
        loading={loading && !data}
        error={data ? null : error}
        empty={!!data && (data.backups?.recent.length ?? 0) === 0}
        emptyTitle="No backup runs yet"
        emptyDescription="Configure a target and run a backup from Settings → Backups."
        actions={
          <Link href="/settings" className="text-xs font-medium text-blue-700 hover:underline dark:text-blue-400">
            Backup settings
          </Link>
        }
      >
        {data?.backups && <DataTable label="Recent backup runs" rows={data.backups.recent} columns={backupColumns} rowKey={(r) => r.id} urlPrefix="b_" searchable={false} csvFileName="backups.csv" />}
      </AsyncCard>
    </div>
  )
}
