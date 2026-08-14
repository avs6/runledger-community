'use client'

import { useState, useTransition } from 'react'
import { useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Loader2, Square } from 'lucide-react'
import { cancelRun } from '@/lib/api'

export default function CancelRunButton({
  runId,
  status,
}: {
  runId: string
  status: string
}) {
  const router = useRouter()
  const { data: session } = useSession()
  const [confirming, setConfirming] = useState(false)
  const [isPending, startTransition] = useTransition()
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (status !== 'running') return null

  const apiKey = (session as { apiKey?: string } | null)?.apiKey

  async function handleCancel() {
    if (!apiKey) {
      toast.error('Missing session API key')
      return
    }
    setIsSubmitting(true)
    try {
      await cancelRun(apiKey, runId)
      toast.success('Run cancelled')
      startTransition(() => {
        router.refresh()
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to cancel run'
      toast.error(message)
    } finally {
      setIsSubmitting(false)
      setConfirming(false)
    }
  }

  return confirming ? (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-500">Cancel this running run?</span>
      <button
        type="button"
        onClick={handleCancel}
        disabled={isSubmitting || isPending}
        className="inline-flex items-center gap-1 rounded-lg bg-red-600 px-3 py-2 text-xs font-semibold text-white shadow-sm hover:bg-red-700 disabled:opacity-60"
      >
        {(isSubmitting || isPending) ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Square className="h-3.5 w-3.5" />}
        Confirm cancel
      </button>
      <button
        type="button"
        onClick={() => setConfirming(false)}
        disabled={isSubmitting || isPending}
        className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
      >
        Keep running
      </button>
    </div>
  ) : (
    <button
      type="button"
      onClick={() => setConfirming(true)}
      className="inline-flex items-center gap-2 rounded-xl border border-red-300 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700 shadow-sm hover:bg-red-100"
    >
      <Square className="h-4 w-4" />
      Cancel run
    </button>
  )
}
