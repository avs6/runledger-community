'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { listPrompts, createPrompt, deletePrompt } from '@/lib/api'
import type { PromptResponse } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { BookText, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { useRole } from '@/components/rbac/useRole'

function SkeletonRows({ cols, rows = 3 }: { cols: number; rows?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i}>
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} className="pb-2 pr-4 py-3">
              <div className="h-4 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

export default function PromptsPage() {
  const { data: session } = useSession()
  const router = useRouter()
  const { canWrite } = useRole()
  const [prompts, setPrompts] = useState<PromptResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)

  // New prompt form state
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [defaultEnv, setDefaultEnv] = useState('production')
  const [showForm, setShowForm] = useState(false)

  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  async function loadPrompts() {
    if (!apiKey) return
    try {
      const data = await listPrompts(apiKey)
      setPrompts(data.items)
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPrompts()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    setCreating(true)
    try {
      await createPrompt(apiKey, {
        name: name.trim(),
        description: description.trim() || null,
        default_environment: defaultEnv,
      })
      toast.success(`Prompt "${name}" created`)
      setName('')
      setDescription('')
      setDefaultEnv('production')
      setShowForm(false)
      await loadPrompts()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      toast.error(msg.includes('409') ? 'A prompt with that name already exists' : `Error: ${msg}`)
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete(promptName: string) {
    if (!confirm(`Delete prompt "${promptName}" and all its versions?`)) return
    try {
      await deletePrompt(apiKey, promptName)
      toast.success(`Prompt "${promptName}" deleted`)
      await loadPrompts()
    } catch (err: unknown) {
      toast.error(`Failed to delete: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Prompts</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Version-controlled prompt templates with variable substitution and environment promotion.
          </p>
        </div>
        {canWrite && (
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-2 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            New Prompt
          </button>
        )}
      </div>

      {/* Create prompt form */}
      {showForm && canWrite && (
        <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700">
          <CardHeader>
            <CardTitle className="text-base text-gray-900 dark:text-white">Create Prompt</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  Name <span className="text-red-500">*</span>
                </label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="support-agent"
                  required
                  className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  Description
                </label>
                <input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional description"
                  className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  Default Environment
                </label>
                <select
                  value={defaultEnv}
                  onChange={(e) => setDefaultEnv(e.target.value)}
                  className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="production">production</option>
                  <option value="staging">staging</option>
                  <option value="dev">dev</option>
                </select>
              </div>
              <div className="sm:col-span-3 flex gap-2">
                <button
                  type="submit"
                  disabled={creating}
                  className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {creating ? 'Creating…' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="rounded-md border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Prompts table */}
      <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700">
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400">Name</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400">Description</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400">Default Env</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {loading ? (
                <SkeletonRows cols={5} />
              ) : prompts.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-12 text-center">
                    <BookText className="mx-auto h-8 w-8 text-gray-300 dark:text-gray-600 mb-2" />
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      No prompts yet. Create your first prompt above.
                    </p>
                  </td>
                </tr>
              ) : (
                prompts.map((p) => (
                  <tr
                    key={p.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                    onClick={() => router.push(`/prompts/${encodeURIComponent(p.name)}`)}
                  >
                    <td className="px-4 py-3 font-mono text-indigo-600 dark:text-indigo-400 font-medium">
                      {p.name}
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-300 max-w-xs truncate">
                      {p.description ?? <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center rounded-full bg-indigo-50 dark:bg-indigo-950 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:text-indigo-300">
                        {p.default_environment}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 dark:text-gray-400">
                      {new Date(p.created_at).toLocaleDateString()}
                    </td>
                    {canWrite && (
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDelete(p.name) }}
                          className="rounded p-1 text-gray-400 hover:text-red-500 dark:hover:text-red-400"
                          title="Delete prompt"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}
