'use client'

import { useSession } from 'next-auth/react'
import { useState } from 'react'
import { toast } from 'sonner'
import { useRole } from '@/components/rbac/useRole'
import { testSlackWebhook } from '@/lib/api'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

export default function IntegrationsPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { canManageOrgSettings } = useRole()

  const [slackWebhookUrl, setSlackWebhookUrl] = useState('')
  const [slackTestResult, setSlackTestResult] = useState<{ ok: boolean; error: string | null } | null>(null)
  const [testingSlack, setTestingSlack] = useState(false)

  async function handleTestSlack(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !slackWebhookUrl.trim()) return
    setTestingSlack(true)
    setSlackTestResult(null)
    try {
      const result = await testSlackWebhook(apiKey, slackWebhookUrl.trim())
      setSlackTestResult(result)
      if (result.ok) {
        toast.success('Test message sent to Slack')
      } else {
        toast.error(`Slack test failed: ${result.error}`)
      }
    } catch (err) {
      const msg = String(err)
      setSlackTestResult({ ok: false, error: msg })
      toast.error(`Slack test failed: ${msg}`)
    } finally {
      setTestingSlack(false)
    }
  }

  if (!canManageOrgSettings) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Integrations</h1>
        <p className="mt-4 text-sm text-slate-500">Integration management is an organization-admin function.</p>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Integrations</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Connect external services for notifications and event streaming.</p>
      </div>

      {/* Slack */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4 space-y-3">
        <div className="font-medium text-gray-800 dark:text-gray-200">Slack Webhook</div>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Paste an incoming webhook URL to test connectivity before configuring budget notifications
          via <code className="rounded bg-gray-100 px-1 font-mono dark:bg-gray-800">POST /budgets/{'{id}'}/notifications</code>.
        </p>
        <form onSubmit={handleTestSlack} className="flex flex-wrap gap-2">
          <input type="url" placeholder="https://hooks.slack.com/services/..." value={slackWebhookUrl} onChange={(e) => setSlackWebhookUrl(e.target.value)} className={`flex-1 ${inputCls}`} required />
          <button type="submit" disabled={testingSlack || !slackWebhookUrl.trim()} className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
            {testingSlack ? 'Sending…' : 'Test'}
          </button>
        </form>
        {slackTestResult && (
          <div className={`rounded border px-3 py-2 text-sm ${slackTestResult.ok ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300' : 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300'}`}>
            {slackTestResult.ok ? '✓ Test message sent successfully.' : <>✗ Failed: {slackTestResult.error}</>}
          </div>
        )}
      </div>
    </div>
  )
}
