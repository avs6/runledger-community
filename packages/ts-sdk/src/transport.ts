import type { RunLedgerEvent } from './types.js'

const DEFAULT_BATCH_SIZE = 50
const DEFAULT_FLUSH_INTERVAL_MS = 2_000
const DEFAULT_TIMEOUT_MS = 5_000
const MAX_RETRIES = 3

// ── Transport ─────────────────────────────────────────────────────────────────

export class Transport {
  private readonly _apiKey: string
  private readonly _baseUrl: string
  private readonly _local: boolean
  private _queue: RunLedgerEvent[] = []
  private _timer: ReturnType<typeof setInterval> | null = null
  private _flushing = false

  constructor(opts: {
    apiKey: string
    baseUrl: string
    local?: boolean
    flushIntervalMs?: number
  }) {
    this._apiKey = opts.apiKey
    this._baseUrl = opts.baseUrl.replace(/\/$/, '')
    this._local = opts.local ?? false

    if (!this._local) {
      this._timer = setInterval(
        () => void this._flush(),
        opts.flushIntervalMs ?? DEFAULT_FLUSH_INTERVAL_MS,
      )
      // Don't block Node.js exit
      this._timer.unref?.()
    }
  }

  /** Add an event to the outbound queue. */
  enqueue(event: RunLedgerEvent): void {
    if (this._local) {
      console.log('[RunLedger]', JSON.stringify(event))
      return
    }
    this._queue.push(event)
    if (this._queue.length >= DEFAULT_BATCH_SIZE) {
      void this._flush()
    }
  }

  /** Flush all queued events immediately. Returns when done. */
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

  private async _flush(): Promise<void> {
    if (this._flushing || this._queue.length === 0) return
    this._flushing = true
    const batch = this._queue.splice(0, DEFAULT_BATCH_SIZE)
    try {
      await this._post(batch)
    } catch {
      // Silently drop — never break application flow
    } finally {
      this._flushing = false
    }
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
