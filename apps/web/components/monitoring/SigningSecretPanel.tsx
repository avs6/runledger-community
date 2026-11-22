'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import { apiErrorMessage, getIngestSigningSecret, rotateIngestSigningSecret } from '@/lib/api'
import type { IngestSigningSecret } from '@/types/api'

/**
 * Per-workspace secret for POST /ingest/v1/signed (tools that can only fire webhooks).
 * Hidden until revealed; rotating invalidates the previous secret immediately.
 */
export default function SigningSecretPanel({ apiKey }: { apiKey: string }) {
  const [secret, setSecret] = useState<IngestSigningSecret | null>(null)
  const [busy, setBusy] = useState(false)

  async function reveal() {
    setBusy(true)
    try {
      setSecret(await getIngestSigningSecret(apiKey))
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Could not load the signing secret'))
    } finally {
      setBusy(false)
    }
  }

  async function rotate() {
    if (!confirm('Rotate the signing secret? Senders using the current secret will be rejected until updated.')) return
    setBusy(true)
    try {
      setSecret(await rotateIngestSigningSecret(apiKey))
      toast.success('Signing secret rotated')
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Rotation failed'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white/90 p-3 dark:border-slate-700 dark:bg-slate-900">
      <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Signed webhook ingest</p>
      <p className="mb-2 text-[10px] text-slate-400">
        For tools that cannot send a bearer key: POST <span className="font-mono">/ingest/v1/signed</span> with
        X-RunLedger-Signature, X-RunLedger-Timestamp and a unique X-RunLedger-Nonce per request.
      </p>
      {secret ? (
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <code className="flex-1 truncate rounded bg-slate-950 px-2 py-1 font-mono text-[11px] text-green-400">{secret.secret}</code>
            <button type="button" onClick={() => void navigator.clipboard.writeText(secret.secret).then(() => toast.success('Copied'))}
              className="rounded border border-slate-300 px-2 py-0.5 text-[10px] dark:border-slate-700">Copy</button>
          </div>
          <p className="text-[10px] text-slate-400">
            Version {secret.version}. Signature: hex HMAC-SHA256 of <span className="font-mono">workspace_id.timestamp.nonce.</span> + body.
          </p>
        </div>
      ) : null}
      <div className="mt-2 flex gap-2">
        {!secret && (
          <button type="button" disabled={busy} onClick={() => void reveal()}
            className="rounded bg-indigo-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
            Reveal secret
          </button>
        )}
        <button type="button" disabled={busy} onClick={() => void rotate()}
          className="rounded border border-slate-300 px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300">
          Rotate
        </button>
      </div>
    </div>
  )
}
