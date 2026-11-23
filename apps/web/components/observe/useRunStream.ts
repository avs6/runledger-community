'use client'

import { useEffect, useRef, useState } from 'react'
import { API_URL } from '@/lib/api/client'
import { getRuns, runsStreamPath, type RunFilterParams } from '@/lib/api/observe'
import type { RunListItem } from '@/types/api'

export type StreamState = 'connecting' | 'live' | 'paused' | 'hidden' | 'error'

/**
 * Live runs over Server-Sent Events (`GET /runs/stream`), review O-07.
 *
 * Loads one window without a COUNT (`include_total=false`), then merges `run` events.
 * The stream closes while the tab is hidden or the user pauses, and resumes with
 * `since` so nothing is missed. fetch() is used instead of EventSource because the
 * API needs the Authorization header.
 */
export function useRunStream(apiKey: string, filters: RunFilterParams, paused: boolean, max = 100) {
  const [runs, setRuns] = useState<RunListItem[]>([])
  const [state, setState] = useState<StreamState>('connecting')
  const [error, setError] = useState<string | null>(null)
  const [lastEvent, setLastEvent] = useState<Date | null>(null)
  const [hidden, setHidden] = useState(false)
  const sinceRef = useRef<string | null>(null)
  const filterKey = JSON.stringify(filters)

  useEffect(() => {
    const onVisibility = () => setHidden(document.visibilityState === 'hidden')
    onVisibility()
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [])

  // Initial window: no COUNT(*).
  useEffect(() => {
    if (!apiKey) return
    let cancelled = false
    getRuns(apiKey, { ...filters, limit: max, include_total: false })
      .then(data => {
        if (cancelled) return
        setRuns(data.items)
        sinceRef.current = data.items[0]?.started_at ?? new Date().toISOString()
        setError(null)
      })
      .catch(err => { if (!cancelled) { setError(err instanceof Error ? err.message : String(err)); setState('error') } })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey, filterKey, max])

  useEffect(() => {
    if (!apiKey) return
    if (paused) { setState('paused'); return }
    if (hidden) { setState('hidden'); return }
    const controller = new AbortController()
    let retry: ReturnType<typeof setTimeout> | null = null

    const connect = async () => {
      setState('connecting')
      const since = sinceRef.current ?? new Date(Date.now() - 5 * 60_000).toISOString()
      try {
        const res = await fetch(`${API_URL}${runsStreamPath({ ...filters, since })}`, {
          headers: { Authorization: `Bearer ${apiKey}`, Accept: 'text/event-stream' },
          signal: controller.signal,
          cache: 'no-store',
        })
        if (!res.ok || !res.body) throw new Error(`API ${res.status}`)
        setState('live')
        setError(null)
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        for (;;) {
          const { value, done } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          let idx: number
          while ((idx = buffer.indexOf('\n\n')) >= 0) {
            const chunk = buffer.slice(0, idx)
            buffer = buffer.slice(idx + 2)
            const lines = chunk.split('\n')
            if (!lines.some(l => l === 'event: run')) continue
            const data = lines.filter(l => l.startsWith('data: ')).map(l => l.slice(6)).join('\n')
            try {
              const run = JSON.parse(data) as RunListItem
              setLastEvent(new Date())
              if (!sinceRef.current || run.started_at > sinceRef.current) sinceRef.current = run.started_at
              setRuns(prev => {
                const rest = prev.filter(r => r.id !== run.id)
                return [run, ...rest]
                  .sort((a, b) => b.started_at.localeCompare(a.started_at))
                  .slice(0, max)
              })
            } catch { /* ignore a malformed event */ }
          }
        }
        // Server closes after max_seconds; reconnect.
        if (!controller.signal.aborted) retry = setTimeout(connect, 500)
      } catch (err) {
        if (controller.signal.aborted) return
        setError(err instanceof Error ? err.message : String(err))
        setState('error')
        retry = setTimeout(connect, 5000)
      }
    }
    void connect()
    return () => {
      controller.abort()
      if (retry) clearTimeout(retry)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey, paused, hidden, filterKey, max])

  return { runs, state, error, lastEvent }
}
