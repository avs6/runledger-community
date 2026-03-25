'use client'

import { useEffect, useState } from 'react'
import { Github, Upload, Download, Settings2 } from 'lucide-react'
import { toast } from 'sonner'
import { getGithubConfig, saveGithubConfig, pushToGithub, pullFromGithub } from '@/lib/api'
import type { GithubConfig } from '@/types/api'

const inputCls =
  'w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'

export default function GitTab({ apiKey }: { apiKey: string }) {
  const [config, setConfig] = useState<GithubConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [repo, setRepo] = useState('')
  const [branch, setBranch] = useState('main')
  const [prefix, setPrefix] = useState('prompts/')
  const [token, setToken] = useState('')
  const [autoSync, setAutoSync] = useState(false)
  const [saving, setSaving] = useState(false)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    if (!apiKey) return
    getGithubConfig(apiKey)
      .then((cfg) => {
        if (cfg) {
          setConfig(cfg)
          setRepo(cfg.repo)
          setBranch(cfg.branch)
          setPrefix(cfg.path_prefix)
          setAutoSync(cfg.auto_sync)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [apiKey])

  async function handleSave() {
    if (!repo.trim()) { toast.error('Repo is required'); return }
    setSaving(true)
    try {
      const cfg = await saveGithubConfig(
        apiKey,
        { repo: repo.trim(), branch, path_prefix: prefix, token: token || undefined, auto_sync: autoSync },
        !!config
      )
      setConfig(cfg)
      setToken('')
      toast.success('Git config saved')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Save failed')
    } finally { setSaving(false) }
  }

  async function handlePush() {
    setSyncing(true)
    try {
      const result = await pushToGithub(apiKey)
      toast.success(`Pushed ${result.pushed} prompt(s) to GitHub`)
      if (result.errors.length > 0) toast.error(`Errors: ${result.errors[0]}`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Push failed')
    } finally { setSyncing(false) }
  }

  async function handlePull() {
    setSyncing(true)
    try {
      const result = await pullFromGithub(apiKey)
      toast.success(`Pulled ${result.pulled} prompt(s) from GitHub`)
      if (result.errors.length > 0) toast.error(`Errors: ${result.errors[0]}`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Pull failed')
    } finally { setSyncing(false) }
  }

  if (loading) return <div className="h-32 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800" />

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
          <Github className="h-4 w-4" /> GitHub Sync
        </h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Connect a GitHub repository to push/pull prompt templates as YAML files. Once configured, you can sync directly from any Prompt detail page.
        </p>
      </div>

      {config?.last_sync_at && (
        <div className="rounded-lg bg-gray-50 dark:bg-gray-800 px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
          Last sync: {new Date(config.last_sync_at).toLocaleString()} ·{' '}
          <span className={config.last_sync_status === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-500'}>
            {config.last_sync_status}
          </span>
          {config.last_sync_message && ` · ${config.last_sync_message}`}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Repository (owner/repo) *</label>
          <input className={inputCls} value={repo} onChange={e => setRepo(e.target.value)} placeholder="acme/ai-prompts" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Branch</label>
          <input className={inputCls} value={branch} onChange={e => setBranch(e.target.value)} placeholder="main" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Path Prefix (folder in repo)</label>
          <input className={inputCls} value={prefix} onChange={e => setPrefix(e.target.value)} placeholder="prompts/" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
            GitHub Token (PAT){config ? ' — leave blank to keep existing' : ''}
          </label>
          <input className={inputCls} value={token} onChange={e => setToken(e.target.value)} type="password" placeholder={config ? '••••••••' : 'ghp_...'} />
        </div>
        <div className="sm:col-span-2 flex items-center gap-2">
          <input type="checkbox" id="autoSync" checked={autoSync} onChange={e => setAutoSync(e.target.checked)} className="rounded" />
          <label htmlFor="autoSync" className="text-sm text-gray-600 dark:text-gray-300">Auto-sync on prompt changes</label>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          <Settings2 className="h-4 w-4" />
          {saving ? 'Saving…' : 'Save Config'}
        </button>
        {config && (
          <>
            <button
              onClick={handlePush}
              disabled={syncing}
              className="flex items-center gap-2 rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50"
            >
              <Upload className="h-4 w-4" />
              {syncing ? 'Syncing…' : 'Push Prompts to GitHub'}
            </button>
            <button
              onClick={handlePull}
              disabled={syncing}
              className="flex items-center gap-2 rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50"
            >
              <Download className="h-4 w-4" />
              {syncing ? 'Syncing…' : 'Pull Prompts from GitHub'}
            </button>
          </>
        )}
      </div>

      {config && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-4 text-sm">
          <p className="font-medium text-gray-900 dark:text-gray-100 mb-1">
            Connected: <code className="font-mono text-indigo-600 dark:text-indigo-400">{config.repo}</code>
          </p>
          <p className="text-gray-500 dark:text-gray-400">Branch: {config.branch} · Path: {config.path_prefix}</p>
        </div>
      )}
    </div>
  )
}
