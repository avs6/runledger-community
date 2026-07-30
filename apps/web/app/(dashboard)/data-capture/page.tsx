'use client'

import { useSession } from 'next-auth/react'
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import { useRole } from '@/components/rbac/useRole'
import { getCapturePolicy, upsertCapturePolicy } from '@/lib/api'
import type { CapturePolicyResponse } from '@/types/api'

const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

export default function DataCapturePage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { canManageOrgSettings } = useRole()

  const [capturePolicy, setCapturePolicy] = useState<CapturePolicyResponse | null>(null)
  const [privacyMode, setPrivacyMode] = useState('METADATA_ONLY')
  const [sampledRate, setSampledRate] = useState('')
  const [savingPrivacy, setSavingPrivacy] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return
    try {
      const policy = await getCapturePolicy(apiKey)
      if (policy) {
        setCapturePolicy(policy)
        setPrivacyMode(policy.privacy_mode)
        setSampledRate(policy.sampled_rate ? String(parseFloat(policy.sampled_rate) * 100) : '')
      }
    } catch (err) {
      console.error(err)
      toast.error('Failed to load capture policy')
    }
  }, [apiKey, canManageOrgSettings])

  useEffect(() => { load() }, [load])

  async function handleSavePrivacy(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setSavingPrivacy(true)
    try {
      const rate = privacyMode === 'SAMPLED' && sampledRate.trim()
        ? parseFloat(sampledRate) / 100
        : null
      const updated = await upsertCapturePolicy(apiKey, {
        privacy_mode: privacyMode,
        sampled_rate: rate,
      })
      setCapturePolicy(updated)
      toast.success('Capture policy saved')
    } catch (err) {
      console.error(err)
      toast.error('Failed to save capture policy')
    } finally {
      setSavingPrivacy(false)
    }
  }

  if (!canManageOrgSettings) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Data Capture</h1>
        <p className="mt-4 text-sm text-slate-500">Data capture policy is an organization-admin function.</p>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Data Capture Policy</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Controls what payload data the SDK sends to the collector. Affects privacy and storage.</p>
      </div>

      {capturePolicy && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 dark:text-gray-400">Current:</span>
          <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">{capturePolicy.privacy_mode}</span>
          {capturePolicy.sampled_rate && (
            <span className="text-xs text-gray-500 dark:text-gray-400">@ {(parseFloat(capturePolicy.sampled_rate) * 100).toFixed(0)}% sample rate</span>
          )}
        </div>
      )}

      <form onSubmit={handleSavePrivacy} className="space-y-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 dark:text-gray-400">Privacy mode</label>
            <select value={privacyMode} onChange={(e) => setPrivacyMode(e.target.value)} className={inputCls}>
              <option value="METADATA_ONLY">METADATA_ONLY — tokens, model, latency only (default)</option>
              <option value="ERRORS_ONLY">ERRORS_ONLY — metadata + error messages</option>
              <option value="SAMPLED">SAMPLED — full payload on a % of runs</option>
              <option value="FULL">FULL — complete request/response payloads</option>
            </select>
          </div>
          {privacyMode === 'SAMPLED' && (
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500 dark:text-gray-400">Sample rate (%)</label>
              <input type="number" min="0" max="100" step="1" placeholder="10" value={sampledRate} onChange={(e) => setSampledRate(e.target.value)} className={`w-24 ${inputCls}`} required />
            </div>
          )}
        </div>
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
          <strong>FULL</strong> mode stores raw prompts and completions. Ensure you have user consent and appropriate data retention policies before enabling.
        </div>
        <button type="submit" disabled={savingPrivacy} className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
          {savingPrivacy ? 'Saving…' : 'Save Policy'}
        </button>
      </form>
    </div>
  )
}
