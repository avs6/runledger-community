'use client'

import { useSession } from 'next-auth/react'
import { useState, useEffect, useCallback } from 'react'
import type {
  LedgerSnapshotResponse,
  LedgerVerifyResult,
  ToolRegistryResponse,
  SecurityEventResponse,
  CapturePolicyResponse,
} from '@/types/api'
import {
  listLedgerSnapshots,
  generateLedgerSnapshot,
  verifyLedgerSnapshot,
  listToolRegistry,
  upsertToolRegistry,
  deleteToolRegistry,
  getSecurityEvents,
  getCapturePolicy,
  upsertCapturePolicy,
} from '@/lib/api'

const POLICY_COLORS: Record<string, string> = {
  allow: 'bg-green-100 text-green-800',
  audit: 'bg-blue-100 text-blue-800',
  block: 'bg-red-100 text-red-800',
}

export default function LedgerPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey as string | undefined

  const [snapshots, setSnapshots] = useState<LedgerSnapshotResponse[]>([])
  const [verifyResults, setVerifyResults] = useState<Record<string, LedgerVerifyResult>>({})
  const [generating, setGenerating] = useState(false)
  const [verifying, setVerifying] = useState<string | null>(null)

  const [tools, setTools] = useState<ToolRegistryResponse[]>([])
  const [newToolName, setNewToolName] = useState('')
  const [newToolPolicy, setNewToolPolicy] = useState('audit')
  const [newToolDesc, setNewToolDesc] = useState('')
  const [registeringTool, setRegisteringTool] = useState(false)

  const [securityEvents, setSecurityEvents] = useState<SecurityEventResponse[]>([])

  const [capturePolicy, setCapturePolicy] = useState<CapturePolicyResponse | null>(null)
  const [policyMode, setPolicyMode] = useState('METADATA_ONLY')
  const [sampledRate, setSampledRate] = useState('')
  const [savingPolicy, setSavingPolicy] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey) return
    try {
      const [snapList, toolList, evtList, policy] = await Promise.all([
        listLedgerSnapshots(apiKey),
        listToolRegistry(apiKey),
        getSecurityEvents(apiKey),
        getCapturePolicy(apiKey),
      ])
      setSnapshots(snapList.items)
      setTools(toolList.items)
      setSecurityEvents(evtList.items.slice(0, 20))
      setCapturePolicy(policy)
      if (policy) {
        setPolicyMode(policy.privacy_mode)
        setSampledRate(policy.sampled_rate ?? '')
      }
    } catch (_) {
      // ignore errors silently in UI
    }
  }, [apiKey])

  useEffect(() => {
    load()
  }, [load])

  async function handleGenerate() {
    if (!apiKey) return
    setGenerating(true)
    try {
      const snap = await generateLedgerSnapshot(apiKey)
      setSnapshots((prev) => [snap, ...prev.filter((s) => s.snapshot_date !== snap.snapshot_date)])
    } finally {
      setGenerating(false)
    }
  }

  async function handleVerify(snap: LedgerSnapshotResponse) {
    if (!apiKey) return
    setVerifying(snap.snapshot_date)
    try {
      const result = await verifyLedgerSnapshot(apiKey, snap.snapshot_date)
      setVerifyResults((prev) => ({ ...prev, [snap.snapshot_date]: result }))
    } finally {
      setVerifying(null)
    }
  }

  async function handleRegisterTool(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !newToolName.trim()) return
    setRegisteringTool(true)
    try {
      const tool = await upsertToolRegistry(apiKey, {
        tool_name: newToolName.trim(),
        policy: newToolPolicy,
        description: newToolDesc.trim() || null,
      })
      setTools((prev) => {
        const filtered = prev.filter((t) => t.tool_name !== tool.tool_name)
        return [...filtered, tool].sort((a, b) => a.tool_name.localeCompare(b.tool_name))
      })
      setNewToolName('')
      setNewToolDesc('')
      setNewToolPolicy('audit')
    } finally {
      setRegisteringTool(false)
    }
  }

  async function handleDeleteTool(toolName: string) {
    if (!apiKey) return
    await deleteToolRegistry(apiKey, toolName)
    setTools((prev) => prev.filter((t) => t.tool_name !== toolName))
  }

  async function handleSavePolicy(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setSavingPolicy(true)
    try {
      const updated = await upsertCapturePolicy(apiKey, {
        privacy_mode: policyMode,
        sampled_rate: policyMode === 'SAMPLED' && sampledRate ? parseFloat(sampledRate) : null,
      })
      setCapturePolicy(updated)
    } finally {
      setSavingPolicy(false)
    }
  }

  return (
    <div className="space-y-8 p-6">
      <h1 className="text-2xl font-semibold">Ledger</h1>

      {/* ── Snapshots ─────────────────────────────────────────────────────── */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-medium">Daily Snapshots</h2>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {generating ? 'Generating…' : 'Generate snapshot'}
          </button>
        </div>

        <div className="overflow-x-auto rounded border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-2 text-left">Date</th>
                <th className="px-4 py-2 text-right">Total Cost</th>
                <th className="px-4 py-2 text-right">Calls</th>
                <th className="px-4 py-2 text-left">Hash</th>
                <th className="px-4 py-2 text-left">Integrity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {snapshots.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-gray-400">
                    No snapshots yet. Click &ldquo;Generate snapshot&rdquo; to create one.
                  </td>
                </tr>
              ) : (
                snapshots.map((snap) => {
                  const vr = verifyResults[snap.snapshot_date]
                  return (
                    <tr key={snap.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono">{snap.snapshot_date}</td>
                      <td className="px-4 py-2 text-right font-mono">
                        ${parseFloat(snap.total_cost_usd).toFixed(6)}
                      </td>
                      <td className="px-4 py-2 text-right">{snap.call_count}</td>
                      <td className="px-4 py-2 font-mono text-xs text-gray-500">
                        {snap.hash.slice(0, 12)}…
                      </td>
                      <td className="px-4 py-2">
                        {vr ? (
                          vr.match ? (
                            <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">
                              ✓ ok
                            </span>
                          ) : (
                            <span className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700">
                              ⚠ {vr.status}
                            </span>
                          )
                        ) : (
                          <button
                            onClick={() => handleVerify(snap)}
                            disabled={verifying === snap.snapshot_date}
                            className="text-xs text-indigo-600 hover:underline disabled:opacity-50"
                          >
                            {verifying === snap.snapshot_date ? 'Verifying…' : 'Verify'}
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Tool Registry ─────────────────────────────────────────────────── */}
      <section>
        <h2 className="mb-3 text-lg font-medium">Tool Registry</h2>

        <form onSubmit={handleRegisterTool} className="mb-4 flex flex-wrap gap-2">
          <input
            type="text"
            placeholder="Tool name"
            value={newToolName}
            onChange={(e) => setNewToolName(e.target.value)}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm"
            required
          />
          <select
            value={newToolPolicy}
            onChange={(e) => setNewToolPolicy(e.target.value)}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm"
          >
            <option value="allow">allow</option>
            <option value="audit">audit</option>
            <option value="block">block</option>
          </select>
          <input
            type="text"
            placeholder="Description (optional)"
            value={newToolDesc}
            onChange={(e) => setNewToolDesc(e.target.value)}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm"
          />
          <button
            type="submit"
            disabled={registeringTool}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {registeringTool ? 'Saving…' : 'Register'}
          </button>
        </form>

        <div className="overflow-x-auto rounded border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-2 text-left">Tool Name</th>
                <th className="px-4 py-2 text-left">Policy</th>
                <th className="px-4 py-2 text-left">Description</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tools.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-gray-400">
                    No tools registered.
                  </td>
                </tr>
              ) : (
                tools.map((tool) => (
                  <tr key={tool.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono">{tool.tool_name}</td>
                    <td className="px-4 py-2">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${POLICY_COLORS[tool.policy] ?? 'bg-gray-100 text-gray-700'}`}
                      >
                        {tool.policy}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-500">{tool.description ?? '—'}</td>
                    <td className="px-4 py-2 text-right">
                      <button
                        onClick={() => handleDeleteTool(tool.tool_name)}
                        className="text-xs text-red-500 hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Security Events ───────────────────────────────────────────────── */}
      <section>
        <h2 className="mb-3 text-lg font-medium">Security Events</h2>
        <div className="overflow-x-auto rounded border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-2 text-left">Type</th>
                <th className="px-4 py-2 text-left">Tool</th>
                <th className="px-4 py-2 text-left">User</th>
                <th className="px-4 py-2 text-left">Detected</th>
                <th className="px-4 py-2 text-left">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {securityEvents.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-gray-400">
                    No security events.
                  </td>
                </tr>
              ) : (
                securityEvents.map((evt) => (
                  <tr key={evt.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2">
                      <span className="rounded bg-orange-100 px-2 py-0.5 text-xs text-orange-700">
                        {evt.event_type}
                      </span>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">{evt.tool_name ?? '—'}</td>
                    <td className="px-4 py-2 text-xs text-gray-500">{evt.end_user_id ?? '—'}</td>
                    <td className="px-4 py-2 text-xs text-gray-500">
                      {new Date(evt.detected_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2 font-mono text-xs text-gray-400">
                      {JSON.stringify(evt.details)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Privacy / Capture Policy ──────────────────────────────────────── */}
      <section>
        <h2 className="mb-3 text-lg font-medium">Privacy / Capture Policy</h2>
        {capturePolicy && (
          <p className="mb-3 text-sm text-gray-500">
            Current mode:{' '}
            <span className="rounded bg-gray-100 px-2 py-0.5 font-mono text-xs">
              {capturePolicy.privacy_mode}
            </span>
            {capturePolicy.sampled_rate != null && (
              <span className="ml-2 text-xs text-gray-400">
                (rate: {capturePolicy.sampled_rate})
              </span>
            )}
          </p>
        )}
        <form onSubmit={handleSavePolicy} className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs text-gray-500">Privacy Mode</label>
            <select
              value={policyMode}
              onChange={(e) => setPolicyMode(e.target.value)}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm"
            >
              <option value="METADATA_ONLY">METADATA_ONLY</option>
              <option value="ERRORS_ONLY">ERRORS_ONLY</option>
              <option value="SAMPLED">SAMPLED</option>
              <option value="FULL">FULL</option>
            </select>
          </div>
          {policyMode === 'SAMPLED' && (
            <div>
              <label className="mb-1 block text-xs text-gray-500">Sample Rate (0–1)</label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={sampledRate}
                onChange={(e) => setSampledRate(e.target.value)}
                className="w-24 rounded border border-gray-300 px-3 py-1.5 text-sm"
                placeholder="0.10"
              />
            </div>
          )}
          <button
            type="submit"
            disabled={savingPolicy}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {savingPolicy ? 'Saving…' : 'Save Policy'}
          </button>
        </form>
      </section>
    </div>
  )
}
