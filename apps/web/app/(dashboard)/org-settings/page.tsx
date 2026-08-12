'use client'

import { useSession } from 'next-auth/react'
import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Clock, Mail, MessageSquare } from 'lucide-react'
import type {
  EmailPreference,
  EmailLogItem,
  OpsFeatureStatus,
} from '@/types/api'
import {
  getEmailPreferences,
  updateEmailPreferences,
  getEmailLog,
  getOpsFeatureStatus,
  testEmailSend,
  testEmailReport,
  testSlackWebhook,
} from '@/lib/api'
import { useRole } from '@/components/rbac/useRole'

const inputCls =
  'rounded border border-slate-300 bg-white text-gray-900 px-3 py-1.5 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500'

const TABS = [
  { id: 'email', label: 'Email & Notifications', description: 'Notification preferences, reports, and delivery', icon: Mail },
  { id: 'slack', label: 'Slack', description: 'Test and configure Slack webhook alerts', icon: MessageSquare },
] as const

export default function OrgSettingsPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const searchParams = useSearchParams()
  const router = useRouter()
  const { canManageOrgSettings } = useRole()

  const activeTab = searchParams.get('tab') || 'email'
  const setTab = (tab: string) => router.push(`/org-settings?tab=${tab}`)

  // ── Email state ────────────────────────────────────────────────────────────
  const [emailPrefs, setEmailPrefs] = useState<EmailPreference | null>(null)
  const [emailLog, setEmailLog] = useState<EmailLogItem[]>([])
  const [loadingEmailPrefs, setLoadingEmailPrefs] = useState(false)
  const [emailPrefsAttempted, setEmailPrefsAttempted] = useState(false)
  const [savingEmailPrefs, setSavingEmailPrefs] = useState(false)
  const [testingEmail, setTestingEmail] = useState(false)
  const [testingEmailReportState, setTestingEmailReportState] = useState(false)
  const [opsStatus, setOpsStatus] = useState<OpsFeatureStatus | null>(null)

  // ── Slack state ────────────────────────────────────────────────────────────
  const [slackWebhookUrl, setSlackWebhookUrl] = useState('')
  const [slackTestResult, setSlackTestResult] = useState<{ ok: boolean; error: string | null } | null>(null)
  const [testingSlack, setTestingSlack] = useState(false)

  // ── Data loading ───────────────────────────────────────────────────────────
  const loadEmailPrefs = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return
    setEmailPrefsAttempted(true)
    setLoadingEmailPrefs(true)
    try {
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
  }, [apiKey, canManageOrgSettings])

  useEffect(() => {
    if (activeTab === 'email' && !emailPrefsAttempted) loadEmailPrefs()
  }, [activeTab, emailPrefsAttempted, loadEmailPrefs])

  const emailDeliveryDisabled = opsStatus
    ? !opsStatus.email_enabled || !opsStatus.smtp_configured
    : false
  const scheduledReportsDisabled = opsStatus
    ? !opsStatus.email_enabled || !opsStatus.email_reports_enabled || !opsStatus.smtp_configured
    : false

  if (!canManageOrgSettings) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900">Organization Settings</h1>
        <p className="mt-4 text-sm text-slate-500">Organization settings access requires org admin or manager role.</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 lg:p-8">
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-blue-700">
            Organization Console
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
            Organization Settings
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">
            Notification preferences, Slack integration, and org-level configuration.
          </p>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {TABS.map(({ id, label, description, icon: Icon }) => {
          const selected = activeTab === id
          return (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`group rounded-2xl border p-4 text-left transition-all ${
                selected
                  ? 'border-blue-300 bg-blue-50 text-slate-950 shadow-sm ring-1 ring-blue-300/30'
                  : 'border-slate-200 bg-white/70 text-slate-700 hover:border-blue-200 hover:bg-blue-50/50'
              }`}
            >
              <div className="flex items-start gap-3">
                <span className={`rounded-xl p-2 ${
                  selected
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 text-slate-500 group-hover:text-slate-700'
                }`}>
                  <Icon className="h-4 w-4" />
                </span>
                <span>
                  <span className="block text-sm font-semibold">{label}</span>
                  <span className="mt-1 block text-xs leading-relaxed text-slate-500">
                    {description}
                  </span>
                </span>
              </div>
            </button>
          )
        })}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">

        {/* ── Email & Notifications ──────────────────────────────────────── */}
        {activeTab === 'email' && (
          <div className="space-y-6">
            {opsStatus && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                <div className="font-semibold">Email delivery status</div>
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
              <p className="text-sm text-gray-500">Loading email settings…</p>
            )}

            {emailPrefs && (
              <div className="rounded-lg border border-gray-200 bg-white p-6">
                <h3 className="text-base font-semibold text-gray-900 mb-4">Email Notification Preferences</h3>
                <div className="space-y-4">
                  <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
                    <div className="mb-4 flex items-start gap-2">
                      <Clock className="mt-0.5 h-4 w-4 text-blue-600" />
                      <div>
                        <h4 className="text-sm font-semibold text-slate-900">Scheduled analytics report</h4>
                        <p className="mt-1 text-xs text-slate-500">
                          Worker checks schedules hourly. Weekly reports send on Monday; monthly reports send on the first day of the month.
                        </p>
                      </div>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2">
                      <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1">Cadence</label>
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
                        <label className="block text-xs font-medium text-slate-600 mb-1">Delivery hour</label>
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
                        <label className="block text-xs font-medium text-slate-600 mb-1">Timezone</label>
                        <input
                          className={`${inputCls} w-full`}
                          value={emailPrefs.report_timezone ?? 'UTC'}
                          onChange={(e) => setEmailPrefs({ ...emailPrefs, report_timezone: e.target.value })}
                          placeholder="UTC"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1">Recipients</label>
                        <select
                          className={`${inputCls} w-full`}
                          value={emailPrefs.report_recipient_mode ?? 'workspace_admins'}
                          onChange={(e) => setEmailPrefs({ ...emailPrefs, report_recipient_mode: e.target.value })}
                        >
                          <option value="workspace_admins">Workspace admins</option>
                          <option value="custom">Custom list</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1">Report template</label>
                        <select
                          className={`${inputCls} w-full`}
                          value={emailPrefs.report_template ?? 'detailed'}
                          onChange={(e) => setEmailPrefs({ ...emailPrefs, report_template: e.target.value })}
                        >
                          <option value="executive">Executive</option>
                          <option value="summary">Summary</option>
                          <option value="detailed">Detailed</option>
                        </select>
                      </div>
                    </div>
                    {emailPrefs.report_recipient_mode === 'custom' && (
                      <div className="mt-3">
                        <label className="block text-xs font-medium text-slate-600 mb-1">Custom recipients</label>
                        <textarea
                          className={`${inputCls} min-h-20 w-full`}
                          value={emailPrefs.report_recipients ?? ''}
                          onChange={(e) => setEmailPrefs({ ...emailPrefs, report_recipients: e.target.value })}
                          placeholder="ops@example.com, finance@example.com"
                        />
                      </div>
                    )}
                    <p className="mt-3 text-xs text-slate-500">
                      Last sent: {emailPrefs.report_last_sent_at ? new Date(emailPrefs.report_last_sent_at).toLocaleString() : 'No scheduled report sent yet.'}
                    </p>
                    <div className="mt-3">
                      <button
                        type="button"
                        className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                        disabled={testingEmailReportState || emailDeliveryDisabled}
                        onClick={async () => {
                          if (!apiKey) return
                          setTestingEmailReportState(true)
                          try {
                            const result = await testEmailReport(apiKey)
                            if (result.ok) {
                              toast.success(`Test report sent${result.recipient ? ` to ${result.recipient}` : ''}`)
                              void loadEmailPrefs()
                            } else {
                              toast.error(result.error ?? 'Failed to send test report')
                            }
                          } catch (err) {
                            console.error(err)
                            toast.error('Failed to send test report')
                          } finally {
                            setTestingEmailReportState(false)
                          }
                        }}
                      >
                        {testingEmailReportState ? 'Sending test report…' : emailDeliveryDisabled ? 'Report delivery disabled' : 'Send Test Report To Me'}
                      </button>
                    </div>
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
                          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="text-sm text-gray-700">{label}</span>
                      </label>
                    ))}
                  </div>

                  <button
                    className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
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
                          report_template: emailPrefs.report_template,
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

            {/* SMTP Test */}
            <div className="rounded-lg border border-gray-200 bg-white p-6">
              <h3 className="text-base font-semibold text-gray-900 mb-2">Test Email Delivery</h3>
              <p className="text-sm text-gray-500 mb-4">
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

            {/* Email Delivery History */}
            <div className="rounded-lg border border-gray-200 bg-white p-6">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-gray-900">Email Delivery History</h3>
                  <p className="mt-1 text-xs text-slate-500">
                    Recent sends, failures, and test deliveries recorded by the backend mail pipeline.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void loadEmailPrefs()}
                  disabled={loadingEmailPrefs}
                  className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                >
                  Refresh
                </button>
              </div>
              {emailLog.length === 0 ? (
                <p className="text-sm text-gray-500">No emails sent yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 uppercase">Sent At</th>
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 uppercase">To</th>
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 uppercase">Subject</th>
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 uppercase">Event Type</th>
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 uppercase">Status</th>
                        <th className="text-left py-2 text-xs font-medium text-gray-500 uppercase">Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      {emailLog.map((item) => (
                        <tr key={item.id} className="border-b border-gray-100">
                          <td className="py-2 pr-4 text-gray-700 font-mono text-xs">
                            {new Date(item.sent_at).toLocaleString()}
                          </td>
                          <td className="py-2 pr-4 text-gray-700 text-xs">{item.to_email}</td>
                          <td className="py-2 pr-4 text-gray-700 text-xs">{item.subject}</td>
                          <td className="py-2 pr-4 text-gray-500 text-xs font-mono">{item.event_type}</td>
                          <td className="py-2 pr-4">
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                item.status === 'sent'
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-red-100 text-red-800'
                              }`}
                            >
                              {item.status}
                            </span>
                          </td>
                          <td className="py-2 text-xs text-slate-500">
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

        {/* ── Slack ──────────────────────────────────────────────────────── */}
        {activeTab === 'slack' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">Slack Webhook</h2>
              <p className="mt-1 text-sm text-slate-500">
                Test incoming webhook connectivity before configuring budget notifications.
              </p>
            </div>
            <form
              onSubmit={async (e) => {
                e.preventDefault()
                if (!apiKey || !slackWebhookUrl.trim()) return
                setTestingSlack(true)
                setSlackTestResult(null)
                try {
                  const result = await testSlackWebhook(apiKey, slackWebhookUrl.trim())
                  setSlackTestResult(result)
                  if (result.ok) toast.success('Test message sent to Slack')
                  else toast.error(`Slack test failed: ${result.error}`)
                } catch (err) {
                  const msg = String(err)
                  setSlackTestResult({ ok: false, error: msg })
                  toast.error(`Slack test failed: ${msg}`)
                } finally {
                  setTestingSlack(false)
                }
              }}
              className="space-y-4"
            >
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Webhook URL</span>
                <input
                  type="url"
                  placeholder="https://hooks.slack.com/services/..."
                  value={slackWebhookUrl}
                  onChange={(e) => setSlackWebhookUrl(e.target.value)}
                  className={`mt-1 w-full ${inputCls}`}
                  required
                />
              </label>
              <button
                type="submit"
                disabled={testingSlack || !slackWebhookUrl.trim()}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {testingSlack ? 'Sending...' : 'Send Test Message'}
              </button>
            </form>
            {slackTestResult && (
              <div
                className={`rounded-xl border px-4 py-3 text-sm ${
                  slackTestResult.ok
                    ? 'border-green-200 bg-green-50 text-green-700'
                    : 'border-red-200 bg-red-50 text-red-700'
                }`}
              >
                {slackTestResult.ok ? 'Test message sent successfully.' : <>Failed: {slackTestResult.error}</>}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
