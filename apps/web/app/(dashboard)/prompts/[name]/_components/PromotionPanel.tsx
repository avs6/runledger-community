'use client'

/**
 * Production promotion through the approvals queue (review B-02, B-03) with a
 * score gate (ENH). Request → approver decides in Approvals → Promote with that
 * approval. Each approval authorises one production version.
 */

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowUpCircle, Loader2, ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import {
  getVersionScore,
  listPromotionRequests,
  promoteVersion,
  requestPromotion,
  updatePrompt,
} from '@/lib/api'
import type { PromotionApproval, PromptResponse, PromptVersion, VersionScore } from '@/types/api'
import { AsyncCard } from '@/components/ui/async-card'
import { useConfirm } from '@/components/ui/confirm-dialog'

const STATUS_CLS: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  approved: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  denied: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
  cancelled: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
}

export function PromotionPanel({
  apiKey,
  prompt,
  versions,
  canWrite,
  onChanged,
}: {
  apiKey: string
  prompt: PromptResponse
  versions: PromptVersion[]
  canWrite: boolean
  onChanged: () => Promise<void> | void
}) {
  const [requests, setRequests] = useState<PromotionApproval[]>([])
  const [score, setScore] = useState<VersionScore | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [gate, setGate] = useState(prompt.promotion_min_score?.toString() ?? '')
  const { confirm, dialog } = useConfirm()

  const candidate = versions.find((v) => v.environment === 'staging') ?? null

  const load = useCallback(async () => {
    try {
      const [reqs, sc] = await Promise.all([
        listPromotionRequests(apiKey, prompt.name),
        candidate ? getVersionScore(apiKey, prompt.name, candidate.version) : Promise.resolve(null),
      ])
      setRequests(reqs.items)
      setScore(sc)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load promotions')
    } finally {
      setLoading(false)
    }
  }, [apiKey, prompt.name, candidate])

  useEffect(() => {
    void load()
  }, [load])

  const request = async () => {
    if (!candidate) return
    setBusy(true)
    try {
      await requestPromotion(apiKey, prompt.name, { source_environment: 'staging', version: candidate.version })
      toast.success(`Approval requested for v${candidate.version}`)
      await load()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setBusy(false)
    }
  }

  const promote = async (approval: PromotionApproval) => {
    const ok = await confirm({
      title: `Promote v${approval.version} to production?`,
      description: 'Uses this approval; production traffic resolving this prompt gets the new version.',
      confirmLabel: 'Promote',
    })
    if (!ok) return
    setBusy(true)
    try {
      const v = await promoteVersion(apiKey, prompt.name, {
        source_environment: approval.source_environment ?? 'staging',
        target_environment: 'production',
        approval_id: approval.id,
      })
      toast.success(`Promoted to production as v${v.version}`)
      await load()
      await onChanged()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Promote failed')
    } finally {
      setBusy(false)
    }
  }

  const saveGate = async () => {
    setBusy(true)
    try {
      if (gate.trim() === '') {
        await updatePrompt(apiKey, prompt.name, { clear_promotion_gate: true })
      } else {
        const value = Number(gate)
        if (!Number.isFinite(value) || value < 0 || value > 1) {
          toast.error('Gate must be between 0 and 1')
          return
        }
        await updatePrompt(apiKey, prompt.name, { promotion_min_score: value })
      }
      toast.success('Score gate saved')
      await onChanged()
      await load()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setBusy(false)
    }
  }

  const pendingForCandidate = requests.some(
    (r) => r.status === 'pending' && r.version === candidate?.version
  )

  return (
    <AsyncCard
      title="Promotion to production"
      description="Production versions need an approved request; the score gate blocks promotion below the threshold."
      loading={loading}
      error={error}
      onRetry={() => void load()}
    >
      {dialog}
      <div className="space-y-4 text-sm">
        <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
          <p className="font-medium">
            Candidate:{' '}
            {candidate ? `v${candidate.version} (staging)` : 'no staging version yet — commit or edit into staging first'}
          </p>
          {score ? (
            <p className="mt-1 text-slate-600 dark:text-slate-300">
              Score {score.score === null ? 'n/a' : score.score.toFixed(3)}
              {score.source ? ` from ${score.source} (${score.sample_size})` : ''}
              {score.passes_gate === null
                ? ' · no gate'
                : score.passes_gate
                  ? ' · passes the gate'
                  : ` · below the ${score.min_score} gate`}
              {score.source === null ? (
                <>
                  {' · '}
                  <Link href="/experiments?new=1" className="text-indigo-600 hover:underline">
                    run an experiment
                  </Link>
                </>
              ) : null}
            </p>
          ) : null}
          {canWrite ? (
            <button
              type="button"
              onClick={() => void request()}
              disabled={!candidate || busy || pendingForCandidate}
              className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-slate-300 px-3 py-1.5 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:hover:bg-slate-800"
            >
              <ShieldCheck className="h-4 w-4" />
              {pendingForCandidate ? 'Approval pending' : 'Request approval'}
            </button>
          ) : null}
        </div>

        <div>
          <label htmlFor="promotion-gate" className="block text-xs font-medium text-slate-500">
            Score gate (0–1, blank = none)
          </label>
          <div className="mt-1 flex gap-2">
            <input
              id="promotion-gate"
              inputMode="decimal"
              value={gate}
              onChange={(e) => setGate(e.target.value)}
              disabled={!canWrite}
              className="w-24 rounded border border-slate-300 bg-white px-2 py-1 dark:border-slate-600 dark:bg-slate-800"
            />
            {canWrite ? (
              <button type="button" onClick={() => void saveGate()} disabled={busy} className="rounded-md bg-slate-900 px-3 py-1 text-white disabled:opacity-50 dark:bg-slate-700">
                Save
              </button>
            ) : null}
          </div>
        </div>

        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Requests</p>
          {requests.length === 0 ? (
            <p className="text-slate-500">No promotion requests yet.</p>
          ) : (
            <ul className="space-y-2">
              {requests.map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-2 rounded border border-slate-200 px-2 py-1.5 dark:border-slate-700">
                  <span>
                    v{r.version ?? '?'}{' '}
                    <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_CLS[r.status] ?? STATUS_CLS.cancelled}`}>
                      {r.used_by_version ? `used → v${r.used_by_version}` : r.status}
                    </span>
                    {r.decided_by ? <span className="ml-1 text-xs text-slate-500">by {r.decided_by}</span> : null}
                  </span>
                  {r.status === 'approved' && !r.used_by_version && canWrite ? (
                    <button
                      type="button"
                      onClick={() => void promote(r)}
                      disabled={busy}
                      aria-label={`Promote version ${r.version} to production`}
                      className="inline-flex items-center gap-1 rounded-md bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <ArrowUpCircle className="h-3 w-3" />}
                      Promote
                    </button>
                  ) : r.status === 'pending' ? (
                    <Link href="/approvals" className="text-xs text-indigo-600 hover:underline">
                      Open approvals
                    </Link>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </AsyncCard>
  )
}
