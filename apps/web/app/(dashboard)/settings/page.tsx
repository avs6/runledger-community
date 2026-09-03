'use client'

import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { useTheme } from 'next-themes'
import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { DatabaseBackup, Lock, Mail, Server, Trash2 } from 'lucide-react'
import type {
  BudgetControlPlatformPosture,
  LedgerCrossFeaturePosture,
  LedgerClosureSummary,
  LedgerSnapshotResponse,
  LedgerVerifyResult,
  PlatformWebhookDefaults,
  PlatformWebhookDefaultsTestResult,
  PlatformSettingsConvergencePosture,
} from '@/types/api'
import {
  getBudgetControlPlatformPosture,
  getLedgerCrossFeaturePosture,
  getLedgerClosureSummary,
  listLedgerSnapshots,
  generateLedgerSnapshot,
  verifyLedgerSnapshot,
  getPlatformSettingsConvergencePosture,
} from '@/lib/api'
import { useRole } from '@/components/rbac/useRole'
import RetentionTab from '@/components/settings/RetentionTab'
import type {
  BackupRun,
  BackupSnapshot,
  BackupTargetConfig,
  OpsFeatureFlagsResponse,
  OpsFeatureStatus,
  OpsPolicyEvaluation,
  OpsQueueStatusItem,
  OpsStorageStatus,
} from '@/types/api'
import {
  getBackupConfig,
  getBackupHistory,
  getBackupSnapshots,
  getOpsFeatureStatus,
  runBackupNow,
  runRestoreDrill,
  testBackupConnection,
  updateBackupConfig,
  getBackupStatus,
  getOpsFeatureFlags,
  getOpsPolicyEvaluation,
  getOpsQueueStatus,
  getOpsStorageStatus,
  getPlatformWebhookDefaults,
  testPlatformWebhookDefaults,
  updatePlatformWebhookDefaults,
} from '@/lib/api'

const inputCls =
  'rounded border border-stone-300 dark:border-stone-700 bg-[#fbfaf7] dark:bg-[#16181F] text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-stone-500 dark:focus:ring-[#D8CAAA]'

const TABS = [
  { id: 'compliance', label: 'Compliance', description: 'Signed ledgers and audit evidence', icon: Lock },
  { id: 'retention', label: 'Data Retention', description: 'Delete or scrub old records safely', icon: Trash2 },
  { id: 'delivery', label: 'Email & SMTP', description: 'Platform transport and delivery posture', icon: Mail },
  { id: 'storage', label: 'Storage Defaults', description: 'Platform buckets, lifecycle, and compliance exports', icon: Server },
  { id: 'backup', label: 'Backup & Restore', description: 'Recovery workflows and operator drills', icon: DatabaseBackup },
] as const

const PLATFORM_WEBHOOK_EVENT_OPTIONS = [
  'budget.breach',
  'runaway.detected',
  'backup.failed',
  'backup.completed',
  'platform.webhook.test',
] as const

function makeDefaultBackupConfig(): BackupTargetConfig {
  const now = new Date().toISOString()
  return {
    id: 'draft',
    workspace_id: 'draft',
    provider: 's3',
    bucket: '',
    prefix: 'runledger',
    region: 'us-east-1',
    endpoint_url: 'http://localhost:9010',
    access_key_id: 'runledger',
    secret_access_key: 'runledgerminio',
    force_path_style: true,
    schedule_enabled: true,
    cadence: 'daily',
    run_hour_utc: 2,
    retention_days: 30,
    include_memory_db: true,
    include_qdrant: false,
    include_kuzu: true,
    include_skills: true,
    encryption_mode: 'server_side',
    last_verified_at: null,
    created_at: now,
    updated_at: now,
  }
}

export default function SettingsPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { theme, setTheme } = useTheme()
  const searchParams = useSearchParams()
  const router = useRouter()
  const { canManagePlatformSettings } = useRole()

  const activeTab = searchParams.get('tab') || 'compliance'
  const setTab = (tab: string) => router.push(`/settings?tab=${tab}`)

  // ── Compliance (Ledger) ────────────────────────────────────────────────────────
  const [snapshots, setSnapshots] = useState<LedgerSnapshotResponse[]>([])
  const [verifyResults, setVerifyResults] = useState<Record<string, LedgerVerifyResult>>({})
  const [closureSummary, setClosureSummary] = useState<LedgerClosureSummary | null>(null)
  const [generatingSnap, setGeneratingSnap] = useState(false)
  const [verifyingSnap, setVerifyingSnap] = useState<string | null>(null)
  const [loadingCompliance, setLoadingCompliance] = useState(false)
  const [complianceAttempted, setComplianceAttempted] = useState(false)

  // ── Operations Status ─────────────────────────────────────────────────────────
  const [opsStatus, setOpsStatus] = useState<OpsFeatureStatus | null>(null)
  const [opsStatusAttempted, setOpsStatusAttempted] = useState(false)
  const [backupRuns, setBackupRuns] = useState<BackupRun[]>([])
  const [backupConfig, setBackupConfig] = useState<BackupTargetConfig>(makeDefaultBackupConfig())
  const [backupSnapshots, setBackupSnapshots] = useState<BackupSnapshot[]>([])
  const [backupStatus, setBackupStatus] = useState<{ ok: boolean; message: string; details: Record<string, unknown> | null } | null>(null)
  const [opsQueues, setOpsQueues] = useState<OpsQueueStatusItem[]>([])
  const [opsQueueSummary, setOpsQueueSummary] = useState<{ total_depth: number; busy_queues: number } | null>(null)
  const [opsStorage, setOpsStorage] = useState<OpsStorageStatus | null>(null)
  const [opsFeatureFlags, setOpsFeatureFlags] = useState<OpsFeatureFlagsResponse | null>(null)
  const [opsPolicy, setOpsPolicy] = useState<OpsPolicyEvaluation | null>(null)
  const [platformWebhookDefaults, setPlatformWebhookDefaults] = useState<PlatformWebhookDefaults | null>(null)
  const [platformWebhookTestResult, setPlatformWebhookTestResult] = useState<PlatformWebhookDefaultsTestResult | null>(null)
  const [savingPlatformWebhooks, setSavingPlatformWebhooks] = useState(false)
  const [loadingBackup, setLoadingBackup] = useState(false)
  const [backupAttempted, setBackupAttempted] = useState(false)
  const [runningBackup, setRunningBackup] = useState(false)
  const [testingBackupConnectionState, setTestingBackupConnectionState] = useState(false)
  const [runningRestoreDrillState, setRunningRestoreDrillState] = useState(false)
  const [savingBackupConfig, setSavingBackupConfig] = useState(false)
  const [testingPlatformWebhooks, setTestingPlatformWebhooks] = useState(false)
  const [budgetPlatformPosture, setBudgetPlatformPosture] = useState<BudgetControlPlatformPosture | null>(null)
  const [ledgerCrossPosture, setLedgerCrossPosture] = useState<LedgerCrossFeaturePosture | null>(null)
  const [convergencePosture, setConvergencePosture] = useState<PlatformSettingsConvergencePosture | null>(null)



  const loadCompliance = useCallback(async () => {
    if (!apiKey || !canManagePlatformSettings) return
    setComplianceAttempted(true)
    setLoadingCompliance(true)
    try {
      const [snapList, summary] = await Promise.all([
        listLedgerSnapshots(apiKey),
        getLedgerClosureSummary(apiKey),
      ])
      setSnapshots(snapList.items)
      setClosureSummary(summary)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load compliance data')
    } finally {
      setLoadingCompliance(false)
    }
  }, [apiKey, canManagePlatformSettings])

  useEffect(() => {
    if (activeTab === 'compliance' && !complianceAttempted) loadCompliance()
  }, [activeTab, complianceAttempted, loadCompliance])

  const loadOpsStatus = useCallback(async () => {
    if (!apiKey || !canManagePlatformSettings) return
    setOpsStatusAttempted(true)
    try {
      const [status, defaults] = await Promise.all([
        getOpsFeatureStatus(apiKey),
        getPlatformWebhookDefaults(apiKey),
      ])
      setOpsStatus(status)
      setPlatformWebhookDefaults(defaults)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load operational feature status')
    }
  }, [apiKey, canManagePlatformSettings])



  useEffect(() => {
    if ((activeTab === 'backup' || activeTab === 'delivery' || activeTab === 'storage') && !opsStatusAttempted) loadOpsStatus()
  }, [activeTab, opsStatusAttempted, loadOpsStatus])

  const loadBackupData = useCallback(async () => {
    if (!apiKey || !canManagePlatformSettings) return
    setBackupAttempted(true)
    setLoadingBackup(true)
    try {
      const [status, history, config, snapshotList, backupHealth, queueStatus, storageStatus, featureFlags, policyEval] = await Promise.all([
        getOpsFeatureStatus(apiKey),
        getBackupHistory(apiKey, 20),
        getBackupConfig(apiKey),
        getBackupSnapshots(apiKey, 20),
        getBackupStatus(apiKey),
        getOpsQueueStatus(apiKey),
        getOpsStorageStatus(apiKey),
        getOpsFeatureFlags(apiKey),
        getOpsPolicyEvaluation(apiKey),
      ])
      setOpsStatus(status)
      setBackupRuns(history.items)
      setBackupConfig(config ?? makeDefaultBackupConfig())
      setBackupSnapshots(snapshotList.items)
      setBackupStatus(backupHealth)
      setOpsQueues(queueStatus.items)
      setOpsQueueSummary({ total_depth: queueStatus.total_depth, busy_queues: queueStatus.busy_queues })
      setOpsStorage(storageStatus)
      setOpsFeatureFlags(featureFlags)
      setOpsPolicy(policyEval)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load backup history')
    } finally {
      setLoadingBackup(false)
    }
  }, [apiKey, canManagePlatformSettings])

  useEffect(() => {
    if ((activeTab === 'backup' || activeTab === 'storage') && !backupAttempted) void loadBackupData()
  }, [activeTab, backupAttempted, loadBackupData])

  useEffect(() => {
    if (apiKey) {
      getBudgetControlPlatformPosture(apiKey).then(setBudgetPlatformPosture).catch(() => {})
      getLedgerCrossFeaturePosture(apiKey).then(setLedgerCrossPosture).catch(() => {})
      getPlatformSettingsConvergencePosture(apiKey).then(setConvergencePosture).catch(() => {})
    }
  }, [apiKey])

  const backupSchedulerDisabled = opsStatus ? !opsStatus.backup_enabled : true

  // ── Compliance handlers ─────────────────────────────────────────────────────

  async function handleGenerateSnapshot() {
    if (!apiKey) return
    setGeneratingSnap(true)
    try {
      const snap = await generateLedgerSnapshot(apiKey)
      setSnapshots((prev) => [snap, ...prev.filter((s) => s.snapshot_date !== snap.snapshot_date)])
      const summary = await getLedgerClosureSummary(apiKey)
      setClosureSummary(summary)
      toast.success('Snapshot generated')
    } catch { toast.error('Failed to generate snapshot') }
    finally { setGeneratingSnap(false) }
  }

  async function handleVerifySnapshot(snap: LedgerSnapshotResponse) {
    if (!apiKey) return
    setVerifyingSnap(snap.snapshot_date)
    try {
      const result = await verifyLedgerSnapshot(apiKey, snap.snapshot_date)
      setVerifyResults((prev) => ({ ...prev, [snap.snapshot_date]: result }))
      const summary = await getLedgerClosureSummary(apiKey)
      setClosureSummary(summary)
      if (result.match) toast.success('Snapshot integrity verified')
      else toast.error(`Integrity check failed: ${result.status}`)
    } catch { toast.error('Failed to verify snapshot') }
    finally { setVerifyingSnap(null) }
  }

  if (!canManagePlatformSettings) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Settings</h1>
        <p className="mt-4 text-sm text-slate-500">Settings access is limited to platform admins.</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 lg:p-8">
      <div className="flex flex-col gap-4 rounded-2xl border border-stone-200 bg-[#fbfaf7]/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950/55 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-700 dark:text-[#D8CAAA]">
            Platform Console
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">
            Platform Settings
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
            High-impact controls for compliance, retention, messaging, and recovery. These are intentionally platform-admin only.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-stone-200 bg-stone-50 px-3 py-2 dark:border-slate-800 dark:bg-slate-900">
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Theme</span>
          <select
            value={theme ?? 'system'}
            onChange={(e) => setTheme(e.target.value)}
            className="rounded-lg border border-stone-200 bg-[#fbfaf7] px-2 py-1.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-stone-500 dark:border-stone-700 dark:bg-[#16181F] dark:text-slate-100"
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">System</option>
          </select>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {TABS.map(({ id, label, description, icon: Icon }) => {
          const selected = activeTab === id
          return (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`group rounded-2xl border p-4 text-left transition-all ${
                selected
                  ? 'border-stone-300 bg-stone-100 text-slate-950 shadow-sm ring-1 ring-stone-400/20 dark:border-stone-500/40 dark:bg-stone-700/30 dark:text-white'
                  : 'border-stone-200 bg-[#fbfaf7]/70 text-slate-700 hover:border-stone-300 hover:bg-[#fffdf8] dark:border-slate-800 dark:bg-slate-950/45 dark:text-slate-300 dark:hover:border-slate-700 dark:hover:bg-slate-900'
              }`}
            >
              <div className="flex items-start gap-3">
                <span className={`rounded-xl p-2 ${
                  selected
                    ? 'bg-stone-700 text-white dark:bg-[#D8CAAA] dark:text-[#111318]'
                    : 'bg-slate-100 text-slate-500 group-hover:text-slate-700 dark:bg-slate-900 dark:text-slate-400 dark:group-hover:text-slate-200'
                }`}>
                  <Icon className="h-4 w-4" />
                </span>
                <span>
                  <span className="block text-sm font-semibold">{label}</span>
                  <span className="mt-1 block text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                    {description}
                  </span>
                </span>
              </div>
            </button>
          )
        })}
      </div>

      {budgetPlatformPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Budget Control — Platform Posture</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Total Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetPlatformPosture.platform_totals.total_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Total Limit</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">${budgetPlatformPosture.platform_totals.total_limit_usd.toFixed(2)}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Overrides</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetPlatformPosture.override_context.active_overrides}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Breached</p>
              <p className={`mt-1 text-lg font-semibold ${budgetPlatformPosture.platform_totals.total_breaches > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{budgetPlatformPosture.platform_totals.total_breaches}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
            <Link href="/budgets" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
            <Link href="/budgets?scope=feature_tag" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Feature Budgets</Link>
            <Link href="/organizations" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">All Organizations</Link>
            <Link href="/analytics?tab=economics" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Economics</Link>
          </div>
        </div>
      )}

      {ledgerCrossPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">Ledger × Cross-Feature Context</h2>
            <span className="text-xs text-emerald-600 dark:text-emerald-400">{ledgerCrossPosture.period_days}d window</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Org Scope</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{ledgerCrossPosture.org_context.workspace_users} users</p>
              <p className="text-xs text-slate-400">{ledgerCrossPosture.org_context.workspaces} workspaces · {ledgerCrossPosture.org_context.access_groups} groups</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Observe</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{ledgerCrossPosture.observe_context.billing_periods} periods</p>
              <p className="text-xs text-slate-400">${ledgerCrossPosture.observe_context.total_spend_30d.toFixed(2)} 30d spend</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Safety</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{ledgerCrossPosture.safety_context.audit_events_30d} audit events</p>
              <p className="text-xs text-slate-400">{ledgerCrossPosture.safety_context.tags} tags</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Platform</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{ledgerCrossPosture.platform_context.total_organizations} orgs</p>
              <p className="text-xs text-slate-400">{ledgerCrossPosture.observe_context.distinct_models_30d} models</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500">Ledger</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{ledgerCrossPosture.ledger_context.total_snapshots} snapshots</p>
              <p className="text-xs text-slate-400">latest: {ledgerCrossPosture.ledger_context.latest_snapshot_date}</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Link href="/organizations" className="text-emerald-600 hover:underline dark:text-emerald-400">Organization →</Link>
            <Link href="/analytics?tab=economics" className="text-emerald-600 hover:underline dark:text-emerald-400">Economics →</Link>
            <Link href="/billing" className="text-emerald-600 hover:underline dark:text-emerald-400">Billing →</Link>
            <Link href="/audit" className="text-emerald-600 hover:underline dark:text-emerald-400">Audit Log →</Link>
            <Link href="/tags" className="text-emerald-600 hover:underline dark:text-emerald-400">Tags →</Link>
          </div>
        </div>
      )}

      {convergencePosture && (
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-cyan-200 bg-cyan-50/50 p-5 shadow-sm dark:border-cyan-900 dark:bg-cyan-950/30">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">Telemetry & Capture Convergence</p>
              <span className="text-xs text-cyan-600 dark:text-cyan-400">{convergencePosture.period_days}d</span>
            </div>
            <div className="grid gap-3 grid-cols-3">
              <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">OTLP Batches</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{convergencePosture.telemetry_context.otlp_batches_7d}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Spans Ingested</p>
                <p className="mt-1 text-lg font-semibold text-cyan-600 dark:text-cyan-400">{convergencePosture.telemetry_context.otlp_spans_7d}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Capture Policies</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{convergencePosture.telemetry_context.capture_policies}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-cyan-200 dark:border-cyan-800">
              <Link href="/telemetry" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Telemetry →</Link>
              <Link href="/retention" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Retention →</Link>
              <Link href="/monitoring" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Monitoring →</Link>
              <Link href="/organizations" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Organizations →</Link>
            </div>
          </div>
          <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm dark:border-amber-900 dark:bg-amber-950/30">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">Audit & Compliance Convergence</p>
              <span className="text-xs text-amber-600 dark:text-amber-400">{convergencePosture.period_days}d</span>
            </div>
            <div className="grid gap-3 grid-cols-2">
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Audit Events</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{convergencePosture.audit_context.audit_events_7d}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Security Events</p>
                <p className="mt-1 text-lg font-semibold text-amber-600 dark:text-amber-400">{convergencePosture.audit_context.security_events_7d}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Ledger Snapshots</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{convergencePosture.compliance_context.ledger_snapshots}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Ledger Closures</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{convergencePosture.compliance_context.ledger_closures}</p>
              </div>
            </div>
            <div className="mt-3 grid gap-3 grid-cols-2">
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Alert Rules</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{convergencePosture.ops_context.alert_rules}</p>
              </div>
              <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">Alert Firings</p>
                <p className={`mt-1 text-lg font-semibold ${convergencePosture.ops_context.alert_firings_7d > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{convergencePosture.ops_context.alert_firings_7d}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-amber-200 dark:border-amber-800">
              <Link href="/audit" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Audit Log →</Link>
              <Link href="/alerts" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Alerts →</Link>
              <Link href="/governance" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Governance →</Link>
              <Link href="/evaluation" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Evaluation Studio →</Link>
              <Link href="/organizations" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Organizations →</Link>
            </div>
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-stone-200 bg-[#fbfaf7]/80 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950/40">

        {/* ── Compliance ────────────────────────────────────────────────────────── */}
        {activeTab === 'compliance' && (
          <div className="space-y-8">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-semibold dark:text-white">Compliance</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  Closure workspace for ledger verification, period-close posture, chargeback evidence, backups, and audit linkage.
                </p>
              </div>
              <button
                onClick={() => { setComplianceAttempted(false) }}
                disabled={loadingCompliance}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
              >
                <svg className={`h-4 w-4 ${loadingCompliance ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                {loadingCompliance ? 'Loading…' : 'Refresh'}
              </button>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/40">
                <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Closure readiness</div>
                <div className="mt-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
                  {closureSummary?.readiness_status ?? 'Unknown'}
                </div>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Evidence score {closureSummary?.evidence_score ?? 0}/5 as of {closureSummary ? new Date(closureSummary.generated_at).toLocaleString() : 'now'}.
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/40">
                <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Latest closed period</div>
                <div className="mt-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
                  {closureSummary?.latest_closed_period ? `${closureSummary.latest_closed_period.period_start} → ${closureSummary.latest_closed_period.period_end}` : 'Missing'}
                </div>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Net cost {closureSummary?.latest_closed_period?.net_cost_usd ? `$${Number.parseFloat(closureSummary.latest_closed_period.net_cost_usd).toFixed(2)}` : '—'}
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/40">
                <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Ledger verification</div>
                <div className="mt-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
                  {closureSummary?.verification.latest_status ?? 'Pending'}
                </div>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  {closureSummary?.verification.ok_count ?? 0} ok · {closureSummary?.verification.tampered_count ?? 0} tampered · {closureSummary?.verification.pending_count ?? 0} pending
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/40">
                <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Chargeback evidence</div>
                <div className="mt-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
                  {closureSummary?.chargeback ? `$${Number.parseFloat(closureSummary.chargeback.total_cost_usd).toFixed(2)}` : 'Missing'}
                </div>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Unallocated {closureSummary?.chargeback ? `$${Number.parseFloat(closureSummary.chargeback.unallocated_cost_usd).toFixed(2)}` : '—'}
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/40">
                <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Audit activity</div>
                <div className="mt-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
                  {(closureSummary?.recent_audit_event_count ?? 0).toLocaleString()}
                </div>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Audit events in the last 30 days.
                </p>
              </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
              <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950/40">
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">Evidence chain</h3>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  Compliance closure should link Billing period close, Chargeback ownership, Ledger verification, backup evidence, and audit history as one operator story.
                </p>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {[
                    ['Billing close', Boolean(closureSummary?.latest_closed_period), '/billing'],
                    ['Chargeback allocation', Boolean(closureSummary?.chargeback), '/chargeback'],
                    ['Ledger snapshot', Boolean(closureSummary?.latest_snapshot), '/settings?tab=compliance'],
                    ['Verified backup', Boolean(closureSummary?.latest_backup_snapshot), '/settings?tab=backup'],
                    ['Audit trail', (closureSummary?.recent_audit_event_count ?? 0) > 0, '/audit'],
                  ].map(([label, ok, href]) => (
                    <a
                      key={String(label)}
                      href={String(href)}
                      className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm transition hover:border-stone-300 hover:bg-[#fffdf8] dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700 dark:hover:bg-slate-800"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-medium text-slate-900 dark:text-slate-100">{label}</span>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                          ok
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-200'
                            : 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200'
                        }`}>
                          {ok ? 'Present' : 'Missing'}
                        </span>
                      </div>
                    </a>
                  ))}
                </div>
                {closureSummary && closureSummary.missing_evidence.length > 0 && (
                  <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
                    <div className="font-semibold">Missing evidence</div>
                    <p className="mt-1">
                      {closureSummary.missing_evidence.join(', ')}
                    </p>
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950/40">
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">Latest evidence anchors</h3>
                <div className="mt-4 space-y-4 text-sm">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Latest snapshot</div>
                    <div className="mt-1 text-slate-900 dark:text-slate-100">
                      {closureSummary?.latest_snapshot ? closureSummary.latest_snapshot.snapshot_date : 'No snapshot yet'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Latest backup evidence</div>
                    <div className="mt-1 text-slate-900 dark:text-slate-100">
                      {closureSummary?.latest_backup_snapshot ? `${closureSummary.latest_backup_snapshot.bucket} · ${closureSummary.latest_backup_snapshot.integrity_status}` : 'No backup snapshot yet'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Chargeback scope</div>
                    <div className="mt-1 text-slate-900 dark:text-slate-100">
                      {closureSummary?.chargeback ? `${closureSummary.chargeback.period} · ${closureSummary.chargeback.dimension}` : 'No chargeback summary yet'}
                    </div>
                  </div>
                  <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-100">
                    Compliance lives here under Platform Settings. `/ledger` remains a compatibility route only.
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-medium dark:text-gray-100">Ledger snapshots</h3>
                <button
                  onClick={handleGenerateSnapshot}
                  disabled={generatingSnap}
                  className="rounded bg-stone-700 px-3 py-1.5 text-sm text-white hover:bg-stone-600 disabled:opacity-50 dark:bg-[#D8CAAA] dark:text-[#111318] dark:hover:bg-[#E8DDC9]"
                >
                  {generatingSnap ? 'Generating…' : 'Generate Snapshot'}
                </button>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Each snapshot is an HMAC-SHA256 signed record of daily spend. Use Verify to confirm integrity and preserve the final close chain.
              </p>
              <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase text-gray-500 dark:text-gray-400">
                    <tr>
                      <th className="px-4 py-2 text-left">Date</th>
                      <th className="px-4 py-2 text-right">Total Cost</th>
                      <th className="px-4 py-2 text-right">Calls</th>
                      <th className="px-4 py-2 text-left">Hash</th>
                      <th className="px-4 py-2 text-left">Integrity</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {loadingCompliance ? (
                      [1,2,3].map((i) => (
                        <tr key={i}>
                          {[1,2,3,4,5].map((j) => (
                            <td key={j} className="px-4 py-3">
                              <div className="h-4 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
                            </td>
                          ))}
                        </tr>
                      ))
                    ) : snapshots.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-4 py-6 text-center text-gray-400 dark:text-gray-500">
                          No snapshots yet. Click &ldquo;Generate Snapshot&rdquo; to create one.
                        </td>
                      </tr>
                    ) : snapshots.map((snap) => {
                      const vr = verifyResults[snap.snapshot_date]
                      return (
                        <tr key={snap.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                          <td className="px-4 py-2 font-mono dark:text-gray-200">{snap.snapshot_date}</td>
                          <td className="px-4 py-2 text-right font-mono dark:text-gray-200">${parseFloat(snap.total_cost_usd).toFixed(6)}</td>
                          <td className="px-4 py-2 text-right dark:text-gray-200">{snap.call_count}</td>
                          <td className="px-4 py-2 font-mono text-xs text-gray-500 dark:text-gray-400">{snap.hash.slice(0, 12)}…</td>
                          <td className="px-4 py-2">
                            {vr ? (
                              vr.match
                                ? <span className="rounded bg-green-100 dark:bg-green-900 px-2 py-0.5 text-xs text-green-700 dark:text-green-300">✓ ok</span>
                                : <span className="rounded bg-red-100 dark:bg-red-900 px-2 py-0.5 text-xs text-red-700 dark:text-red-300">⚠ {vr.status}</span>
                            ) : (
                              <button
                                onClick={() => handleVerifySnapshot(snap)}
                                disabled={verifyingSnap === snap.snapshot_date}
                                className="text-xs font-medium text-stone-700 hover:underline disabled:opacity-50 dark:text-[#D8CAAA]"
                              >
                                {verifyingSnap === snap.snapshot_date ? 'Verifying…' : 'Verify'}
                              </button>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <a href="/billing" className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4 text-sm text-slate-600 dark:text-slate-300 hover:border-stone-300 hover:bg-[#fffdf8] dark:hover:border-slate-600 dark:hover:bg-slate-800">
                <p className="font-medium">Billing period detail</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Review the closed accounting period that should feed ledger closure.
                </p>
              </a>
              <a href="/chargeback" className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4 text-sm text-slate-600 dark:text-slate-300 hover:border-stone-300 hover:bg-[#fffdf8] dark:hover:border-slate-600 dark:hover:bg-slate-800">
                <p className="font-medium">Chargeback allocation</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Confirm ownership allocation before treating the close package as complete.
                </p>
              </a>
              <a href="/audit" className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4 text-sm text-slate-600 dark:text-slate-300 hover:border-stone-300 hover:bg-[#fffdf8] dark:hover:border-slate-600 dark:hover:bg-slate-800">
                <p className="font-medium">Audit log and governance evidence</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Use Audit Log and Tool Registry as the downstream evidence companions to ledger verification.
                </p>
              </a>
            </div>
          </div>
        )}

        {/* ── Data Retention (Admin only) ───────────────────────────────────────── */}
        {activeTab === 'retention' && (
          <RetentionTab apiKey={apiKey ?? ''} />
        )}

        {activeTab === 'delivery' && (
          <div className="space-y-6">
            <div className="rounded-lg border border-stone-200 bg-[#fbfaf7] p-6 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-start gap-3">
                <div className="rounded-xl bg-stone-100 p-2 text-stone-700 dark:bg-stone-700/35 dark:text-[#D8CAAA]">
                  <Mail className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">Platform Email Transport</h3>
                  <p className="mt-1 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
                    SMTP belongs to Platform Settings because it is shared delivery infrastructure. Organization Console owns notification preferences and smoke tests, while this surface owns the transport posture they depend on.
                  </p>
                </div>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-3">
                <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/40">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Email delivery</div>
                  <div className="mt-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
                    {opsStatus?.email_enabled ? 'Enabled' : 'Disabled'}
                  </div>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Controlled by `EMAIL_ENABLED`.</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/40">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">SMTP credentials</div>
                  <div className="mt-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
                    {opsStatus?.smtp_configured ? 'Configured' : 'Missing'}
                  </div>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Welcome mail, resets, alerts, and reports all depend on this.</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/40">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Scheduled reports</div>
                  <div className="mt-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
                    {opsStatus?.email_reports_enabled ? 'Enabled' : 'Disabled'}
                  </div>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Controlled by `EMAIL_REPORTS_ENABLED`.</p>
                </div>
              </div>

              <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-100">
                <div className="font-semibold">Ownership split</div>
                <p className="mt-1">
                  Organization admins manage delivery preferences in Organization Console. Platform admins manage whether the transport exists and whether the deployment is allowed to send mail at all.
                </p>
              </div>

              <div className="mt-5 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/40">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Platform Webhook Defaults</h4>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      Optional global fallback destinations for platform-operated notifications and exports. Org-owned webhook destinations live in Organization Console.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={savingPlatformWebhooks || !platformWebhookDefaults}
                      onClick={async () => {
                        if (!apiKey || !platformWebhookDefaults) return
                        setSavingPlatformWebhooks(true)
                        try {
                          const updated = await updatePlatformWebhookDefaults(apiKey, {
                            generic_webhook_url: platformWebhookDefaults.generic_webhook_url?.trim() || null,
                            slack_webhook_url: platformWebhookDefaults.slack_webhook_url?.trim() || null,
                            events: platformWebhookDefaults.events,
                          })
                          setPlatformWebhookDefaults(updated)
                          setPlatformWebhookTestResult(null)
                          toast.success('Platform webhook defaults saved')
                        } catch (err) {
                          console.error(err)
                          toast.error('Failed to save platform webhook defaults')
                        } finally {
                          setSavingPlatformWebhooks(false)
                        }
                      }}
                      className="rounded bg-stone-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-stone-600 disabled:opacity-50 dark:bg-[#D8CAAA] dark:text-[#111318]"
                    >
                      {savingPlatformWebhooks ? 'Saving...' : 'Save defaults'}
                    </button>
                    <button
                      type="button"
                      disabled={testingPlatformWebhooks || !(platformWebhookDefaults?.generic_webhook_url || platformWebhookDefaults?.slack_webhook_url)}
                      onClick={async () => {
                        if (!apiKey) return
                        setTestingPlatformWebhooks(true)
                        try {
                          const result = await testPlatformWebhookDefaults(apiKey)
                          setPlatformWebhookTestResult(result)
                          result.ok ? toast.success('Platform webhook defaults tested') : toast.error(result.message)
                        } catch (err) {
                          console.error(err)
                          toast.error('Failed to test platform webhook defaults')
                        } finally {
                          setTestingPlatformWebhooks(false)
                        }
                      }}
                      className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300"
                    >
                      {testingPlatformWebhooks ? 'Testing...' : 'Test defaults'}
                    </button>
                  </div>
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
                    <label className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Generic webhook</label>
                    <input
                      className={`${inputCls} mt-2 w-full`}
                      placeholder="https://example.com/webhooks/runledger"
                      value={platformWebhookDefaults?.generic_webhook_url ?? ''}
                      onChange={(e) => setPlatformWebhookDefaults((prev) => prev ? { ...prev, generic_webhook_url: e.target.value, generic_webhook_configured: e.target.value.trim().length > 0 } : prev)}
                    />
                    <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                      Used for generic export and alert payloads when an org has not defined its own destination.
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
                    <label className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Slack webhook</label>
                    <input
                      className={`${inputCls} mt-2 w-full`}
                      placeholder="https://hooks.slack.com/services/..."
                      value={platformWebhookDefaults?.slack_webhook_url ?? ''}
                      onChange={(e) => setPlatformWebhookDefaults((prev) => prev ? { ...prev, slack_webhook_url: e.target.value, slack_webhook_configured: e.target.value.trim().length > 0 } : prev)}
                    />
                    <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                      Used for platform-wide operator alerts and Slack-formatted test notifications.
                    </p>
                  </div>
                </div>
                <div className="mt-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Default events</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {PLATFORM_WEBHOOK_EVENT_OPTIONS.map((eventType) => {
                      const selected = platformWebhookDefaults?.events.includes(eventType) ?? false
                      return (
                        <button
                          key={eventType}
                          type="button"
                          onClick={() => setPlatformWebhookDefaults((prev) => {
                            if (!prev) return prev
                            const nextEvents = prev.events.includes(eventType)
                              ? prev.events.filter((item) => item !== eventType)
                              : [...prev.events, eventType]
                            return { ...prev, events: nextEvents }
                          })}
                          className={`rounded-full px-2.5 py-1 text-[11px] font-medium transition ${
                            selected
                              ? 'bg-blue-600 text-white dark:bg-blue-400 dark:text-slate-950'
                              : 'bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-500/10 dark:text-blue-200 dark:hover:bg-blue-500/20'
                          }`}
                        >
                          {eventType}
                        </button>
                      )
                    })}
                  </div>
                  <div className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                    Persisted in the database. Environment variables only seed the first row the first time this platform loads defaults.
                  </div>
                </div>
                {platformWebhookTestResult && (
                  <div className={`mt-4 rounded-xl px-4 py-3 text-sm ${platformWebhookTestResult.ok ? 'border border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-100' : 'border border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100'}`}>
                    <div className="font-semibold">{platformWebhookTestResult.message}</div>
                    <div className="mt-2 space-y-1 text-xs">
                      {platformWebhookTestResult.results.map((item) => (
                        <div key={item.channel}>
                          {item.channel}: {item.ok ? 'ok' : item.error}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'storage' && (
          <div className="space-y-6">
            <div className="rounded-lg border border-stone-200 bg-[#fbfaf7] p-6 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-start gap-3">
                <div className="rounded-xl bg-stone-100 p-2 text-stone-700 dark:bg-stone-700/35 dark:text-[#D8CAAA]">
                  <Server className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">Platform Storage Defaults</h3>
                  <p className="mt-1 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
                    This platform surface owns default storage posture and compliance export buckets. Organization Console owns org-specific S3 overrides for backup and export workflows.
                  </p>
                </div>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/40">
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Backup default posture</h4>
                  <div className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                    <div>Bucket: <span className="font-medium text-slate-900 dark:text-slate-100">{opsStorage?.backup.bucket ?? 'Not configured'}</span></div>
                    <div>Lifecycle: <span className="font-medium text-slate-900 dark:text-slate-100">{opsStorage?.backup.lifecycle_enabled ? 'Enabled' : 'Disabled'}</span></div>
                    <div>Retention: <span className="font-medium text-slate-900 dark:text-slate-100">{opsStorage?.backup.retention_days ?? 0} days</span></div>
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/40">
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Compliance exports</h4>
                  <div className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                    <div>Enabled: <span className="font-medium text-slate-900 dark:text-slate-100">{opsStorage?.compliance_exports.enabled ? 'Yes' : 'No'}</span></div>
                    <div>Bucket: <span className="font-medium text-slate-900 dark:text-slate-100">{opsStorage?.compliance_exports.bucket ?? 'Not configured'}</span></div>
                    <div>Prefix: <span className="font-medium text-slate-900 dark:text-slate-100">{opsStorage?.compliance_exports.prefix ?? 'Not configured'}</span></div>
                  </div>
                </div>
              </div>

              <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-100">
                <div className="font-semibold">Where org overrides live</div>
                <p className="mt-1">
                  Org-owned bucket, endpoint, credentials, and schedule overrides now live in Organization Console under Destinations so operators can manage one org at a time without mixing those controls into the platform posture.
                </p>
              </div>
            </div>
          </div>
        )}



        {activeTab === 'backup' && (
          <div className="space-y-6">
            <div className="rounded-lg border border-stone-200 bg-[#fbfaf7] p-6 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-start justify-between gap-3">
                <div className="rounded-xl bg-stone-100 p-2 text-stone-700 dark:bg-stone-700/35 dark:text-[#D8CAAA]">
                  <DatabaseBackup className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">Backup Schedule</h3>
                  <p className="mt-1 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
                    S3 backup and restore are available today through the Helm CronJob and `scripts/restore.sh`.
                    This page is the platform UI for configuring and testing that flow; local product-managed scheduling stays off until `BACKUP_ENABLED=true`.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void loadBackupData()}
                  disabled={loadingBackup}
                  className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300"
                >
                  {loadingBackup ? 'Refreshing...' : 'Refresh'}
                </button>
              </div>

              {opsStatus && (
                <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
                  <div className="font-semibold">
                    {backupSchedulerDisabled ? 'Backup scheduler is disabled.' : 'Backup scheduler is enabled.'}
                  </div>
                  <p className="mt-1">
                    {backupSchedulerDisabled
                      ? 'BACKUP_ENABLED=false, so this local stack will not launch backup jobs from the UI. Helm/script-based S3 backup remains available outside the app.'
                      : 'BACKUP_ENABLED=true. Manual backup runs and history are live. Schedule persistence and S3 test flows can layer on top of this.'}
                  </p>
                </div>
              )}

              {backupStatus && (
                <div className={`mt-4 rounded-xl px-4 py-3 text-sm ${backupStatus.ok ? 'border border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-100' : 'border border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-100'}`}>
                  <div className="font-semibold">{backupStatus.message}</div>
                  {backupStatus.details && (
                    <p className="mt-1 text-xs">
                      Recent failures: {String(backupStatus.details.failed_recent_runs ?? 0)} · Latest status: {String(backupStatus.details.latest_status ?? 'unknown')}
                    </p>
                  )}
                </div>
              )}

              <div className="mt-4 rounded-xl border border-slate-200 bg-white px-4 py-4 dark:border-slate-800 dark:bg-slate-950/40">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Worker Queue Visibility</h4>
                    <p className="mt-1 max-w-3xl text-xs text-slate-500 dark:text-slate-400">
                      Live queue depth for the background worker lanes that drive alerts, budgets, exports, and scheduled operations.
                    </p>
                  </div>
                  <div className="flex gap-2 text-xs">
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                      Total queued: {opsQueueSummary?.total_depth ?? 0}
                    </span>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                      Active queues: {opsQueueSummary?.busy_queues ?? 0}
                    </span>
                  </div>
                </div>

                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
                        <th className="py-2 pr-4">Queue</th>
                        <th className="py-2 pr-4">Role</th>
                        <th className="py-2 pr-4">Depth</th>
                        <th className="py-2 pr-4">Status</th>
                        <th className="py-2">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {opsQueues.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="py-4 text-sm text-slate-500 dark:text-slate-400">
                            Queue visibility will appear after the first refresh against a running Redis-backed worker stack.
                          </td>
                        </tr>
                      ) : opsQueues.map((item) => (
                        <tr key={item.queue} className="border-b border-slate-100 dark:border-slate-900">
                          <td className="py-3 pr-4 font-mono text-xs text-slate-700 dark:text-slate-200">{item.queue}</td>
                          <td className="py-3 pr-4 text-xs text-slate-600 dark:text-slate-300">{item.role}</td>
                          <td className="py-3 pr-4 text-sm font-semibold text-slate-900 dark:text-slate-100">{item.depth}</td>
                          <td className="py-3 pr-4">
                            <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                              item.status === 'busy'
                                ? 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200'
                                : item.status === 'active'
                                  ? 'bg-blue-100 text-blue-800 dark:bg-blue-500/15 dark:text-blue-200'
                                  : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-200'
                            }`}>
                              {item.status}
                            </span>
                          </td>
                          <td className="py-3 text-xs text-slate-500 dark:text-slate-400">{item.description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr,0.9fr]">
                <div className="rounded-xl border border-slate-200 bg-white px-4 py-4 dark:border-slate-800 dark:bg-slate-950/40">
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Infrastructure Hardening</h4>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Runtime posture derived from config, storage targets, and the infra policy evaluation layer.
                  </p>
                  <div className="mt-4 grid grid-cols-2 gap-3 text-xs sm:grid-cols-3">
                    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 dark:border-slate-800 dark:bg-slate-900">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">{opsStatus?.deployment_profile ?? 'core'}</div>
                      <div className="mt-1 text-slate-500 dark:text-slate-400">Deployment profile</div>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 dark:border-slate-800 dark:bg-slate-900">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">{opsStatus?.redis_durability_mode ?? 'ephemeral'}</div>
                      <div className="mt-1 text-slate-500 dark:text-slate-400">Redis durability</div>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 dark:border-slate-800 dark:bg-slate-900">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">{opsStatus?.local_tls_enabled ? 'Enabled' : 'Disabled'}</div>
                      <div className="mt-1 text-slate-500 dark:text-slate-400">Local TLS demo</div>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 dark:border-slate-800 dark:bg-slate-900">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">{opsStorage?.backup.lifecycle_enabled ? `${opsStorage.backup.retention_days}d` : 'Not set'}</div>
                      <div className="mt-1 text-slate-500 dark:text-slate-400">Object lifecycle</div>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 dark:border-slate-800 dark:bg-slate-900">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">{opsStorage?.compliance_exports.bucket ?? 'Not configured'}</div>
                      <div className="mt-1 text-slate-500 dark:text-slate-400">Compliance export bucket</div>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 dark:border-slate-800 dark:bg-slate-900">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">{opsStatus?.abuse_protection_enabled ? 'Protected' : 'Open'}</div>
                      <div className="mt-1 text-slate-500 dark:text-slate-400">System abuse controls</div>
                    </div>
                  </div>

                  {opsFeatureFlags && (
                    <div className="mt-4">
                      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Feature flags</div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {opsFeatureFlags.items.map((flag) => (
                          <span
                            key={flag.name}
                            className={`rounded-full px-3 py-1 text-[11px] font-semibold ${
                              flag.enabled
                                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-200'
                                : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                            }`}
                          >
                            {flag.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="rounded-xl border border-slate-200 bg-white px-4 py-4 dark:border-slate-800 dark:bg-slate-950/40">
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Bring-up Policy Evaluation</h4>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Advisory checks for durability, storage, abuse controls, TLS, and deployment shape.
                  </p>
                  <div className="mt-3 flex gap-2 text-xs">
                    <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 font-medium text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200">
                      Pass {opsPolicy?.summary.pass ?? 0}
                    </span>
                    <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 font-medium text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
                      Warn {opsPolicy?.summary.warn ?? 0}
                    </span>
                    <span className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 font-medium text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200">
                      Fail {opsPolicy?.summary.fail ?? 0}
                    </span>
                  </div>
                  <div className="mt-4 space-y-2">
                    {(opsPolicy?.checks ?? []).map((check) => (
                      <div key={`${check.category}:${check.name}`} className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800">
                        <div className="flex items-center justify-between gap-3">
                          <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                            {check.category} / {check.name}
                          </div>
                          <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                            check.status === 'pass'
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-200'
                              : check.status === 'warn'
                                ? 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200'
                                : 'bg-rose-100 text-rose-800 dark:bg-rose-500/15 dark:text-rose-200'
                          }`}>
                            {check.status}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{check.detail}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Cadence</label>
                  <select
                    className={`${inputCls} w-full`}
                    value={backupConfig?.cadence ?? 'daily'}
                    onChange={(e) => setBackupConfig((prev) => prev ? { ...prev, cadence: e.target.value as BackupTargetConfig['cadence'] } : prev)}
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Run time</label>
                  <select
                    className={`${inputCls} w-full`}
                    value={String(backupConfig?.run_hour_utc ?? 2)}
                    onChange={(e) => setBackupConfig((prev) => prev ? { ...prev, run_hour_utc: Number(e.target.value) } : prev)}
                  >
                    {Array.from({ length: 24 }, (_, hour) => (
                      <option key={hour} value={hour}>{String(hour).padStart(2, '0')}:00</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Retention</label>
                  <select
                    className={`${inputCls} w-full`}
                    value={String(backupConfig?.retention_days ?? 30)}
                    onChange={(e) => setBackupConfig((prev) => prev ? { ...prev, retention_days: Number(e.target.value) } : prev)}
                  >
                    <option value="7">7 days</option>
                    <option value="30">30 days</option>
                    <option value="90">90 days</option>
                    <option value="365">1 year</option>
                  </select>
                </div>
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">S3 bucket</label>
                  <input
                    className={`${inputCls} w-full`}
                    placeholder="runledger-backups"
                    value={backupConfig?.bucket ?? ''}
                    onChange={(e) => setBackupConfig((prev) => prev ? { ...prev, bucket: e.target.value } : prev)}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">AWS region</label>
                  <input
                    className={`${inputCls} w-full`}
                    placeholder="us-east-1"
                    value={backupConfig?.region ?? ''}
                    onChange={(e) => setBackupConfig((prev) => prev ? { ...prev, region: e.target.value } : prev)}
                  />
                </div>
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Encryption</label>
                  <select
                    className={`${inputCls} w-full`}
                    value={backupConfig.encryption_mode}
                    onChange={(e) => setBackupConfig((prev) => ({ ...prev, encryption_mode: e.target.value as BackupTargetConfig['encryption_mode'] }))}
                  >
                    <option value="server_side">Server-side AES256</option>
                    <option value="none">None</option>
                  </select>
                </div>
                <label className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 dark:border-slate-800 dark:bg-slate-950/40 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={backupConfig.force_path_style}
                    onChange={(e) => setBackupConfig((prev) => ({ ...prev, force_path_style: e.target.checked }))}
                    className="h-4 w-4 rounded border-slate-300 text-stone-700 focus:ring-stone-500"
                  />
                  Force path-style S3 URLs
                </label>
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Endpoint URL</label>
                  <input
                    className={`${inputCls} w-full`}
                    placeholder="http://runledger-minio:9000"
                    value={backupConfig?.endpoint_url ?? ''}
                    onChange={(e) => setBackupConfig((prev) => prev ? { ...prev, endpoint_url: e.target.value } : prev)}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Prefix</label>
                  <input
                    className={`${inputCls} w-full`}
                    placeholder="runledger"
                    value={backupConfig?.prefix ?? ''}
                    onChange={(e) => setBackupConfig((prev) => prev ? { ...prev, prefix: e.target.value } : prev)}
                  />
                </div>
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Access key</label>
                  <input
                    className={`${inputCls} w-full`}
                    placeholder="runledger"
                    value={backupConfig.access_key_id ?? ''}
                    onChange={(e) => setBackupConfig((prev) => ({ ...prev, access_key_id: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Secret key</label>
                  <input
                    className={`${inputCls} w-full`}
                    placeholder="runledgerminio"
                    value={backupConfig.secret_access_key ?? ''}
                    onChange={(e) => setBackupConfig((prev) => ({ ...prev, secret_access_key: e.target.value }))}
                  />
                </div>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-2">
                {[
                  ['include_memory_db', 'Memory DB'],
                  ['include_qdrant', 'Qdrant snapshots'],
                  ['include_kuzu', 'Kuzu graph PVC'],
                  ['include_skills', 'Skill registry PVC'],
                ].map(([field, label]) => (
                  <label key={field} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 dark:border-slate-800 dark:bg-slate-950/40 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={Boolean(backupConfig?.[field as keyof BackupTargetConfig])}
                      onChange={(e) => setBackupConfig((prev) => prev ? { ...prev, [field]: e.target.checked } as BackupTargetConfig : prev)}
                      className="h-4 w-4 rounded border-slate-300 text-stone-700 focus:ring-stone-500"
                    />
                    {label}
                  </label>
                ))}
              </div>

              <div className="mt-5 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={savingBackupConfig || !backupConfig.bucket}
                  onClick={async () => {
                    if (!apiKey) return
                    setSavingBackupConfig(true)
                    try {
                      const saved = await updateBackupConfig(apiKey, {
                        provider: 's3',
                        bucket: backupConfig.bucket,
                        prefix: backupConfig.prefix,
                        region: backupConfig.region,
                        endpoint_url: backupConfig.endpoint_url,
                        access_key_id: backupConfig.access_key_id,
                        secret_access_key: backupConfig.secret_access_key,
                        force_path_style: backupConfig.force_path_style,
                        schedule_enabled: true,
                        cadence: backupConfig.cadence,
                        run_hour_utc: backupConfig.run_hour_utc,
                        retention_days: backupConfig.retention_days,
                        include_memory_db: backupConfig.include_memory_db,
                        include_qdrant: backupConfig.include_qdrant,
                        include_kuzu: backupConfig.include_kuzu,
                        include_skills: backupConfig.include_skills,
                        encryption_mode: backupConfig.encryption_mode,
                      })
                      setBackupConfig(saved)
                      toast.success('Backup schedule saved')
                    } catch (err) {
                      console.error(err)
                      toast.error('Failed to save backup schedule')
                    } finally {
                      setSavingBackupConfig(false)
                    }
                  }}
                  className="rounded bg-stone-700 px-4 py-2 text-sm font-medium text-white hover:bg-stone-600 disabled:opacity-60 dark:bg-[#D8CAAA] dark:text-[#111318]"
                >
                  {savingBackupConfig ? 'Saving…' : 'Save schedule'}
                </button>
                <button
                  type="button"
                  disabled={testingBackupConnectionState}
                  onClick={async () => {
                    if (!apiKey) return
                    setTestingBackupConnectionState(true)
                    try {
                      const result = await testBackupConnection(apiKey)
                      if (result.ok) {
                        toast.success(result.message || 'Backup connectivity check passed')
                      } else {
                        toast.error(result.message || 'Backup connectivity check failed')
                      }
                    } catch (err) {
                      console.error(err)
                      toast.error('Failed to test backup connectivity')
                    } finally {
                      setTestingBackupConnectionState(false)
                    }
                  }}
                  className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  {testingBackupConnectionState ? 'Testing…' : 'Test S3 Connection'}
                </button>
                <button
                  type="button"
                  disabled={backupSchedulerDisabled || runningBackup}
                  onClick={async () => {
                    if (!apiKey) return
                    setRunningBackup(true)
                    try {
                      const run = await runBackupNow(apiKey)
                      setBackupRuns((prev) => [run, ...prev.filter((item) => item.id !== run.id)])
                      toast.success('Backup started in background')
                      setTimeout(() => { void loadBackupData() }, 1500)
                    } catch (err) {
                      console.error(err)
                      toast.error('Failed to start backup')
                    } finally {
                      setRunningBackup(false)
                    }
                  }}
                  className="rounded border border-stone-300 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50 disabled:opacity-60 dark:border-stone-600 dark:text-stone-200"
                >
                  {runningBackup ? 'Starting...' : 'Run backup now'}
                </button>
                <button
                  type="button"
                  disabled={runningRestoreDrillState}
                  onClick={async () => {
                    if (!apiKey) return
                    setRunningRestoreDrillState(true)
                    try {
                      const run = await runRestoreDrill(apiKey)
                      setBackupRuns((prev) => [run, ...prev.filter((item) => item.id !== run.id)])
                      toast.success('Restore drill queued')
                      setTimeout(() => { void loadBackupData() }, 1500)
                    } catch (err) {
                      console.error(err)
                      toast.error('Failed to start restore drill')
                    } finally {
                      setRunningRestoreDrillState(false)
                    }
                  }}
                  className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  {runningRestoreDrillState ? 'Starting…' : 'Run Restore Drill'}
                </button>
              </div>

              <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
                Available today: Helm CronJob backups to S3, background manual backup runs from this page, backup connectivity checks, restore drills, and `scripts/restore.sh` restore. Schedule persistence remains infrastructure-managed.
              </div>
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-900">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Backup History</h3>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Manual and scheduled backup attempts, including failures and recent command output excerpts.
                  </p>
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  {backupRuns.length} recent run{backupRuns.length === 1 ? '' : 's'}
                </div>
              </div>
              {loadingBackup ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">Loading backup history...</p>
              ) : backupRuns.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">No backup runs have been recorded yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 dark:border-gray-700">
                        <th className="py-2 pr-4 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Created</th>
                        <th className="py-2 pr-4 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Status</th>
                        <th className="py-2 pr-4 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Target</th>
                        <th className="py-2 pr-4 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Started</th>
                        <th className="py-2 pr-4 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Completed</th>
                        <th className="py-2 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {backupRuns.map((run) => (
                        <tr key={run.id} className="border-b border-gray-100 dark:border-gray-800">
                          <td className="py-2 pr-4 font-mono text-xs text-gray-700 dark:text-gray-300">
                            {new Date(run.created_at).toLocaleString()}
                          </td>
                          <td className="py-2 pr-4">
                            <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${
                              run.status === 'success'
                                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                : run.status === 'failed'
                                  ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                                  : 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                            }`}>
                              {run.status}
                            </span>
                          </td>
                          <td className="py-2 pr-4 text-xs text-gray-600 dark:text-gray-400">{run.target ?? '-'}</td>
                          <td className="py-2 pr-4 text-xs text-gray-600 dark:text-gray-400">
                            {run.started_at ? new Date(run.started_at).toLocaleString() : '-'}
                          </td>
                          <td className="py-2 pr-4 text-xs text-gray-600 dark:text-gray-400">
                            {run.completed_at ? new Date(run.completed_at).toLocaleString() : '-'}
                          </td>
                          <td className="py-2 text-xs text-slate-500 dark:text-slate-400">
                            {run.error_detail ?? run.output_excerpt ?? '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-900">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Snapshot Inventory</h3>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Recorded backup manifests with checksum, size, and artifact metadata.
                  </p>
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  {backupSnapshots.length} snapshot{backupSnapshots.length === 1 ? '' : 's'}
                </div>
              </div>
              {loadingBackup ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">Loading snapshot inventory...</p>
              ) : backupSnapshots.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">No snapshots recorded yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 dark:border-gray-700">
                        <th className="py-2 pr-4 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Created</th>
                        <th className="py-2 pr-4 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Bucket</th>
                        <th className="py-2 pr-4 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Checksum</th>
                        <th className="py-2 pr-4 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Artifacts</th>
                        <th className="py-2 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Integrity</th>
                      </tr>
                    </thead>
                    <tbody>
                      {backupSnapshots.map((snap) => (
                        <tr key={snap.id} className="border-b border-gray-100 dark:border-gray-800">
                          <td className="py-2 pr-4 font-mono text-xs text-gray-700 dark:text-gray-300">{new Date(snap.created_at).toLocaleString()}</td>
                          <td className="py-2 pr-4 text-xs text-gray-700 dark:text-gray-300">{snap.bucket}</td>
                          <td className="py-2 pr-4 font-mono text-xs text-slate-500 dark:text-slate-400">{snap.checksum ? `${snap.checksum.slice(0, 14)}...` : '-'}</td>
                          <td className="py-2 pr-4 text-xs text-slate-500 dark:text-slate-400">{snap.artifact_count}</td>
                          <td className="py-2 text-xs text-slate-500 dark:text-slate-400">{snap.integrity_status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
