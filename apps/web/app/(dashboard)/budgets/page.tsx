'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { Plus, Bell } from 'lucide-react'
import { toast } from 'sonner'
import type { Budget, NotificationResponse } from '@/types/api'
import { getBudgets, listBudgetNotifications, createBudgetNotification } from '@/lib/api'
import BudgetList from '@/components/budgets/BudgetList'
import CreateBudgetModal from '@/components/budgets/CreateBudgetModal'

const ALL_EVENTS = ['budget.breach', 'runaway.detected']

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500'

export default function BudgetsPage() {
  const { data: session } = useSession()
  const apiKey = session?.apiKey ?? ''

  // ── Budgets ──────────────────────────────────────────────────────────────────
  const [budgets, setBudgets] = useState<Budget[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)

  // ── Notifications ─────────────────────────────────────────────────────────────
  const [notifications, setNotifications] = useState<NotificationResponse[]>([])
  const [notifChannel, setNotifChannel] = useState<'webhook' | 'slack'>('webhook')
  const [notifUrl, setNotifUrl] = useState('')
  const [notifEvents, setNotifEvents] = useState<string[]>(ALL_EVENTS)
  const [addingNotif, setAddingNotif] = useState(false)
  const [showNotifForm, setShowNotifForm] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [budgetData, notifData] = await Promise.all([
        getBudgets(apiKey),
        listBudgetNotifications(apiKey),
      ])
      setBudgets(budgetData.items)
      setNotifications(notifData.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load budgets')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => {
    load()
  }, [load])

  function handleCreated(budget: Budget) {
    setBudgets((prev) => [budget, ...prev])
    toast.success('Budget created')
  }

  function handleDeleted(id: string) {
    setBudgets((prev) => prev.filter((b) => b.id !== id))
    toast.success('Budget deleted')
  }

  function toggleEvent(event: string) {
    setNotifEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    )
  }

  async function handleAddNotification(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !notifUrl.trim() || notifEvents.length === 0) return
    setAddingNotif(true)
    try {
      const created = await createBudgetNotification(apiKey, {
        channel: notifChannel,
        destination_url: notifUrl.trim(),
        events: notifEvents,
      })
      setNotifications((prev) => [created, ...prev])
      setNotifUrl('')
      setNotifEvents(ALL_EVENTS)
      setShowNotifForm(false)
      toast.success('Notification channel added')
    } catch (err) {
      console.error(err)
      toast.error('Failed to add notification channel')
    } finally {
      setAddingNotif(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* ── Budgets ──────────────────────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold dark:text-white">Budgets</h1>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            New Budget
          </button>
        </div>

        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800" />
            ))}
          </div>
        ) : (
          <BudgetList items={budgets} apiKey={apiKey} onDeleted={handleDeleted} />
        )}
      </div>

      {/* ── Notification Channels ─────────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            <h2 className="text-base font-semibold dark:text-gray-100">Notification Channels</h2>
          </div>
          {!showNotifForm && (
            <button
              onClick={() => setShowNotifForm(true)}
              className="flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Channel
            </button>
          )}
        </div>

        {showNotifForm && (
          <form
            onSubmit={handleAddNotification}
            className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/50"
          >
            <div className="mb-3 flex flex-wrap items-end gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 dark:text-gray-400">Channel type</label>
                <select
                  value={notifChannel}
                  onChange={(e) => setNotifChannel(e.target.value as 'webhook' | 'slack')}
                  className={inputCls}
                >
                  <option value="webhook">Webhook</option>
                  <option value="slack">Slack</option>
                </select>
              </div>
              <div className="flex flex-1 flex-col gap-1">
                <label className="text-xs text-gray-500 dark:text-gray-400">
                  {notifChannel === 'slack' ? 'Slack webhook URL' : 'Destination URL'}
                </label>
                <input
                  type="url"
                  placeholder={
                    notifChannel === 'slack'
                      ? 'https://hooks.slack.com/services/...'
                      : 'https://your-webhook.example.com'
                  }
                  value={notifUrl}
                  onChange={(e) => setNotifUrl(e.target.value)}
                  className={`w-full ${inputCls}`}
                  required
                />
              </div>
            </div>

            <div className="mb-3">
              <label className="mb-1.5 block text-xs text-gray-500 dark:text-gray-400">
                Trigger on events
              </label>
              <div className="flex flex-wrap gap-3">
                {ALL_EVENTS.map((ev) => (
                  <label key={ev} className="flex cursor-pointer items-center gap-1.5 text-sm dark:text-gray-300">
                    <input
                      type="checkbox"
                      checked={notifEvents.includes(ev)}
                      onChange={() => toggleEvent(ev)}
                      className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-700">{ev}</code>
                  </label>
                ))}
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="submit"
                disabled={addingNotif || notifEvents.length === 0}
                className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {addingNotif ? 'Adding…' : 'Add Channel'}
              </button>
              <button
                type="button"
                onClick={() => setShowNotifForm(false)}
                className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {!loading && notifications.length === 0 && !showNotifForm && (
          <p className="text-sm text-gray-400 dark:text-gray-500">
            No notification channels configured. Add one to get alerted on budget breaches.
          </p>
        )}

        {notifications.length > 0 && (
          <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                <tr>
                  <th className="px-4 py-2 text-left">Channel</th>
                  <th className="px-4 py-2 text-left">Destination</th>
                  <th className="px-4 py-2 text-left">Events</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-left">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {notifications.map((n) => (
                  <tr key={n.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-4 py-2">
                      <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                        {n.channel}
                      </span>
                    </td>
                    <td className="max-w-xs truncate px-4 py-2 font-mono text-xs text-gray-600 dark:text-gray-400">
                      {n.destination_url}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap gap-1">
                        {n.events.map((ev) => (
                          <code
                            key={ev}
                            className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-700 dark:text-gray-300"
                          >
                            {ev}
                          </code>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`rounded px-2 py-0.5 text-xs ${
                          n.is_active
                            ? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300'
                            : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                        }`}
                      >
                        {n.is_active ? 'active' : 'inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">
                      {new Date(n.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && session?.apiKey && (
        <CreateBudgetModal
          apiKey={session.apiKey}
          onCreated={handleCreated}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}
