'use client'

import { useSession } from 'next-auth/react'
import { useTheme } from 'next-themes'
import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Clock, DatabaseBackup, Lock, Mail, Trash2 } from 'lucide-react'
import type {
  LedgerSnapshotResponse,
  LedgerVerifyResult,
} from '@/types/api'
import {
  listLedgerSnapshots,
  generateLedgerSnapshot,
  verifyLedgerSnapshot,
} from '@/lib/api'
import { useRole } from '@/components/rbac/useRole'
import RetentionTab from '@/components/settings/RetentionTab'
import type { BackupRun, EmailPreference, EmailLogItem, OpsFeatureStatus } from '@/types/api'
import {
  getBackupHistory,
  getEmailPreferences,
  updateEmailPreferences,
  getEmailLog,
  getOpsFeatureStatus,
  runBackupNow,
  testEmailSend,
} from '@/lib/api'

const inputCls =
  'rounded border border-stone-300 dark:border-stone-700 bg-[#fbfaf7] dark:bg-[#16181F] text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-stone-500 dark:focus:ring-[#D8CAAA]'

const TABS = [
  { id: 'compliance', label: 'Compliance', description: 'Signed ledgers and audit evidence', icon: Lock },
  { id: 'retention', label: 'Data Retention', description: 'Delete or scrub old records safely', icon: Trash2 },
  { id: 'email', label: 'Email Delivery', description: 'SMTP, reporting, and notification policy', icon: Mail },
  { id: 'backup', label: 'Backup & Restore', description: 'External S3 schedules and recovery posture', icon: DatabaseBackup },
] as const

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
  const [generatingSnap, setGeneratingSnap] = useState(false)
  const [verifyingSnap, setVerifyingSnap] = useState<string | null>(null)
  const [loadingCompliance, setLoadingCompliance] = useState(false)
  const [complianceAttempted, setComplianceAttempted] = useState(false)

  // ── Email Preferences ─────────────────────────────────────────────────────────
  const [emailPrefs, setEmailPrefs] = useState<EmailPreference | null>(null)
  const [emailLog, setEmailLog] = useState<EmailLogItem[]>([])
  const [loadingEmailPrefs, setLoadingEmailPrefs] = useState(false)
  const [emailPrefsAttempted, setEmailPrefsAttempted] = useState(false)
  const [savingEmailPrefs, setSavingEmailPrefs] = useState(false)
  const [testingEmail, setTestingEmail] = useState(false)
  const [opsStatus, setOpsStatus] = useState<OpsFeatureStatus | null>(null)
  const [opsStatusAttempted, setOpsStatusAttempted] = useState(false)
  const [backupRuns, setBackupRuns] = useState<BackupRun[]>([])
  const [loadingBackup, setLoadingBackup] = useState(false)
  const [backupAttempted, setBackupAttempted] = useState(false)
  const [runningBackup, setRunningBackup] = useState(false)

  const loadCompliance = useCallback(async () => {
    if (!apiKey || !canManagePlatformSettings) return
    setComplianceAttempted(true)
    setLoadingCompliance(true)
    try {
      const snapList = await listLedgerSnapshots(apiKey)
      setSnapshots(snapList.items)
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
      setOpsStatus(await getOpsFeatureStatus(apiKey))
    } catch (err) {
      console.error(err)
      toast.error('Failed to load operational feature status')
    }
  }, [apiKey, canManagePlatformSettings])

  const loadEmailPrefs = useCallback(async () => {
    if (!apiKey || !canManagePlatformSettings) return
    setEmailPrefsAttempted(true)
    setLoadingEmailPrefs(true)
    try {
      setOpsStatusAttempted(true)
      const [prefs, logData, status] = await Promise.all([
        getEmailPreferences(apiKey),
        getEmailLog(apiKey),
        getOpsFeatureStatus(apiKey),
      ])
      setEmailPrefs(prefs)
      setEmailLog(logData.items.slice(0, 20))
      setOpsStatus(status)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load email settings')
    } finally {
      setLoadingEmailPrefs(false)
    }
  }, [apiKey, canManagePlatformSettings])

  useEffect(() => {
    if (activeTab === 'email' && !emailPrefsAttempted) loadEmailPrefs()
  }, [activeTab, emailPrefsAttempted, loadEmailPrefs])

  useEffect(() => {
    if (activeTab === 'backup' && !opsStatusAttempted) loadOpsStatus()
  }, [activeTab, opsStatusAttempted, loadOpsStatus])

  const loadBackupData = useCallback(async () => {
    if (!apiKey || !canManagePlatformSettings) return
    setBackupAttempted(true)
    setLoadingBackup(true)
    try {
      const [status, history] = await Promise.all([
        getOpsFeatureStatus(apiKey),
        getBackupHistory(apiKey, 20),
      ])
      setOpsStatus(status)
      setBackupRuns(history.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load backup history')
    } finally {
      setLoadingBackup(false)
    }
  }, [apiKey, canManagePlatformSettings])

  useEffect(() => {
    if (activeTab === 'backup' && !backupAttempted) void loadBackupData()
  }, [activeTab, backupAttempted, loadBackupData])

  const emailDeliveryDisabled = opsStatus
    ? !opsStatus.email_enabled || !opsStatus.smtp_configured
    : false
  const scheduledReportsDisabled = opsStatus
    ? !opsStatus.email_enabled || !opsStatus.email_reports_enabled || !opsStatus.smtp_configured
    : false
  const backupSchedulerDisabled = opsStatus ? !opsStatus.backup_enabled : true

  // ── Compliance handlers ─────────────────────────────────────────────────────

  async function handleGenerateSnapshot() {
    if (!apiKey) return
    setGeneratingSnap(true)
    try {
      const snap = await generateLedgerSnapshot(apiKey)
      setSnapshots((prev) => [snap, ...prev.filter((s) => s.snapshot_date !== snap.snapshot_date)])
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

      <div className="rounded-2xl border border-stone-200 bg-[#fbfaf7]/80 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950/40">

        {/* ── Compliance ────────────────────────────────────────────────────────── */}
        {activeTab === 'compliance' && (
          <div className="space-y-8">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-semibold dark:text-white">Compliance</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  Tamper-evident HMAC-signed ledger snapshots and agent tool audit registry.
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

            {/* Ledger Snapshots */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-medium dark:text-gray-100">Daily Snapshots</h3>
                <button
                  onClick={handleGenerateSnapshot}
                  disabled={generatingSnap}
                  className="rounded bg-stone-700 px-3 py-1.5 text-sm text-white hover:bg-stone-600 disabled:opacity-50 dark:bg-[#D8CAAA] dark:text-[#111318] dark:hover:bg-[#E8DDC9]"
                >
                  {generatingSnap ? 'Generating…' : 'Generate Snapshot'}
                </button>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Each snapshot is an HMAC-SHA256 signed record of daily spend. Use Verify to confirm integrity hasn&apos;t been tampered.
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

            {/* Tool Registry link */}
            <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4 text-sm text-slate-600 dark:text-slate-300">
              <p className="font-medium">Tool Registry</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Tool governance has moved to its own page.{' '}
                <a href="/tool-registry" className="text-stone-700 hover:underline dark:text-[#D8CAAA]">Go to Tool Registry →</a>
              </p>
            </div>
          </div>
        )}

        {/* ── Data Retention (Admin only) ───────────────────────────────────────── */}
        {activeTab === 'retention' && (
          <RetentionTab apiKey={apiKey ?? ''} />
        )}

        {/* ── Email Notifications ──────────────────────────────────────────────── */}
        {activeTab === 'email' && (
          <div className="space-y-6">
            {opsStatus && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
                <div className="font-semibold">Email delivery is currently quiet.</div>
                <p className="mt-1">
                  {opsStatus.email_enabled
                    ? opsStatus.smtp_configured
                      ? opsStatus.email_reports_enabled
                        ? 'SMTP and scheduled reports are enabled.'
                        : 'SMTP is configured, but scheduled reports are disabled with EMAIL_REPORTS_ENABLED=false.'
                      : 'EMAIL_ENABLED=true, but SMTP credentials are missing, so delivery is still blocked.'
                    : 'EMAIL_ENABLED=false, so welcome emails, alerts, tests, and reports are skipped by the backend.'}
                </p>
                {scheduledReportsDisabled && (
                  <p className="mt-1 text-xs">
                    Scheduled analytics reports will not be queued unless EMAIL_ENABLED=true, EMAIL_REPORTS_ENABLED=true, and SMTP credentials are set.
                  </p>
                )}
              </div>
            )}

            {loadingEmailPrefs && (
              <p className="text-sm text-gray-500 dark:text-gray-400">Loading email settings…</p>
            )}

            {/* Section 1: Email Preferences */}
            {emailPrefs && (
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
                <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">Email Notification Preferences</h3>
                <div className="space-y-4">
                  <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-800 dark:bg-slate-950/40">
                    <div className="mb-4 flex items-start gap-2">
                      <Clock className="mt-0.5 h-4 w-4 text-stone-600 dark:text-[#D8CAAA]" />
                      <div>
                        <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Scheduled analytics report</h4>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          Worker checks schedules hourly. Weekly reports send on Monday; monthly reports send on the first day of the month.
                        </p>
                      </div>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2">
                      <div>
                        <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                          Cadence
                        </label>
                        <select
                          className={`${inputCls} w-full`}
                          value={emailPrefs.report_frequency}
                          onChange={(e) => setEmailPrefs({ ...emailPrefs, report_frequency: e.target.value })}
                        >
                          <option value="never">Never</option>
                          <option value="daily">Daily</option>
                          <option value="weekly">Weekly</option>
                          <option value="monthly">Monthly</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                          Delivery hour
                        </label>
                        <select
                          className={`${inputCls} w-full`}
                          value={emailPrefs.report_hour ?? 7}
                          onChange={(e) => setEmailPrefs({ ...emailPrefs, report_hour: Number(e.target.value) })}
                        >
                          {Array.from({ length: 24 }, (_, hour) => (
                            <option key={hour} value={hour}>{String(hour).padStart(2, '0')}:00</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                          Timezone
                        </label>
                        <input
                          className={`${inputCls} w-full`}
                          value={emailPrefs.report_timezone ?? 'UTC'}
                          onChange={(e) => setEmailPrefs({ ...emailPrefs, report_timezone: e.target.value })}
                          placeholder="UTC"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                          Recipients
                        </label>
                        <select
                          className={`${inputCls} w-full`}
                          value={emailPrefs.report_recipient_mode ?? 'workspace_admins'}
                          onChange={(e) => setEmailPrefs({ ...emailPrefs, report_recipient_mode: e.target.value })}
                        >
                          <option value="workspace_admins">Workspace admins</option>
                          <option value="custom">Custom list</option>
                        </select>
                      </div>
                    </div>
                    {emailPrefs.report_recipient_mode === 'custom' && (
                      <div className="mt-3">
                        <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                          Custom recipients
                        </label>
                        <textarea
                          className={`${inputCls} min-h-20 w-full`}
                          value={emailPrefs.report_recipients ?? ''}
                          onChange={(e) => setEmailPrefs({ ...emailPrefs, report_recipients: e.target.value })}
                          placeholder="ops@example.com, finance@example.com"
                        />
                      </div>
                    )}
                    <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                      Last sent: {emailPrefs.report_last_sent_at ? new Date(emailPrefs.report_last_sent_at).toLocaleString() : 'No scheduled report sent yet.'}
                    </p>
                  </div>

                  <div className="space-y-2">
                    {(
                      [
                        ['alerts_enabled', 'Alert rule firings'],
                        ['approvals_enabled', 'Approval requests & decisions'],
                        ['reconciliation_enabled', 'Invoice reconciliation complete'],
                        ['budget_alerts_enabled', 'Budget breach & runaway protection'],
                        ['billing_closed_enabled', 'Billing period closed'],
                        ['score_regression_enabled', 'Score regressions'],
                        ['dispute_flagged_enabled', 'Invoice lines disputed'],
                      ] as [keyof EmailPreference, string][]
                    ).map(([key, label]) => (
                      <label key={key} className="flex items-center gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={emailPrefs[key] as boolean}
                          onChange={(e) => setEmailPrefs({ ...emailPrefs, [key]: e.target.checked })}
                          className="h-4 w-4 rounded border-gray-300 text-stone-700 focus:ring-stone-500"
                        />
                        <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>
                      </label>
                    ))}
                  </div>

                  <button
                    className="rounded bg-stone-700 px-4 py-2 text-sm font-medium text-white hover:bg-stone-600 disabled:opacity-50 dark:bg-[#D8CAAA] dark:text-[#111318] dark:hover:bg-[#E8DDC9]"
                    disabled={savingEmailPrefs}
                    onClick={async () => {
                      if (!apiKey || !emailPrefs) return
                      setSavingEmailPrefs(true)
                      try {
                        const updated = await updateEmailPreferences(apiKey, {
                          report_frequency: emailPrefs.report_frequency,
                          report_hour: emailPrefs.report_hour,
                          report_timezone: emailPrefs.report_timezone,
                          report_recipient_mode: emailPrefs.report_recipient_mode,
                          report_recipients: emailPrefs.report_recipients,
                          alerts_enabled: emailPrefs.alerts_enabled,
                          approvals_enabled: emailPrefs.approvals_enabled,
                          reconciliation_enabled: emailPrefs.reconciliation_enabled,
                          budget_alerts_enabled: emailPrefs.budget_alerts_enabled,
                          billing_closed_enabled: emailPrefs.billing_closed_enabled,
                          score_regression_enabled: emailPrefs.score_regression_enabled,
                          dispute_flagged_enabled: emailPrefs.dispute_flagged_enabled,
                        })
                        setEmailPrefs(updated)
                        toast.success('Email preferences saved')
                      } catch (err) {
                        console.error(err)
                        toast.error('Failed to save preferences')
                      } finally {
                        setSavingEmailPrefs(false)
                      }
                    }}
                  >
                    {savingEmailPrefs ? 'Saving…' : 'Save Preferences'}
                  </button>
                </div>
              </div>
            )}

            {/* Section 2: SMTP Test */}
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
              <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-2">Test Email Delivery</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                Sends a test email to the address associated with your session to verify SMTP is configured correctly.
              </p>
              <button
                className="px-4 py-2 rounded bg-gray-700 text-white text-sm font-medium hover:bg-gray-600 disabled:opacity-50"
                disabled={testingEmail || emailDeliveryDisabled}
                onClick={async () => {
                  if (!apiKey) return
                  setTestingEmail(true)
                  try {
                    const result = await testEmailSend(apiKey)
                    if (result.ok) {
                      toast.success('Test email sent!')
                    } else {
                      toast.error(`Failed: ${result.error ?? 'unknown error'}`)
                    }
                  } catch (err) {
                    toast.error('Failed to send test email')
                    console.error(err)
                  } finally {
                    setTestingEmail(false)
                  }
                }}
              >
                {testingEmail ? 'Sending…' : emailDeliveryDisabled ? 'Email disabled' : 'Send Test Email'}
              </button>
            </div>

            {/* Section 3: Email Delivery History */}
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Email Delivery History</h3>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Recent sends, failures, and test deliveries recorded by the backend mail pipeline.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void loadEmailPrefs()}
                  disabled={loadingEmailPrefs}
                  className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300"
                >
                  Refresh
                </button>
              </div>
              {emailLog.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">No emails sent yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 dark:border-gray-700">
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Sent At</th>
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">To</th>
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Subject</th>
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Event Type</th>
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
                        <th className="text-left py-2 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      {emailLog.map((item) => (
                        <tr key={item.id} className="border-b border-gray-100 dark:border-gray-800">
                          <td className="py-2 pr-4 text-gray-700 dark:text-gray-300 font-mono text-xs">
                            {new Date(item.sent_at).toLocaleString()}
                          </td>
                          <td className="py-2 pr-4 text-gray-700 dark:text-gray-300 text-xs">{item.to_email}</td>
                          <td className="py-2 pr-4 text-gray-700 dark:text-gray-300 text-xs">{item.subject}</td>
                          <td className="py-2 pr-4 text-gray-500 dark:text-gray-400 text-xs font-mono">{item.event_type}</td>
                          <td className="py-2 pr-4">
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                item.status === 'sent'
                                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                  : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                              }`}
                            >
                              {item.status}
                            </span>
                          </td>
                          <td className="py-2 text-xs text-slate-500 dark:text-slate-400">
                            {item.error_message ?? '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
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

              <div className="mt-6 grid gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Cadence</label>
                  <select className={`${inputCls} w-full`} defaultValue="daily" disabled={backupSchedulerDisabled}>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Run time</label>
                  <select className={`${inputCls} w-full`} defaultValue="2" disabled={backupSchedulerDisabled}>
                    {Array.from({ length: 24 }, (_, hour) => (
                      <option key={hour} value={hour}>{String(hour).padStart(2, '0')}:00</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Retention</label>
                  <select className={`${inputCls} w-full`} defaultValue="30" disabled={backupSchedulerDisabled}>
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
                  <input className={`${inputCls} w-full`} placeholder="s3://my-bucket/runledger-backups" disabled={backupSchedulerDisabled} />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">AWS region</label>
                  <input className={`${inputCls} w-full`} placeholder="us-east-1" disabled={backupSchedulerDisabled} />
                </div>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-2">
                {[
                  'Control-plane Postgres',
                  'Memory DB',
                  'Qdrant snapshots',
                  'Kuzu graph PVC',
                  'Skill registry PVC',
                  'Trace/export artifacts',
                ].map((label) => (
                  <label key={label} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 dark:border-slate-800 dark:bg-slate-950/40 dark:text-slate-300">
                    <input type="checkbox" defaultChecked={label !== 'Qdrant snapshots'} disabled={backupSchedulerDisabled} className="h-4 w-4 rounded border-slate-300 text-stone-700 focus:ring-stone-500" />
                    {label}
                  </label>
                ))}
              </div>

              <div className="mt-5 flex flex-wrap gap-2">
                <button disabled className="rounded bg-stone-700 px-4 py-2 text-sm font-medium text-white opacity-60 dark:bg-[#D8CAAA] dark:text-[#111318]">
                  Save schedule
                </button>
                <button disabled className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-500 opacity-70 dark:border-slate-700">
                  Test S3 connection
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
                <button disabled className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-500 opacity-70 dark:border-slate-700">
                  Restore docs planned
                </button>
              </div>

              <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
                Available today: Helm CronJob backups to S3, background manual backup runs from this page, and `scripts/restore.sh` restore. Planned next: save schedule, test S3 connection, and guided restore drills.
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
          </div>
        )}
      </div>
    </div>
  )
}
