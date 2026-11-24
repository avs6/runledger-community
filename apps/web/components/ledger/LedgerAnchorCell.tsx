'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import { anchorLedgerSnapshot } from '@/lib/api'
import type { LedgerSnapshotResponse } from '@/types/api'

/**
 * Off-box anchor state of a sealed snapshot (review cd:M-02): written to the
 * workspace's backup bucket, with S3 Object Lock when the bucket supports it.
 */
export function LedgerAnchorCell({
  apiKey,
  snapshot,
  onAnchored,
}: {
  apiKey: string
  snapshot: LedgerSnapshotResponse
  onAnchored: (snap: LedgerSnapshotResponse) => void
}) {
  const [busy, setBusy] = useState(false)
  if (snapshot.anchor_uri) {
    return (
      <span
        title={snapshot.anchor_uri}
        className={`rounded px-2 py-0.5 text-xs ${
          snapshot.anchor_locked
            ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
            : 'bg-amber-100 text-amber-700 dark:bg-amber-900/60 dark:text-amber-300'
        }`}
      >
        {snapshot.anchor_locked ? 'anchored · locked' : 'anchored · no lock'}
      </span>
    )
  }
  if (snapshot.entry_count == null) {
    return <span className="text-xs text-gray-400">legacy</span>
  }
  async function handleAnchor() {
    setBusy(true)
    try {
      const updated = await anchorLedgerSnapshot(apiKey, snapshot.snapshot_date)
      onAnchored(updated)
      toast.success(updated.anchor_locked ? 'Anchored with Object Lock' : 'Anchored (bucket has no Object Lock)')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Anchor failed')
    } finally {
      setBusy(false)
    }
  }
  return (
    <button
      type="button"
      onClick={handleAnchor}
      disabled={busy}
      aria-label={`Anchor the ${snapshot.snapshot_date} snapshot off-box`}
      className="rounded border border-gray-300 px-2 py-0.5 text-xs hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:hover:bg-gray-800"
    >
      {busy ? 'Anchoring…' : 'Anchor'}
    </button>
  )
}
