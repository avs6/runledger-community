import { randomUUID } from 'node:crypto'
import { withRunLedgerContext } from './context.js'
import type { Transport } from './transport.js'
import type { TaskOptions, RunEndEvent, RunStartEvent, ToolCallEvent, ProviderCallEvent, OutcomeEvent, SpanStartEvent, SpanEndEvent } from './types.js'

export class RunLedgerTask {
  readonly runId: string
  private _outcomeRecorded = false
  private _totalCostUsd = 0
  private _totalInputTokens = 0
  private _totalOutputTokens = 0

  constructor(
    private readonly _transport: Transport,
    runId: string,
    readonly name: string,
  ) {
    this.runId = runId
  }

  recordSpan(name: string, opts: { spanType?: 'llm' | 'tool' | 'retrieval'; status?: 'succeeded' | 'failed'; metadata?: Record<string, unknown> } = {}): string {
    const spanId = randomUUID()
    const now = new Date().toISOString()
    const start: SpanStartEvent = {
      event_type: 'span_start',
      run_id: this.runId,
      span_id: spanId,
      span_type: opts.spanType ?? 'tool',
      name,
      started_at: now,
    }
    const end: SpanEndEvent = {
      event_type: 'span_end',
      run_id: this.runId,
      span_id: spanId,
      status: opts.status ?? 'succeeded',
      ended_at: now,
      metadata: opts.metadata,
    }
    this._transport.enqueue(start)
    this._transport.enqueue(end)
    return spanId
  }

  recordToolCall(toolName: string, opts: Omit<ToolCallEvent, 'event_type' | 'run_id' | 'tool_name'> = { status: 'success' }): void {
    this._transport.enqueue({
      event_type: 'tool_call',
      run_id: this.runId,
      tool_name: toolName,
      ...opts,
    })
  }

  recordModelCall(opts: Omit<ProviderCallEvent, 'event_type' | 'run_id'>): void {
    this._transport.enqueue({
      event_type: 'provider_call',
      run_id: this.runId,
      ...opts,
    })
    this._totalCostUsd += Number(opts.cost_usd ?? 0)
    this._totalInputTokens += Number(opts.input_tokens ?? 0)
    this._totalOutputTokens += Number(opts.output_tokens ?? 0)
  }

  recordOutcome(
    outcomeType: string,
    opts: {
      success?: boolean
      labels?: Record<string, unknown>
      finalStatus?: 'succeeded' | 'failed'
      totalCostUsd?: number
      totalInputTokens?: number
      totalOutputTokens?: number
      qualityScore?: number
      verificationStatus?: string
    } = {},
  ): void {
    const labels = { ...(opts.labels ?? {}) }
    if (opts.qualityScore !== undefined) labels['quality_score'] = opts.qualityScore
    if (opts.verificationStatus !== undefined) labels['verification_status'] = opts.verificationStatus
    const outcome: OutcomeEvent = {
      event_type: 'outcome',
      run_id: this.runId,
      outcome_type: outcomeType,
      success: opts.success ?? true,
      labels: Object.keys(labels).length ? labels : undefined,
    }
    const end: RunEndEvent = {
      event_type: 'run_end',
      run_id: this.runId,
      ended_at: new Date().toISOString(),
      status: opts.finalStatus ?? 'succeeded',
      total_input_tokens: opts.totalInputTokens ?? this._totalInputTokens,
      total_output_tokens: opts.totalOutputTokens ?? this._totalOutputTokens,
    }
    if (opts.totalCostUsd !== undefined || this._totalCostUsd > 0) {
      ;(end as RunEndEvent & { total_cost_usd?: number }).total_cost_usd = opts.totalCostUsd ?? this._totalCostUsd
    }
    this._transport.enqueue(outcome)
    this._transport.enqueue(end)
    this._outcomeRecorded = true
  }

  complete(): void {
    this.recordOutcome('completed')
  }

  fail(error: unknown): void {
    const errorType = error instanceof Error ? error.name : 'Error'
    this.recordOutcome('failed', {
      success: false,
      finalStatus: 'failed',
      labels: { error_type: errorType },
    })
  }

  get outcomeRecorded(): boolean {
    return this._outcomeRecorded
  }
}

export async function withTask<T>(
  transport: Transport,
  name: string,
  options: TaskOptions,
  defaultMetadata: Record<string, unknown>,
  fn: (task: RunLedgerTask) => Promise<T> | T,
): Promise<T> {
  return withRunLedgerContext(options, async (runId) => {
    const mergedMetadata = { ...defaultMetadata, ...(options.metadata ?? {}), task: name }
    const start: RunStartEvent = {
      event_type: 'run_start',
      run_id: runId,
      started_at: new Date().toISOString(),
      end_user_id: options.endUserId,
      session_id: options.sessionId,
      feature_tag: options.featureTag,
      deployment_version: options.deploymentVersion,
      metadata: mergedMetadata,
      intent: options.intent,
    }
    transport.enqueue(start)
    const task = new RunLedgerTask(transport, runId, name)
    try {
      const result = await fn(task)
      if (!task.outcomeRecorded) task.complete()
      return result
    } catch (error) {
      if (!task.outcomeRecorded) task.fail(error)
      throw error
    }
  })
}
