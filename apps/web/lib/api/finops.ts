/** Budgets, billing, invoices and ledger. */
import type { BudgetBurndown, BudgetSimulateRequest, BudgetSimulateResult, RunawayHold, RunawayHoldList, BillingAdjustment, BillingAdjustmentList, BillingPeriod, BillingPeriodList, BreachList, ChargebackReportList, ChargebackRuleList, ChargebackRuleResponse, Budget, BudgetList, BudgetRollupResponse, LedgerSnapshotList, NotificationList, NotificationDeliveryList, NotificationResponse, NotificationTestResult, LedgerSnapshotResponse, LedgerClosureSummary, LedgerVerifyResult, PeriodBreakdown, ReconciliationResult, SharedCostAllocationResult, SharedCostPolicy, SharedCostPolicyList, UsageSnapshot } from '@/types/api'
import { apiFetch } from './client'

// ── Budget helpers ─────────────────────────────────────────────────────────────

export async function getBudgets(
  apiKey: string,
  params: { scope_type?: string; scope_id?: string; include_inactive?: boolean } = {}
): Promise<BudgetList> {
  const qs = new URLSearchParams()
  if (params.scope_type) qs.set('scope_type', params.scope_type)
  if (params.scope_id) qs.set('scope_id', params.scope_id)
  if (params.include_inactive) qs.set('include_inactive', 'true')
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<BudgetList>(`/budgets${query}`, apiKey)
}

export async function getBudgetRollup(
  apiKey: string,
  scope: 'workspace' | 'org' | 'platform' = 'workspace'
): Promise<BudgetRollupResponse> {
  return apiFetch<BudgetRollupResponse>(`/budgets/rollup?scope=${scope}`, apiKey)
}

export async function createBudget(
  apiKey: string,
  body: {
    scope_type: string
    scope_id?: string | null
    api_key_id?: string | null
    period_type: string
    limit_usd: number
    action: string
    downgrade_to_model?: string | null
  }
): Promise<Budget> {
  return apiFetch<Budget>('/budgets', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getBudget(apiKey: string, id: string): Promise<Budget> {
  return apiFetch<Budget>(`/budgets/${id}`, apiKey)
}

export async function updateBudget(
  apiKey: string,
  id: string,
  body: Partial<{
    scope_type: string
    scope_id: string | null
    api_key_id: string | null
    period_type: string
    limit_usd: number
    action: string
    downgrade_to_model: string | null
    is_active: boolean
  }>
): Promise<Budget> {
  return apiFetch<Budget>(`/budgets/${id}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteBudget(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/budgets/${id}`, apiKey, { method: 'DELETE' })
}

export async function getBudgetBurndown(apiKey: string, id: string): Promise<BudgetBurndown> {
  return apiFetch<BudgetBurndown>(`/budgets/${id}/burndown`, apiKey)
}

/** Replay the last N days of real spend against a candidate budget. */
export async function simulateBudget(
  apiKey: string,
  body: BudgetSimulateRequest
): Promise<BudgetSimulateResult> {
  return apiFetch<BudgetSimulateResult>('/budgets/simulate', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listRunawayHolds(
  apiKey: string,
  activeOnly = false
): Promise<RunawayHoldList> {
  return apiFetch<RunawayHoldList>(
    `/budgets/runaway-holds?limit=100${activeOnly ? '&active_only=true' : ''}`,
    apiKey
  )
}

export async function createRunawayHold(
  apiKey: string,
  body: { subject_type: 'run' | 'session'; subject_id: string; minutes: number; reason?: string }
): Promise<RunawayHold> {
  return apiFetch<RunawayHold>('/budgets/runaway-holds', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function releaseRunawayHold(apiKey: string, id: string): Promise<RunawayHold> {
  return apiFetch<RunawayHold>(`/budgets/runaway-holds/${id}/release`, apiKey, { method: 'POST' })
}

export async function getBudgetBreaches(apiKey: string, id: string): Promise<BreachList> {
  return apiFetch<BreachList>(`/budgets/${id}/breaches`, apiKey)
}

export async function listBudgetNotifications(apiKey: string): Promise<NotificationList> {
  return apiFetch<NotificationList>('/budgets/notifications', apiKey)
}

export async function createBudgetNotification(
  apiKey: string,
  body: { channel: string; destination_url: string; events?: string[] }
): Promise<NotificationResponse> {
  return apiFetch<NotificationResponse>('/budgets/notifications', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateBudgetNotification(
  apiKey: string,
  id: string,
  body: { destination_url?: string; events?: string[]; is_active?: boolean }
): Promise<NotificationResponse> {
  return apiFetch<NotificationResponse>(`/budgets/notifications/${id}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteBudgetNotification(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/budgets/notifications/${id}`, apiKey, { method: 'DELETE' })
}

export async function testBudgetNotification(apiKey: string, id: string): Promise<NotificationTestResult> {
  return apiFetch<NotificationTestResult>(`/budgets/notifications/${id}/test`, apiKey, {
    method: 'POST',
  })
}

export async function listBudgetNotificationDeliveries(
  apiKey: string,
  id: string,
  limit = 20
): Promise<NotificationDeliveryList> {
  return apiFetch<NotificationDeliveryList>(`/budgets/notifications/${id}/deliveries?limit=${limit}`, apiKey)
}

// ── Billing helpers ────────────────────────────────────────────────────────────

export async function getBillingPeriods(
  apiKey: string,
  params: { access_group_id?: string; api_key_id?: string } = {}
): Promise<BillingPeriodList> {
  const qs = new URLSearchParams()
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<BillingPeriodList>(`/billing/periods${query}`, apiKey)
}

export async function getBillingPeriod(apiKey: string, id: string): Promise<BillingPeriod> {
  return apiFetch<BillingPeriod>(`/billing/periods/${id}`, apiKey)
}

export async function createBillingPeriod(
  apiKey: string,
  body: { period_start: string; period_end: string }
): Promise<BillingPeriod> {
  return apiFetch<BillingPeriod>('/billing/periods', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function closeBillingPeriod(apiKey: string, id: string): Promise<UsageSnapshot> {
  return apiFetch<UsageSnapshot>(`/billing/periods/${id}/close`, apiKey, { method: 'POST' })
}

export async function getReconciliation(
  apiKey: string,
  id: string,
  params: { access_group_id?: string; api_key_id?: string } = {}
): Promise<ReconciliationResult> {
  const qs = new URLSearchParams()
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<ReconciliationResult>(`/billing/periods/${id}/reconciliation${query}`, apiKey)
}

export async function getPeriodBreakdown(
  apiKey: string,
  id: string,
  params: { access_group_id?: string; api_key_id?: string } = {}
): Promise<PeriodBreakdown> {
  const qs = new URLSearchParams()
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<PeriodBreakdown>(`/billing/periods/${id}/breakdown${query}`, apiKey)
}

export async function listBillingAdjustments(
  apiKey: string,
  id: string
): Promise<BillingAdjustmentList> {
  return apiFetch<BillingAdjustmentList>(`/billing/periods/${id}/adjustments`, apiKey)
}

export async function createBillingAdjustment(
  apiKey: string,
  id: string,
  body: {
    adjustment_type: 'credit' | 'refund' | 'prepaid_deduction' | 'surcharge'
    amount_usd: string
    description?: string | null
    reference_id?: string | null
  }
): Promise<BillingAdjustment> {
  return apiFetch<BillingAdjustment>(`/billing/periods/${id}/adjustments`, apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateBillingAdjustment(
  apiKey: string,
  periodId: string,
  adjustmentId: string,
  body: {
    adjustment_type?: 'credit' | 'refund' | 'prepaid_deduction' | 'surcharge'
    amount_usd?: string
    description?: string | null
    reference_id?: string | null
  }
): Promise<BillingAdjustment> {
  return apiFetch<BillingAdjustment>(
    `/billing/periods/${periodId}/adjustments/${adjustmentId}`,
    apiKey,
    {
      method: 'PUT',
      body: JSON.stringify(body),
    }
  )
}

export async function deleteBillingAdjustment(
  apiKey: string,
  periodId: string,
  adjustmentId: string
): Promise<void> {
  await apiFetch<void>(`/billing/periods/${periodId}/adjustments/${adjustmentId}`, apiKey, {
    method: 'DELETE',
  })
}

export async function exportPeriodSignedJson(
  apiKey: string,
  id: string,
  params: { access_group_id?: string; api_key_id?: string } = {}
): Promise<object> {
  const query = new URLSearchParams({ format: 'signed_json' })
  if (params.access_group_id) query.set('access_group_id', params.access_group_id)
  if (params.api_key_id) query.set('api_key_id', params.api_key_id)
  return apiFetch<object>(`/billing/periods/${id}/export?${query.toString()}`, apiKey)
}

export async function listSharedCostPolicies(
  apiKey: string,
  activeOnly = false
): Promise<SharedCostPolicyList> {
  const qs = activeOnly ? '?active_only=true' : ''
  return apiFetch<SharedCostPolicyList>(`/billing/shared-cost-policies${qs}`, apiKey)
}

export async function createSharedCostPolicy(
  apiKey: string,
  body: {
    name: string
    description?: string | null
    formula_type: 'equal_split' | 'proportional' | 'fixed_weight'
    allocations: Array<{
      label: string
      cost_center_id?: string | null
      weight?: string | null
      denominator_value?: string | null
    }>
    is_active?: boolean
  }
): Promise<SharedCostPolicy> {
  return apiFetch<SharedCostPolicy>('/billing/shared-cost-policies', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateSharedCostPolicy(
  apiKey: string,
  policyId: string,
  body: {
    name?: string
    description?: string | null
    formula_type?: 'equal_split' | 'proportional' | 'fixed_weight'
    allocations?: Array<{
      label: string
      cost_center_id?: string | null
      weight?: string | null
      denominator_value?: string | null
    }>
    is_active?: boolean
  }
): Promise<SharedCostPolicy> {
  return apiFetch<SharedCostPolicy>(`/billing/shared-cost-policies/${policyId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteSharedCostPolicy(apiKey: string, policyId: string): Promise<void> {
  await apiFetch<void>(`/billing/shared-cost-policies/${policyId}`, apiKey, {
    method: 'DELETE',
  })
}

export async function previewSharedCostAllocation(
  apiKey: string,
  policyId: string,
  poolUsd: string
): Promise<SharedCostAllocationResult> {
  return apiFetch<SharedCostAllocationResult>(
    `/billing/shared-cost-policies/${policyId}/allocate`,
    apiKey,
    {
      method: 'POST',
      body: JSON.stringify({ pool_usd: poolUsd }),
    }
  )
}

export async function listChargebackRules(apiKey: string): Promise<ChargebackRuleList> {
  return apiFetch<ChargebackRuleList>('/billing/chargeback-rules', apiKey)
}

export async function createChargebackRule(
  apiKey: string,
  body: {
    allocation_type: 'direct' | 'shared_weight'
    dimension: string
    dimension_value: string
    weight: string
    cost_center_id: string
    require_approval?: boolean
  }
): Promise<ChargebackRuleResponse> {
  return apiFetch<ChargebackRuleResponse>('/billing/chargeback-rules', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateChargebackRule(
  apiKey: string,
  ruleId: string,
  body: {
    allocation_type?: 'direct' | 'shared_weight'
    dimension?: string
    dimension_value?: string
    weight?: string
    cost_center_id?: string
    status?: 'active' | 'inactive'
  }
): Promise<ChargebackRuleResponse> {
  return apiFetch<ChargebackRuleResponse>(`/billing/chargeback-rules/${ruleId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

// ── Phase 11 — Ledger helpers ──────────────────────────────────────────────────

export async function listLedgerSnapshots(apiKey: string): Promise<LedgerSnapshotList> {
  return apiFetch<LedgerSnapshotList>('/ledger/snapshots', apiKey)
}

export async function generateLedgerSnapshot(apiKey: string): Promise<LedgerSnapshotResponse> {
  return apiFetch<LedgerSnapshotResponse>('/ledger/snapshots/generate', apiKey, { method: 'POST' })
}

export async function verifyLedgerSnapshot(
  apiKey: string,
  snapshotDate: string
): Promise<LedgerVerifyResult> {
  return apiFetch<LedgerVerifyResult>(`/ledger/verify/${snapshotDate}`, apiKey)
}

export async function getLedgerClosureSummary(apiKey: string): Promise<LedgerClosureSummary> {
  return apiFetch<LedgerClosureSummary>('/ledger/closure-summary', apiKey)
}

// ── SaaS / Billing ────────────────────────────────────────────────────────────

export async function getSubscription(apiKey: string): Promise<import('@/types/api').SubscriptionResponse> {
  return apiFetch<import('@/types/api').SubscriptionResponse>('/billing/subscription', apiKey)
}

export async function createCheckout(apiKey: string, plan: string, successUrl: string, cancelUrl: string): Promise<{ checkout_url: string }> {
  return apiFetch<{ checkout_url: string }>('/billing/checkout', apiKey, {
    method: 'POST',
    body: JSON.stringify({ plan, success_url: successUrl, cancel_url: cancelUrl }),
  })
}

// ── Provider Invoice Reconciliation ───────────────────────────────────────────

export async function listInvoices(
  apiKey: string,
  params?: { provider?: string; status?: string }
): Promise<import('@/types/api').InvoiceList> {
  const qs = params ? '?' + new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
  ).toString() : ''
  return apiFetch<import('@/types/api').InvoiceList>(`/invoices${qs}`, apiKey)
}

export async function getInvoiceSummary(
  apiKey: string,
  invoiceId: string
): Promise<import('@/types/api').ReconciliationSummary> {
  return apiFetch<import('@/types/api').ReconciliationSummary>(`/invoices/${invoiceId}`, apiKey)
}

export async function reconcileInvoice(
  apiKey: string,
  invoiceId: string
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/invoices/${invoiceId}/reconcile`, apiKey, {
    method: 'POST',
  })
}

export async function deleteInvoice(apiKey: string, invoiceId: string): Promise<void> {
  await apiFetch<void>(`/invoices/${invoiceId}`, apiKey, { method: 'DELETE' })
}

export async function listInvoiceLines(
  apiKey: string,
  invoiceId: string,
  params?: { match_status?: string; limit?: number; offset?: number }
): Promise<import('@/types/api').InvoiceLineList> {
  const qs = params ? '?' + new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
  ).toString() : ''
  return apiFetch<import('@/types/api').InvoiceLineList>(`/invoices/${invoiceId}/lines${qs}`, apiKey)
}

export async function disputeInvoiceLine(
  apiKey: string,
  invoiceId: string,
  lineId: string,
  note: string
): Promise<import('@/types/api').InvoiceLineResponse> {
  return apiFetch<import('@/types/api').InvoiceLineResponse>(
    `/invoices/${invoiceId}/lines/${lineId}/dispute`,
    apiKey,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note }),
    }
  )
}

// ── Phase 13: Chargeback Rules ───────────────────────────────────────────────

export async function deleteChargebackRule(
  apiKey: string,
  ruleId: string
): Promise<void> {
  await apiFetch<void>(`/billing/chargeback-rules/${ruleId}`, apiKey, { method: 'DELETE' })
}

export async function getChargebackReport(
  apiKey: string,
  params?: { period?: string; dimension?: string; format?: 'json' | 'csv'; access_group_id?: string; api_key_id?: string }
): Promise<ChargebackReportList> {
  const q = new URLSearchParams()
  if (params?.period) q.set('period', params.period)
  if (params?.dimension) q.set('dimension', params.dimension)
  if (params?.access_group_id) q.set('access_group_id', params.access_group_id)
  if (params?.api_key_id) q.set('api_key_id', params.api_key_id)
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<ChargebackReportList>(`/billing/chargeback-report${qs}`, apiKey)
}

export async function createBudgetOverride(
  apiKey: string,
  budgetId: string,
  body: {
    override_limit_usd: number
    starts_at: string
    expires_at: string
    reason?: string
    require_approval?: boolean
  }
): Promise<import('@/types/api').BudgetOverride> {
  return apiFetch<import('@/types/api').BudgetOverride>(`/budgets/${budgetId}/override`, apiKey, { method: 'POST', body: JSON.stringify(body) })
}

export async function listBudgetOverrides(
  apiKey: string,
  budgetId: string
): Promise<import('@/types/api').BudgetOverrideList> {
  return apiFetch<import('@/types/api').BudgetOverrideList>(`/budgets/${budgetId}/overrides`, apiKey)
}

export async function revokeBudgetOverride(
  apiKey: string,
  budgetId: string,
  overrideId: string
): Promise<import('@/types/api').BudgetOverride> {
  return apiFetch<import('@/types/api').BudgetOverride>(`/budgets/${budgetId}/override/${overrideId}/revoke`, apiKey, { method: 'POST' })
}

export async function getBillingSummary(
  apiKey: string,
  months?: number
): Promise<import('@/types/api').BillingSummaryResponse> {
  const qs = months ? `?months=${months}` : ''
  return apiFetch<import('@/types/api').BillingSummaryResponse>(`/budgets/billing-summary${qs}`, apiKey)
}

// ── Billing: period lifecycle, cost centers, cost-center chargeback, shared costs, signing ──

export async function updateBillingPeriod(
  apiKey: string,
  id: string,
  body: { period_start?: string; period_end?: string; currency?: string; exchange_rate_to_usd?: string },
): Promise<import('@/types/api').BillingPeriod> {
  return apiFetch(`/billing/periods/${id}`, apiKey, { method: 'PATCH', body: JSON.stringify(body) })
}

export async function deleteBillingPeriod(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/billing/periods/${id}`, apiKey, { method: 'DELETE' })
}

export async function reopenBillingPeriod(
  apiKey: string,
  id: string,
  reason: string,
): Promise<import('@/types/api').BillingPeriod> {
  return apiFetch(`/billing/periods/${id}/reopen`, apiKey, { method: 'POST', body: JSON.stringify({ reason }) })
}

export async function listCostCenters(apiKey: string, q?: string): Promise<import('@/types/api').CostCenterList> {
  const qs = new URLSearchParams({ limit: '500' })
  if (q) qs.set('q', q)
  return apiFetch(`/billing/cost-centers?${qs}`, apiKey)
}

export async function createCostCenter(
  apiKey: string,
  body: { name: string; code?: string | null; parent_id?: string | null; description?: string | null },
): Promise<import('@/types/api').CostCenter> {
  return apiFetch('/billing/cost-centers', apiKey, { method: 'POST', body: JSON.stringify(body) })
}

export async function updateCostCenter(
  apiKey: string,
  id: string,
  body: { name?: string; code?: string | null; parent_id?: string | null; description?: string | null },
): Promise<import('@/types/api').CostCenter> {
  return apiFetch(`/billing/cost-centers/${id}`, apiKey, { method: 'PUT', body: JSON.stringify(body) })
}

export async function deleteCostCenter(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/billing/cost-centers/${id}`, apiKey, { method: 'DELETE' })
}

export async function getCostCenterReport(
  apiKey: string,
  period?: string,
): Promise<import('@/types/api').CostCenterReport> {
  const qs = period ? `?period=${encodeURIComponent(period)}` : ''
  return apiFetch(`/billing/chargeback-report/cost-centers${qs}`, apiKey)
}

export async function applySharedCostPolicy(
  apiKey: string,
  policyId: string,
  body: { period: string; pool_usd: string },
): Promise<import('@/types/api').CostAllocationList> {
  return apiFetch(`/billing/shared-cost-policies/${policyId}/apply`, apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listCostAllocations(
  apiKey: string,
  params?: { period?: string; policy_id?: string },
): Promise<import('@/types/api').CostAllocationList> {
  const qs = new URLSearchParams()
  if (params?.period) qs.set('period', params.period)
  if (params?.policy_id) qs.set('policy_id', params.policy_id)
  return apiFetch(`/billing/cost-allocations${qs.toString() ? `?${qs}` : ''}`, apiKey)
}

export async function deleteCostAllocation(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/billing/cost-allocations/${id}`, apiKey, { method: 'DELETE' })
}

export async function getBillingSigningKey(apiKey: string): Promise<import('@/types/api').BillingSigningKey> {
  return apiFetch('/billing/signing-key', apiKey)
}

export async function rotateBillingSigningKey(apiKey: string): Promise<import('@/types/api').BillingSigningKey> {
  return apiFetch('/billing/signing-key/rotate', apiKey, { method: 'POST' })
}

export async function verifyBillingSignature(
  apiKey: string,
  body: { payload: Record<string, unknown>; signature: string; signing_key_id: string },
): Promise<{ valid: boolean; signing_key_id: string }> {
  return apiFetch('/billing/verify', apiKey, { method: 'POST', body: JSON.stringify(body) })
}

export async function listBillingWebhooks(
  apiKey: string
): Promise<import('@/types/api').BillingWebhookConfigList> {
  const result = await listBudgetNotifications(apiKey)
  return {
    items: result.items
      .filter((item) => item.channel === 'webhook')
      .map((item) => ({
        id: item.id,
        workspace_id: '',
        url: item.destination_url,
        label: item.channel,
        enabled: item.is_active,
        created_at: item.created_at,
      })),
  }
}

export async function createBillingWebhook(
  apiKey: string,
  body: { url: string; secret: string; label?: string }
): Promise<import('@/types/api').BillingWebhookConfig> {
  const result = await createBudgetNotification(apiKey, {
    channel: 'webhook',
    destination_url: body.url,
    events: ['budget.breach', 'runaway.detected'],
  })
  return {
    id: result.id,
    workspace_id: '',
    url: result.destination_url,
    label: body.label ?? 'webhook',
    enabled: result.is_active,
    created_at: result.created_at,
  }
}

export async function deleteBillingWebhook(apiKey: string, id: string): Promise<void> {
  await deleteBudgetNotification(apiKey, id)
}
