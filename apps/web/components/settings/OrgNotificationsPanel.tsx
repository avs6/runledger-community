'use client'

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Clock, Mail, MessageSquare } from 'lucide-react'
import type {
  EmailLogItem,
  EmailPreference,
  OrgEmailFeatureStatus,
} from '@/types/api'
import {
  getEmailLog,
  getEmailPreferences,
  getOrgEmailFeatureStatus,
  testEmailReport,
  testEmailSend,
  testSlackWebhook,
  updateEmailPreferences,
} from '@/lib/api'
import { useRole } from '@/components/rbac/useRole'

const inputCls =
  'rounded border border-slate-300 bg-white text-gray-900 px-3 py-1.5 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500'

export type OrgConsoleTab = 'overview' | 'email' | 'slack' | 'destinations'

const TABS = [
  { id: 'email', label: 'Email & Notifications', description: 'Notification preferences, reports, and delivery', icon: Mail },
  { id: 'slack', label: 'Slack', description: 'Test and configure Slack webhook alerts', icon: MessageSquare },
] as const

export function OrgNotificationsPanel({
  activeTab,
  onTabChange,
}: {
  activeTab: Extract<OrgConsoleTab, 'email' | 'slack'>
  onTabChange: (tab: Extract<OrgConsoleTab, 'email' | 'slack'>) => void
}) {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { canManageOrgSettings } = useRole()

  const [emailPrefs, setEmailPrefs] = useState<EmailPreference | null>(null)
  const [emailLog, setEmailLog] = useState<EmailLogItem[]>([])
  const [loadingEmailPrefs, setLoadingEmailPrefs] = useState(false)
  const [emailPrefsAttempted, setEmailPrefsAttempted] = useState(false)
  const [savingEmailPrefs, setSavingEmailPrefs] = useState(false)
  const [testingEmail, setTestingEmail] = useState(false)
  const [testingEmailReportState, setTestingEmailReportState] = useState(false)
  const [emailStatus, setEmailStatus] = useState<OrgEmailFeatureStatus | null>(null)

  const [slackWebhookUrl, setSlackWebhookUrl] = useState('')
  const [slackTestResult, setSlackTestResult] = useState<{ ok: boolean; error: string | null } | null>(null)
  const [testingSlack, setTestingSlack] = useState(false)

  const loadEmailPrefs = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return
    setEmailPrefsAttempted(true)
    setLoadingEmailPrefs(true)
    try {
      const [prefs, logData, status] = await Promise.all([
        getEmailPreferences(apiKey),
        getEmailLog(apiKey),
        getOrgEmailFeatureStatus(apiKey),
      ])
      setEmailPrefs(prefs)
      setEmailLog(logData.items.slice(0, 20))
      setEmailStatus(status)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load email settings')
    } finally {
      setLoadingEmailPrefs(false)
    }
  }, [apiKey, canManageOrgSettings])

  useEffect(() => {
    if (activeTab === 'email' && !emailPrefsAttempted) {
      void loadEmailPrefs()
    }
  }, [activeTab, emailPrefsAttempted, loadEmailPrefs])

  const emailDeliveryDisabled = emailStatus
    ? !emailStatus.email_enabled || !emailStatus.smtp_configured
    : false
  const scheduledReportsDisabled = emailStatus
    ? !emailStatus.email_enabled || !emailStatus.email_reports_enabled || !emailStatus.smtp_configured
    : false

  if (!canManageOrgSettings) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-950">Organization Console</h2>
        <p className="mt-2 text-sm text-slate-500">
          Organization settings access requires the org admin or org manager role.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-3 md:grid-cols-2">
        {TABS.map(({ id, label, description, icon: Icon }) => {
          const selected = activeTab === id
          return (
            <button
              key={id}
              onClick={() => onTabChange(id)}
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
        {activeTab === 'email' && (
          <div className="space-y-6">
            {emailStatus && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                <div className="font-semibold">Email delivery status</div>
                <p className="mt-1">
                  {emailStatus.email_enabled
                    ? emailStatus.smtp_configured
                      ? emailStatus.email_reports_enabled
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
                <h3 className="mb-4 text-base font-semibold text-gray-900">Email Notification Preferences</h3>
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
                        <label className="mb-1 block text-xs font-medium text-slate-600">Cadence</label>
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
                        <label className="mb-1 block text-xs font-medium text-slate-600">Delivery hour</label>
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
                        <label className="mb-1 block text-xs font-medium text-slate-600">Timezone</label>
                        <input
                          className={`${inputCls} w-full`}
                          value={emailPrefs.report_timezone ?? 'UTC'}
                          onChange={(e) => setEmailPrefs({ ...emailPrefs, report_timezone: e.target.value })}
                          placeholder="UTC"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs font-medium text-slate-600">Recipients</label>
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
                        <label className="mb-1 block text-xs font-medium text-slate-600">Report template</label>
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
                        <label className="mb-1 block text-xs font-medium text-slate-600">Custom recipients</label>
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
                      <label key={key} className="flex cursor-pointer items-center gap-3">
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

                  <div className="flex flex-wrap gap-3">
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
                          toast.success('Email settings updated')
                        } catch (err) {
                          console.error(err)
                          toast.error('Failed to update email settings')
                        } finally {
                          setSavingEmailPrefs(false)
                        }
                      }}
                    >
                      {savingEmailPrefs ? 'Saving…' : 'Save Email Settings'}
                    </button>

                    <button
                      type="button"
                      className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                      disabled={testingEmail || emailDeliveryDisabled}
                      onClick={async () => {
                        if (!apiKey) return
                        setTestingEmail(true)
                        try {
                          const result = await testEmailSend(apiKey)
                          if (result.ok) {
                            toast.success('Test email sent')
                            void loadEmailPrefs()
                          } else {
                            toast.error(result.error ?? 'Failed to send test email')
                          }
                        } catch (err) {
                          console.error(err)
                          toast.error('Failed to send test email')
                        } finally {
                          setTestingEmail(false)
                        }
                      }}
                    >
                      {testingEmail ? 'Sending test email…' : emailDeliveryDisabled ? 'Email delivery disabled' : 'Send Test Email To Me'}
                    </button>
                  </div>

                  <div>
                    <h4 className="mb-2 text-sm font-semibold text-slate-900">Recent delivery log</h4>
                    {emailLog.length === 0 ? (
                      <p className="text-sm text-slate-500">No email activity yet.</p>
                    ) : (
                      <div className="overflow-hidden rounded-lg border border-slate-200">
                        <table className="w-full text-sm">
                          <thead className="bg-slate-50">
                            <tr>
                              <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">When</th>
                              <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Event</th>
                              <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Recipient</th>
                              <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {emailLog.map((item) => (
                              <tr key={item.id}>
                                <td className="px-3 py-2 text-xs text-slate-500">{new Date(item.sent_at).toLocaleString()}</td>
                                <td className="px-3 py-2 text-sm text-slate-700">{item.event_type}</td>
                                <td className="px-3 py-2 text-sm text-slate-700">{item.to_email}</td>
                                <td className="px-3 py-2 text-sm text-slate-700">{item.status}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'slack' && (
          <div className="space-y-6">
            <div className="rounded-lg border border-gray-200 bg-white p-6">
              <h3 className="mb-2 text-base font-semibold text-gray-900">Slack Webhook Test</h3>
              <p className="mb-4 text-sm text-gray-500">
                Verify that budget alerts and governance notifications can reach your Slack channel before you wire them into live workflows.
              </p>

              <div className="space-y-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600">Incoming webhook URL</label>
                  <input
                    className={`${inputCls} w-full`}
                    placeholder="https://hooks.slack.com/services/..."
                    value={slackWebhookUrl}
                    onChange={(e) => setSlackWebhookUrl(e.target.value)}
                  />
                </div>

                <button
                  className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  disabled={testingSlack || !slackWebhookUrl.trim()}
                  onClick={async () => {
                    if (!apiKey || !slackWebhookUrl.trim()) return
                    setTestingSlack(true)
                    setSlackTestResult(null)
                    try {
                      const result = await testSlackWebhook(apiKey, slackWebhookUrl.trim())
                      setSlackTestResult(result)
                      if (result.ok) toast.success('Slack test message sent')
                      else toast.error(result.error ?? 'Slack test failed')
                    } catch (err) {
                      console.error(err)
                      toast.error('Slack test failed')
                    } finally {
                      setTestingSlack(false)
                    }
                  }}
                >
                  {testingSlack ? 'Testing Slack…' : 'Send Slack Test'}
                </button>

                {slackTestResult && (
                  <div className={`rounded-lg border px-4 py-3 text-sm ${
                    slackTestResult.ok
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                      : 'border-rose-200 bg-rose-50 text-rose-900'
                  }`}>
                    {slackTestResult.ok ? 'Test message sent successfully.' : <>Failed: {slackTestResult.error}</>}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
