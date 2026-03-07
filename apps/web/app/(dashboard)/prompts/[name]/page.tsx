'use client'

import { useEffect, useState, use } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import {
  getPrompt,
  listVersions,
  createVersion,
  promoteVersion,
  getPromptMetrics,
} from '@/lib/api'
import type { PromptResponse, PromptVersion, VersionMetrics } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowLeft, GitBranch, Plus, ArrowUpCircle } from 'lucide-react'
import { toast } from 'sonner'

function SkeletonBlock() {
  return (
    <div className="space-y-2">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-4 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
      ))}
    </div>
  )
}

function EnvBadge({ env }: { env: string }) {
  const colors: Record<string, string> = {
    production: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    staging: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    dev: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  }
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[env] ?? colors.dev}`}
    >
      {env}
    </span>
  )
}

/** Very simple line-level diff: highlights lines added/removed between two texts. */
function SimpleDiff({ oldText, newText }: { oldText: string; newText: string }) {
  const oldLines = oldText.split('\n')
  const newLines = newText.split('\n')
  const maxLen = Math.max(oldLines.length, newLines.length)

  return (
    <div className="grid grid-cols-2 gap-4 font-mono text-xs">
      <div>
        <p className="mb-1 text-gray-500 font-sans">Before</p>
        <div className="rounded border border-gray-200 dark:border-gray-700 overflow-auto max-h-64 bg-gray-50 dark:bg-gray-900 p-2 space-y-px">
          {Array.from({ length: maxLen }).map((_, i) => {
            const line = oldLines[i] ?? ''
            const changed = line !== (newLines[i] ?? '')
            return (
              <div
                key={i}
                className={`whitespace-pre-wrap leading-5 rounded px-1 ${
                  changed ? 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300' : 'text-gray-800 dark:text-gray-200'
                }`}
              >
                {line || '\u00a0'}
              </div>
            )
          })}
        </div>
      </div>
      <div>
        <p className="mb-1 text-gray-500 font-sans">After</p>
        <div className="rounded border border-gray-200 dark:border-gray-700 overflow-auto max-h-64 bg-gray-50 dark:bg-gray-900 p-2 space-y-px">
          {Array.from({ length: maxLen }).map((_, i) => {
            const line = newLines[i] ?? ''
            const changed = line !== (oldLines[i] ?? '')
            return (
              <div
                key={i}
                className={`whitespace-pre-wrap leading-5 rounded px-1 ${
                  changed ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300' : 'text-gray-800 dark:text-gray-200'
                }`}
              >
                {line || '\u00a0'}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default function PromptDetailPage({
  params,
}: {
  params: Promise<{ name: string }>
}) {
  const { name } = use(params)
  const decodedName = decodeURIComponent(name)
  const { data: session } = useSession()
  const router = useRouter()

  const [prompt, setPrompt] = useState<PromptResponse | null>(null)
  const [versions, setVersions] = useState<PromptVersion[]>([])
  const [metrics, setMetrics] = useState<VersionMetrics[]>([])
  const [loading, setLoading] = useState(true)

  // New version form
  const [showVersionForm, setShowVersionForm] = useState(false)
  const [content, setContent] = useState('')
  const [commitMsg, setCommitMsg] = useState('')
  const [versionEnv, setVersionEnv] = useState('production')
  const [modelHint, setModelHint] = useState('')
  const [saving, setSaving] = useState(false)

  // Diff viewer
  const [diffA, setDiffA] = useState<number | null>(null)
  const [diffB, setDiffB] = useState<number | null>(null)

  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  async function load() {
    if (!apiKey) return
    try {
      const [p, vs, m] = await Promise.all([
        getPrompt(apiKey, decodedName),
        listVersions(apiKey, decodedName),
        getPromptMetrics(apiKey, decodedName),
      ])
      setPrompt(p)
      setVersions(vs.items)
      setMetrics(m.items)
    } catch {
      toast.error('Failed to load prompt')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey])

  async function handleCreateVersion(e: React.FormEvent) {
    e.preventDefault()
    if (!content.trim()) return
    setSaving(true)
    try {
      await createVersion(apiKey, decodedName, {
        content: content.trim(),
        commit_message: commitMsg.trim() || null,
        environment: versionEnv,
        model_hint: modelHint.trim() || null,
      })
      toast.success('Version committed')
      setContent('')
      setCommitMsg('')
      setModelHint('')
      setShowVersionForm(false)
      await load()
    } catch (err: unknown) {
      toast.error(`Failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setSaving(false)
    }
  }

  async function handlePromote(fromEnv: string) {
    try {
      await promoteVersion(apiKey, decodedName, {
        source_environment: fromEnv,
        target_environment: 'production',
      })
      toast.success(`Promoted ${fromEnv} → production`)
      await load()
    } catch (err: unknown) {
      toast.error(`Promote failed: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  const versionA = diffA !== null ? versions.find((v) => v.version === diffA) : null
  const versionB = diffB !== null ? versions.find((v) => v.version === diffB) : null

  const metricsMap = new Map(metrics.map((m) => [m.version, m]))

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push('/prompts')}
          className="rounded p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-xl font-semibold font-mono text-gray-900 dark:text-white">
            {decodedName}
          </h1>
          {prompt && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {prompt.description ?? 'No description'} ·{' '}
              <EnvBadge env={prompt.default_environment} />
            </p>
          )}
        </div>
        <div className="ml-auto flex gap-2">
          <button
            onClick={() => handlePromote('staging')}
            className="flex items-center gap-1.5 rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <ArrowUpCircle className="h-4 w-4" />
            Promote staging → production
          </button>
          <button
            onClick={() => setShowVersionForm((v) => !v)}
            className="flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            New Version
          </button>
        </div>
      </div>

      {/* New version form */}
      {showVersionForm && (
        <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700">
          <CardHeader>
            <CardTitle className="text-base text-gray-900 dark:text-white">Commit New Version</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateVersion} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  Content <span className="text-red-500">*</span>
                  <span className="ml-1 text-gray-400 font-normal">(use {'{{variable}}'} for placeholders)</span>
                </label>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  rows={6}
                  required
                  placeholder="You are a helpful assistant. Hello {{user_name}}, how can I help you with {{topic}} today?"
                  className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm font-mono text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                    Commit Message
                  </label>
                  <input
                    value={commitMsg}
                    onChange={(e) => setCommitMsg(e.target.value)}
                    placeholder="Improve tone"
                    className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                    Environment
                  </label>
                  <select
                    value={versionEnv}
                    onChange={(e) => setVersionEnv(e.target.value)}
                    className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="production">production</option>
                    <option value="staging">staging</option>
                    <option value="dev">dev</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                    Model Hint
                  </label>
                  <input
                    value={modelHint}
                    onChange={(e) => setModelHint(e.target.value)}
                    placeholder="gpt-4o-mini"
                    className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {saving ? 'Committing…' : 'Commit Version'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowVersionForm(false)}
                  className="rounded-md border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Version history */}
        <div className="lg:col-span-2">
          <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700">
            <CardHeader>
              <CardTitle className="text-base text-gray-900 dark:text-white flex items-center gap-2">
                <GitBranch className="h-4 w-4" />
                Version History
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {loading ? (
                <div className="p-4">
                  <SkeletonBlock />
                </div>
              ) : versions.length === 0 ? (
                <div className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  No versions yet. Commit the first version above.
                </div>
              ) : (
                <div className="divide-y divide-gray-100 dark:divide-gray-800">
                  {versions.map((v) => {
                    const m = metricsMap.get(v.version)
                    return (
                      <div key={v.id} className="px-4 py-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <span className="font-mono text-xs font-semibold text-gray-500 dark:text-gray-400 w-6">
                              v{v.version}
                            </span>
                            <EnvBadge env={v.environment} />
                            {v.model_hint && (
                              <span className="text-xs text-gray-400 font-mono">{v.model_hint}</span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                            {m && (
                              <>
                                <span>{m.run_count} runs</span>
                                {m.avg_cost_usd !== null && (
                                  <span>${m.avg_cost_usd.toFixed(4)} avg</span>
                                )}
                                {m.avg_score !== null && (
                                  <span className="text-indigo-600 dark:text-indigo-400">
                                    ★ {m.avg_score.toFixed(2)}
                                  </span>
                                )}
                              </>
                            )}
                            <span>{new Date(v.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                        {v.commit_message && (
                          <p className="mt-1 ml-8 text-sm text-gray-700 dark:text-gray-300">
                            {v.commit_message}
                          </p>
                        )}
                        <pre className="mt-2 ml-8 rounded bg-gray-50 dark:bg-gray-800 p-2 text-xs font-mono text-gray-700 dark:text-gray-300 overflow-auto max-h-24 whitespace-pre-wrap">
                          {v.content.length > 200 ? v.content.slice(0, 200) + '…' : v.content}
                        </pre>
                        {/* Diff selector */}
                        <div className="mt-2 ml-8 flex gap-2 text-xs text-gray-400">
                          <button
                            onClick={() => setDiffA(diffA === v.version ? null : v.version)}
                            className={`rounded px-2 py-0.5 border ${
                              diffA === v.version
                                ? 'border-red-400 text-red-600 dark:text-red-400'
                                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
                            }`}
                          >
                            {diffA === v.version ? '✓ before' : 'set before'}
                          </button>
                          <button
                            onClick={() => setDiffB(diffB === v.version ? null : v.version)}
                            className={`rounded px-2 py-0.5 border ${
                              diffB === v.version
                                ? 'border-green-400 text-green-600 dark:text-green-400'
                                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
                            }`}
                          >
                            {diffB === v.version ? '✓ after' : 'set after'}
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Diff viewer */}
        <div>
          <Card className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700">
            <CardHeader>
              <CardTitle className="text-base text-gray-900 dark:text-white">Diff Viewer</CardTitle>
            </CardHeader>
            <CardContent>
              {versionA && versionB ? (
                <SimpleDiff oldText={versionA.content} newText={versionB.content} />
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Select a "before" and "after" version from the history to compare them.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
