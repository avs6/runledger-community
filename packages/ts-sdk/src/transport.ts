import type { RunLedgerEvent } from './types.js'

const DEFAULT_BATCH_SIZE = 50
const DEFAULT_FLUSH_INTERVAL_MS = 2_000
const DEFAULT_TIMEOUT_MS = 5_000
const MAX_RETRIES = 3
/** Max buffered events; the oldest are dropped beyond this (memory stays bounded). */
const DEFAULT_MAX_QUEUE = 1_000

// ── Transport ─────────────────────────────────────────────────────────────────

export class Transport {
  private readonly _apiKey: string
  private readonly _baseUrl: string
  private readonly _local: boolean
  private readonly _maxQueue: number
  private _queue: RunLedgerEvent[] = []
  private _timer: ReturnType<typeof setInterval> | null = null
  private _inflight: Promise<void> | null = null
  private _warnedFull = false

  constructor(opts: {
    apiKey: string
    baseUrl: string
    local?: boolean
    flushIntervalMs?: number
    maxQueueSize?: number
  }) {
    this._apiKey = opts.apiKey
    this._baseUrl = opts.baseUrl.replace(/\/$/, '')
    this._local = opts.local ?? false
    this._maxQueue = opts.maxQueueSize ?? DEFAULT_MAX_QUEUE

    if (!this._local) {
      this._timer = setInterval(
        () => void this._flush(),
        opts.flushIntervalMs ?? DEFAULT_FLUSH_INTERVAL_MS,
      )
      // Don't block Node.js exit
      this._timer.unref?.()
      // Flush what is buffered when the process is about to exit (Node only).
      const proc = (globalThis as { process?: { once?: (e: string, cb: () => void) => void } })
        .process
      proc?.once?.('beforeExit', () => void this.shutdown())
    }
  }

  /** Add an event to the outbound queue. */
  enqueue(event: RunLedgerEvent): void {
    if (this._local) {
      console.log('[RunLedger]', JSON.stringify(event))
      return
    }
    if (this._queue.length >= this._maxQueue) {
      this._queue.shift()
      if (!this._warnedFull) {
        console.warn('[RunLedger] event queue full; dropping oldest events')
        this._warnedFull = true
      }
    }
    this._queue.push(event)
    if (this._queue.length >= DEFAULT_BATCH_SIZE) {
      void this._flush()
    }
  }

  /** Flush every queued event (waits for an in-flight flush). Returns when done. */
  async flush(): Promise<void> {
    await this._flush()
  }

  /** Stop the background flush timer and flush remaining events. */
  async shutdown(): Promise<void> {
    if (this._timer) {
      clearInterval(this._timer)
      this._timer = null
    }
    await this._flush()
  }

  private _flush(): Promise<void> {
    if (this._inflight) return this._inflight.then(() => this._flush())
    if (this._queue.length === 0) return Promise.resolve()
    this._inflight = (async () => {
      try {
        while (this._queue.length > 0) {
          const batch = this._queue.splice(0, DEFAULT_BATCH_SIZE)
          try {
            await this._post(batch)
          } catch {
            // Never break application flow
          }
        }
      } finally {
        this._inflight = null
      }
    })()
    return this._inflight
  }

  private async _post(events: RunLedgerEvent[], attempt = 1): Promise<void> {
    const url = `${this._baseUrl}/ingest/v1/batch`
    const body = JSON.stringify({ events })
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS)

    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${this._apiKey}`,
          'Content-Type': 'application/json',
          'User-Agent': '@runledger/sdk',
        },
        body,
        signal: controller.signal,
      })
      clearTimeout(timer)

      if (resp.status === 429 || resp.status >= 500) {
        if (attempt < MAX_RETRIES) {
          await _sleep(200 * attempt)
          await this._post(events, attempt + 1)
        }
      }
    } catch {
      clearTimeout(timer)
      if (attempt < MAX_RETRIES) {
        await _sleep(200 * attempt)
        await this._post(events, attempt + 1)
      }
    }
  }
}

function _sleep(ms: number): Promise<void> {
  return new Promise(r => setTimeout(r, ms))
}
