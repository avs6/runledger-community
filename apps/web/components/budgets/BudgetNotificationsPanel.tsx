'use client'

import { useState } from 'react'
import { Play, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import {
  createBudgetNotification,
  deleteBudgetNotification,
  testBudgetNotification,
  updateBudgetNotification,
} from '@/lib/api'
import type { NotificationResponse } from '@/types/api'

interface Props {
  initialItems: NotificationResponse[]
  apiKey: string
}

export default function BudgetNotificationsPanel({ initialItems, apiKey }: Props) {
  const [items, setItems] = useState(initialItems)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({
    channel: 'webhook',
    destination_url: '',
    events: 'budget.breach,runaway.detected',
  })

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      const created = await createBudgetNotification(apiKey, {
        channel: form.channel,
        destination_url: form.destination_url,
        events: form.events
          .split(',')
          .map((value) => value.trim())
          .filter(Boolean),
      })
      setItems((current) => [created, ...current])
      setShowForm(false)
      setForm({
        channel: 'webhook',
        destination_url: '',
        events: 'budget.breach,runaway.detected',
      })
      toast.success('Notification channel created')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create notification')
      console.error(err)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleToggle(item: NotificationResponse) {
    try {
      const updated = await updateBudgetNotification(apiKey, item.id, {
        is_active: !item.is_active,
      })
      setItems((current) => current.map((entry) => (entry.id === item.id ? updated : entry)))
      toast.success(updated.is_active ? 'Notification enabled' : 'Notification disabled')
    } catch (err) {
      toast.error('Failed to update notification')
      console.error(err)
    }
  }

  async function handleDelete(item: NotificationResponse) {
    if (!confirm('Delete this notification channel?')) return
    try {
      await deleteBudgetNotification(apiKey, item.id)
      setItems((current) => current.filter((entry) => entry.id !== item.id))
      toast.success('Notification deleted')
    } catch (err) {
      toast.error('Failed to delete notification')
      console.error(err)
    }
  }

  async function handleTest(item: NotificationResponse) {
    try {
      const result = await testBudgetNotification(apiKey, item.id)
      if (result.ok) {
        toast.success('Test delivery sent')
      } else {
        toast.error(result.error || 'Notification test failed')
      }
    } catch (err) {
      toast.error('Notification test failed')
      console.error(err)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950 md:flex-row md:items-end md:justify-between">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-wide text-slate-500">Notifications</p>
          <h3 className="text-lg font-semibold text-slate-950 dark:text-slate-100">
            Breach delivery channels
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Send budget events to webhooks or Slack so spend exceptions become operational signals.
          </p>
        </div>
        <button
          onClick={() => setShowForm((value) => !value)}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          {showForm ? 'Hide form' : 'New Channel'}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950 md:grid-cols-3"
        >
          <label className="block">
            <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Channel</span>
            <select
              value={form.channel}
              onChange={(e) => setForm({ ...form, channel: e.target.value })}
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
            >
              <option value="webhook">Webhook</option>
              <option value="slack">Slack</option>
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Destination URL</span>
            <input
              required
              value={form.destination_url}
              onChange={(e) => setForm({ ...form, destination_url: e.target.value })}
              placeholder="https://hooks.example.com/runledger"
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Events</span>
            <input
              value={form.events}
              onChange={(e) => setForm({ ...form, events: e.target.value })}
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
            />
          </label>
          <div className="md:col-span-3">
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {submitting ? 'Saving...' : 'Create Channel'}
            </button>
          </div>
        </form>
      )}

      {items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white/70 py-12 text-center text-sm text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-400">
          No budget notification channels configured yet.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
            <thead className="bg-slate-50 dark:bg-slate-900">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
                  Channel
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
                  Destination
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
                  Events
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
                  Status
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
                  Controls
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {items.map((item) => (
                <tr key={item.id}>
                  <td className="px-4 py-3 font-medium capitalize text-slate-950 dark:text-slate-100">
                    {item.channel}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">
                    {item.destination_url}
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                    {item.events.join(', ')}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleToggle(item)}
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        item.is_active
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                          : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
                      }`}
                    >
                      {item.is_active ? 'Active' : 'Paused'}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleTest(item)}
                        className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-300 dark:hover:bg-slate-900 dark:hover:text-white"
                        title="Send test"
                      >
                        <Play className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(item)}
                        className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30 dark:hover:text-red-300"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
