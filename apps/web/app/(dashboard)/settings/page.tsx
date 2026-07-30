'use client'

import { useSession } from 'next-auth/react'
import { useTheme } from 'next-themes'
import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Lock, Trash2, Mail } from 'lucide-react'
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
import type { EmailPreference, EmailLogItem } from '@/types/api'
import {
  getEmailPreferences,
  updateEmailPreferences,
  testEmailSend,
  getEmailLog,
} from '@/lib/api'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

const TABS = [
  { id: 'compliance', label: 'Compliance', icon: Lock },
  { id: 'retention', label: 'Data Retention', icon: Trash2 },
  { id: 'email', label: 'Email', icon: Mail },
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

  const loadEmailPrefs = useCallback(async () => {
    if (!apiKey || !canManagePlatformSettings) return
    setEmailPrefsAttempted(true)
    setLoadingEmailPrefs(true)
    try {
      const [prefs, logData] = await Promise.all([
        getEmailPreferences(apiKey),
        getEmailLog(apiKey),
      ])
      setEmailPrefs(prefs)
      setEmailLog(logData.items.slice(0, 20))
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
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-52 shrink-0 border-r border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 py-4 px-2">
        <div className="mb-3 px-2 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">Platform Settings</div>
        <nav className="flex flex-col gap-0.5">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-left w-full transition-colors ${
                activeTab === id
                  ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm font-medium'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-white/70 dark:hover:bg-slate-800/70 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </button>
          ))}
        </nav>

        {/* Appearance at bottom */}
        <div className="mt-6 px-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2">Appearance</div>
          <select
            value={theme ?? 'system'}
            onChange={(e) => setTheme(e.target.value)}
            className="w-full rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">System</option>
          </select>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">

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
                  className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
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
                                className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline disabled:opacity-50"
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
                <a href="/tool-registry" className="text-violet-600 dark:text-violet-400 hover:underline">Go to Tool Registry →</a>
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
            {loadingEmailPrefs && (
              <p className="text-sm text-gray-500 dark:text-gray-400">Loading email settings…</p>
            )}

            {/* Section 1: Email Preferences */}
            {emailPrefs && (
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
                <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">Email Notification Preferences</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Report Frequency
                    </label>
                    <select
                      className={inputCls}
                      value={emailPrefs.report_frequency}
                      onChange={(e) => setEmailPrefs({ ...emailPrefs, report_frequency: e.target.value })}
                    >
                      <option value="never">Never</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
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
                          className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>
                      </label>
                    ))}
                  </div>

                  <button
                    className="px-4 py-2 rounded bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
                    disabled={savingEmailPrefs}
                    onClick={async () => {
                      if (!apiKey || !emailPrefs) return
                      setSavingEmailPrefs(true)
                      try {
                        const updated = await updateEmailPreferences(apiKey, {
                          report_frequency: emailPrefs.report_frequency,
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
                disabled={testingEmail}
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
                {testingEmail ? 'Sending…' : 'Send Test Email'}
              </button>
            </div>

            {/* Section 3: Email Log */}
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
              <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">Recent Email Log</h3>
              {emailLog.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">No emails sent yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 dark:border-gray-700">
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Sent At</th>
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">To</th>
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Event Type</th>
                        <th className="text-left py-2 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {emailLog.map((item) => (
                        <tr key={item.id} className="border-b border-gray-100 dark:border-gray-800">
                          <td className="py-2 pr-4 text-gray-700 dark:text-gray-300 font-mono text-xs">
                            {new Date(item.sent_at).toLocaleString()}
                          </td>
                          <td className="py-2 pr-4 text-gray-700 dark:text-gray-300 text-xs">{item.to_email}</td>
                          <td className="py-2 pr-4 text-gray-500 dark:text-gray-400 text-xs font-mono">{item.event_type}</td>
                          <td className="py-2">
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
