'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  Puzzle,
  Plus,
  Trash2,
  CheckCircle2,
  Sparkles,
  Zap,
  Activity,
  ShieldCheck,
  Radio,
  Layers,
  ArrowRight,
} from 'lucide-react'
import {
  listPlugins,
  createPlugin,
  deletePlugin,
  seedDefaultPlugins,
  listPluginExecutions,
} from '@/lib/api'
import type { PluginResponse, PluginExecutionResponse } from '@/types/api'

type PluginCategory = 'all' | 'security' | 'telemetry' | 'ops' | 'finops'

const inputCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'

const PREINTEGRATED_CATALOG = [
  {
    name: 'PII & Secret Redactor Plugin',
    category: 'security',
    description: 'Automatically redacts SSNs, API keys, passwords, and credit card numbers from prompts before reaching upstream LLMs.',
    plugin_type: 'transformer',
    hooks: ['pre_ingest', 'pre_gateway'],
    priority: 10,
    author: 'RunLedger Security',
    icon: ShieldCheck,
  },
  {
    name: 'LangSmith Trace Bridge',
    category: 'telemetry',
    description: 'Post-gateway telemetry enricher exporting spans, tool call traces, and token latencies to LangSmith & OpenInference collectors.',
    plugin_type: 'enricher',
    hooks: ['post_ingest', 'post_gateway'],
    priority: 20,
    author: 'RunLedger Integrations',
    icon: Radio,
  },
  {
    name: 'PagerDuty / Slack Emergency Dispatcher',
    category: 'ops',
    description: 'Instant notification webhook fired when a project breaches cost limits or triggers high-severity guardrail alerts.',
    plugin_type: 'webhook',
    hooks: ['on_budget_exceeded', 'on_guardrail_violation'],
    priority: 5,
    author: 'RunLedger Ops',
    icon: Zap,
  },
  {
    name: 'Prompt Injection Firewall',
    category: 'security',
    description: 'Pre-gateway validator inspecting incoming prompt payloads for jailbreaks, system prompt overrides, and adversarial instructions.',
    plugin_type: 'validator',
    hooks: ['pre_gateway'],
    priority: 1,
    author: 'RunLedger AI Safety',
    icon: ShieldCheck,
  },
  {
    name: 'Kafka Realtime Event Mirror',
    category: 'telemetry',
    description: 'Streams completed LLM transactions, tool execution logs, and usage telemetry directly to Kafka/Redpanda topic buffers.',
    plugin_type: 'transformer',
    hooks: ['post_gateway'],
    priority: 50,
    author: 'RunLedger Streaming',
    icon: Activity,
  },
  {
    name: 'Cost Attribution Header Injector',
    category: 'finops',
    description: 'Injects Project ID, Access Group ID, and Workspace Metadata headers into upstream model provider calls for FinOps tracking.',
    plugin_type: 'enricher',
    hooks: ['pre_gateway'],
    priority: 15,
    author: 'RunLedger FinOps',
    icon: Layers,
  },
]

export function PluginsTab() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey

  const [plugins, setPlugins] = useState<PluginResponse[]>([])
  const [executions, setExecutions] = useState<PluginExecutionResponse[]>([])
  const [selectedPluginId, setSelectedPluginId] = useState<string | null>(null)
  const [category, setCategory] = useState<PluginCategory>('all')
  const [loading, setLoading] = useState(true)

  // Custom Modal State
  const [showCustomModal, setShowCustomModal] = useState(false)
  const [name, setName] = useState('')
  const [pluginType, setPluginType] = useState('webhook')
  const [hooksStr, setHooksStr] = useState('pre_gateway, post_gateway')
  const [priority, setPriority] = useState(100)
  const [description, setDescription] = useState('')

  const loadData = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      let res = await listPlugins(apiKey)
      if (res.items.length === 0) {
        await seedDefaultPlugins(apiKey)
        res = await listPlugins(apiKey)
      }
      setPlugins(res.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load plugins')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function handleSeedDefaults() {
    if (!apiKey) return
    try {
      const res = await seedDefaultPlugins(apiKey)
      toast.success(`Populated ${res.plugins_added} pre-integrated popular plugins!`)
      loadData()
    } catch (err) {
      toast.error('Failed to seed default plugins')
    }
  }

  async function handleInstallCatalogPlugin(item: typeof PREINTEGRATED_CATALOG[0]) {
    if (!apiKey) return
    try {
      await createPlugin(apiKey, {
        name: item.name,
        description: item.description,
        plugin_type: item.plugin_type,
        hooks: item.hooks,
        priority: item.priority,
        author: item.author,
      })
      toast.success(`Plugin '${item.name}' installed and active!`)
      loadData()
    } catch (err) {
      toast.error('Failed to install plugin')
    }
  }

  async function handleCreateCustom(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !name.trim()) return
    try {
      await createPlugin(apiKey, {
        name: name.trim(),
        description: description.trim() || undefined,
        plugin_type: pluginType,
        hooks: hooksStr ? hooksStr.split(',').map((h) => h.trim()) : [],
        priority,
      })
      toast.success(`Custom plugin '${name}' created`)
      setName('')
      setDescription('')
      setShowCustomModal(false)
      loadData()
    } catch (err) {
      toast.error('Failed to create plugin')
    }
  }

  async function handleDelete(id: string) {
    if (!apiKey) return
    try {
      await deletePlugin(apiKey, id)
      toast.success('Plugin uninstalled')
      if (selectedPluginId === id) setSelectedPluginId(null)
      loadData()
    } catch (err) {
      toast.error('Failed to uninstall plugin')
    }
  }

  async function loadExecutions(pluginId: string) {
    if (!apiKey) return
    setSelectedPluginId(pluginId)
    try {
      const res = await listPluginExecutions(apiKey, pluginId)
      setExecutions(res.items)
    } catch (err) {
      toast.error('Failed to load plugin execution logs')
    }
  }

  const installedNames = new Set(plugins.map((p) => p.name))
  const filteredCatalog = PREINTEGRATED_CATALOG.filter((item) => {
    if (category === 'all') return true
    return item.category === category
  })

  if (!apiKey) return <div className="p-6 text-slate-400">Please sign in.</div>

  return (
    <div className="space-y-8 mt-6">
      {/* Header */}
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm lg:flex-row lg:items-center lg:justify-between dark:border-slate-800 dark:bg-slate-900/80">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-blue-700 dark:text-blue-400 flex items-center gap-1.5">
            <Puzzle className="h-4 w-4 text-blue-600" /> Lifecycle Extensibility Engine
          </p>
          <h2 className="mt-1 text-xl font-bold tracking-tight text-slate-950 dark:text-white">
            Plugins & Traffic Interceptors Marketplace
          </h2>
          <p className="mt-1 max-w-3xl text-sm text-slate-500">
            Extend RunLedger with pre-built lifecycle hooks that intercept LLM gateway traffic, enforce prompt safety, dispatch alert webhooks, and enrich FinOps cost attribution.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleSeedDefaults}
            className="flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-3.5 py-2 text-xs font-semibold text-blue-700 hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300 dark:hover:bg-blue-900 transition"
          >
            <Sparkles className="h-4 w-4" /> Seed Default Plugins
          </button>
          <button
            onClick={() => setShowCustomModal(true)}
            className="flex items-center gap-2 rounded-xl bg-blue-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 transition"
          >
            <Plus className="h-4 w-4" /> Custom Webhook / Plugin
          </button>
        </div>
      </div>

      {/* Catalog Cards */}
      <section className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-blue-600" /> Popular Pre-Integrated Plugins
          </h3>

          <div className="flex items-center gap-1 rounded-xl border border-slate-200 bg-white p-1 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            {(
              [
                ['all', 'All'],
                ['security', 'Security'],
                ['telemetry', 'Telemetry'],
                ['ops', 'Alert Ops'],
                ['finops', 'FinOps'],
              ] as [PluginCategory, string][]
            ).map(([catId, label]) => (
              <button
                key={catId}
                onClick={() => setCategory(catId)}
                className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                  category === catId
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredCatalog.map((item) => {
            const Icon = item.icon
            const isInstalled = installedNames.has(item.name)

            return (
              <div
                key={item.name}
                className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 hover:border-blue-300 dark:hover:border-blue-700 transition"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-blue-50 p-2.5 dark:bg-blue-950 text-blue-600 dark:text-blue-400">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <h4 className="font-bold text-slate-950 dark:text-white text-sm">
                          {item.name}
                        </h4>
                        <p className="text-xs text-slate-400 mt-0.5">{item.author}</p>
                      </div>
                    </div>
                  </div>

                  <p className="mt-3 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                    {item.description}
                  </p>

                  <div className="mt-4 flex flex-wrap gap-1.5">
                    {item.hooks.map((h) => (
                      <span
                        key={h}
                        className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-mono font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                      >
                        {h}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-3 dark:border-slate-800">
                  <span className="text-[11px] text-slate-400 font-mono">Priority: #{item.priority}</span>
                  {isInstalled ? (
                    <span className="flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 className="h-4 w-4" /> Installed
                    </span>
                  ) : (
                    <button
                      onClick={() => handleInstallCatalogPlugin(item)}
                      className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 transition"
                    >
                      Install Plugin <ArrowRight className="h-3 w-3" />
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </section>

      {/* Installed Plugins Table */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4">
        <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Puzzle className="h-5 w-5 text-blue-600" /> Installed Plugins ({plugins.length})
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50/80 dark:bg-slate-950/50 text-xs uppercase tracking-wider text-slate-500 font-semibold border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-3 px-4 text-left">Plugin Name</th>
                <th className="py-3 px-4 text-left">Type</th>
                <th className="py-3 px-4 text-left">Lifecycle Hooks</th>
                <th className="py-3 px-4 text-left">Priority</th>
                <th className="py-3 px-4 text-left">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {plugins.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-slate-950/40">
                  <td className="py-3 px-4">
                    <div className="font-semibold text-slate-900 dark:text-white">{p.name}</div>
                    <div className="text-xs text-slate-400">{p.description || 'Custom plugin handler'}</div>
                  </td>
                  <td className="py-3 px-4 text-xs font-mono text-slate-600 dark:text-slate-300 uppercase">
                    {p.plugin_type}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex flex-wrap gap-1">
                      {(p.hooks || []).map((h) => (
                        <span
                          key={h}
                          className="rounded border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] font-mono text-blue-700 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300"
                        >
                          {h}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-4 font-mono text-xs text-slate-500">#{p.priority}</td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        p.is_active
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                          : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {p.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right flex items-center justify-end gap-3">
                    <button
                      onClick={() => loadExecutions(p.id)}
                      className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 font-semibold"
                    >
                      View Logs
                    </button>
                    <button
                      onClick={() => handleDelete(p.id)}
                      className="text-xs text-red-500 hover:text-red-700 font-medium"
                    >
                      Uninstall
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Execution Log Viewer */}
        {selectedPluginId && (
          <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-950 p-4 font-mono text-xs text-slate-200 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-blue-400 font-semibold flex items-center gap-2">
                <Activity className="h-4 w-4" /> Execution Telemetry Log (ID: {selectedPluginId.slice(0, 8)}...)
              </span>
              <button
                onClick={() => setSelectedPluginId(null)}
                className="text-xs text-slate-400 hover:text-slate-200"
              >
                Close
              </button>
            </div>
            {executions.length === 0 ? (
              <p className="text-slate-500">No execution events recorded for this plugin yet.</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {executions.map((e) => (
                  <div key={e.id} className="flex items-center justify-between border-b border-slate-900 pb-1">
                    <span className="text-slate-300">
                      Hook: <span className="text-blue-300">{e.hook}</span>
                    </span>
                    <span className="text-slate-400">{e.latency_ms ? `${e.latency_ms}ms` : '—'}</span>
                    <span className={e.status === 'success' ? 'text-emerald-400' : 'text-red-400'}>
                      {e.status}
                    </span>
                    <span className="text-slate-500">{new Date(e.created_at).toLocaleTimeString()}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Custom Modal */}
      {showCustomModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Plus className="h-4 w-4 text-blue-600" /> Create Custom Interceptor / Webhook Plugin
            </h3>

            <form onSubmit={handleCreateCustom} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Plugin Name *
                </label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  placeholder="e.g. Audit Log Webhook"
                  className={inputCls}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Plugin Interceptor Type
                </label>
                <select
                  value={pluginType}
                  onChange={(e) => setPluginType(e.target.value)}
                  className={inputCls}
                >
                  <option value="webhook">Webhook (HTTP Dispatcher)</option>
                  <option value="transformer">Transformer (Payload Modifier)</option>
                  <option value="validator">Validator (Policy Filter)</option>
                  <option value="enricher">Enricher (Header / Tag Injector)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Lifecycle Hooks (comma-separated)
                </label>
                <input
                  value={hooksStr}
                  onChange={(e) => setHooksStr(e.target.value)}
                  placeholder="pre_gateway, post_gateway, on_budget_exceeded"
                  className={inputCls}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Description
                </label>
                <input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Custom interceptor description..."
                  className={inputCls}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Priority Order (1 = highest)
                </label>
                <input
                  type="number"
                  value={priority}
                  onChange={(e) => setPriority(Number(e.target.value))}
                  className={inputCls}
                />
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCustomModal(false)}
                  className="rounded-lg px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700"
                >
                  Create Plugin
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
