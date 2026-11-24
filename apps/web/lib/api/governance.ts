/** Guardrails, tools, policies, approvals, tags, audit, privacy and security. */
import type { CapturePolicyResponse, SecurityEventList, ToolRegistryList, ToolRegistryResponse, AuditEventList, RetentionPolicy, RetentionPolicyList, RetentionResourceType, RetentionActionType, RetentionScopeType, PurgeResult, PolicyCheckResponse, PolicyDryRunReport } from '@/types/api'
import { apiFetch } from './client'

// ── Phase 11 — Tool registry helpers ──────────────────────────────────────────

export async function listToolRegistry(apiKey: string): Promise<ToolRegistryList> {
  return apiFetch<ToolRegistryList>('/tools/registry', apiKey)
}

export async function upsertToolRegistry(
  apiKey: string,
  body: { tool_name: string; policy?: string; runtime_enforcement?: boolean; description?: string | null }
): Promise<ToolRegistryResponse> {
  return apiFetch<ToolRegistryResponse>('/tools/registry', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateToolRegistry(
  apiKey: string,
  toolName: string,
  body: { policy?: string; runtime_enforcement?: boolean; description?: string | null }
): Promise<ToolRegistryResponse> {
  return apiFetch<ToolRegistryResponse>(`/tools/registry/${encodeURIComponent(toolName)}`, apiKey, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function deleteToolRegistry(apiKey: string, toolName: string): Promise<void> {
  await apiFetch<void>(`/tools/registry/${encodeURIComponent(toolName)}`, apiKey, {
    method: 'DELETE',
  })
}

export async function getSecurityEvents(apiKey: string): Promise<SecurityEventList> {
  return apiFetch<SecurityEventList>('/tools/security-events', apiKey)
}

export async function upsertCapturePolicy(
  apiKey: string,
  body: { privacy_mode: string; sampled_rate?: number | null }
): Promise<CapturePolicyResponse> {
  return apiFetch<CapturePolicyResponse>('/privacy/capture-policy', apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function getSecuritySettings(apiKey: string): Promise<import('@/types/api').WorkspaceSecuritySettings> {
  return apiFetch<import('@/types/api').WorkspaceSecuritySettings>('/security/settings', apiKey)
}

export async function updateSecuritySettings(
  apiKey: string,
  body: {
    required_metadata_fields?: string[]
    required_metadata_mode?: string
  }
): Promise<import('@/types/api').WorkspaceSecuritySettings> {
  return apiFetch<import('@/types/api').WorkspaceSecuritySettings>('/security/settings', apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function listOidcProviders(apiKey: string): Promise<import('@/types/api').OIDCProviderList> {
  return apiFetch<import('@/types/api').OIDCProviderList>('/security/oidc-providers', apiKey)
}

export async function createOidcProvider(
  apiKey: string,
  body: {
    name: string
    issuer_url: string
    audience?: string | null
    discovery_url?: string | null
    jwks_uri?: string | null
    claim_mappings?: Record<string, unknown>
    is_active?: boolean
  }
): Promise<import('@/types/api').OIDCProviderResponse> {
  return apiFetch<import('@/types/api').OIDCProviderResponse>('/security/oidc-providers', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateOidcProvider(
  apiKey: string,
  providerId: string,
  body: {
    name?: string
    issuer_url?: string
    audience?: string | null
    discovery_url?: string | null
    jwks_uri?: string | null
    claim_mappings?: Record<string, unknown> | null
    is_active?: boolean
  }
): Promise<import('@/types/api').OIDCProviderResponse> {
  return apiFetch<import('@/types/api').OIDCProviderResponse>(`/security/oidc-providers/${providerId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteOidcProvider(apiKey: string, providerId: string): Promise<void> {
  await apiFetch<void>(`/security/oidc-providers/${providerId}`, apiKey, { method: 'DELETE' })
}

export async function listIpAclRules(apiKey: string): Promise<import('@/types/api').IpAclRuleList> {
  return apiFetch<import('@/types/api').IpAclRuleList>('/security/ip-acl', apiKey)
}

export async function createIpAclRule(
  apiKey: string,
  body: {
    scope_type: string
    api_key_id?: string | null
    access_group_id?: string | null
    cidr: string
    action: string
    priority?: number
    description?: string | null
  }
): Promise<import('@/types/api').IpAclRuleResponse> {
  return apiFetch<import('@/types/api').IpAclRuleResponse>('/security/ip-acl', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateIpAclRule(
  apiKey: string,
  ruleId: string,
  body: {
    api_key_id?: string | null
    access_group_id?: string | null
    cidr?: string
    action?: string
    priority?: number
    description?: string | null
  }
): Promise<import('@/types/api').IpAclRuleResponse> {
  return apiFetch<import('@/types/api').IpAclRuleResponse>(`/security/ip-acl/${ruleId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteIpAclRule(apiKey: string, ruleId: string): Promise<void> {
  await apiFetch<void>(`/security/ip-acl/${ruleId}`, apiKey, { method: 'DELETE' })
}

export async function testIpAcl(
  apiKey: string,
  body: { ip: string; api_key_id?: string | null; user_id?: string | null }
): Promise<import('@/types/api').IpAclTestResponse> {
  return apiFetch<import('@/types/api').IpAclTestResponse>('/security/ip-acl/test', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getApiKeyRotationHistory(
  apiKey: string,
  keyId: string
): Promise<import('@/types/api').KeyRotationEventList> {
  return apiFetch<import('@/types/api').KeyRotationEventList>(`/security/api-keys/${keyId}/rotation-history`, apiKey)
}

export async function rotateApiKey(
  apiKey: string,
  keyId: string,
  graceHours = 24
): Promise<import('@/types/api').RotateApiKeyResponse> {
  return apiFetch<import('@/types/api').RotateApiKeyResponse>(`/security/api-keys/${keyId}/rotate`, apiKey, {
    method: 'POST',
    body: JSON.stringify({ grace_hours: graceHours }),
  })
}

// ── Approvals ─────────────────────────────────────────────────────────────────

export async function getApprovalSummary(
  apiKey: string
): Promise<import('@/types/api').ApprovalSummary> {
  return apiFetch<import('@/types/api').ApprovalSummary>('/approvals/summary', apiKey)
}

export async function listApprovals(
  apiKey: string,
  params?: { status?: string; request_type?: string; requested_by?: string; access_group_id?: string; api_key_prefix?: string; limit?: number }
): Promise<import('@/types/api').ApprovalList> {
  const q = new URLSearchParams()
  if (params?.status) q.set('status', params.status)
  if (params?.request_type) q.set('request_type', params.request_type)
  if (params?.requested_by) q.set('requested_by', params.requested_by)
  if (params?.access_group_id) q.set('access_group_id', params.access_group_id)
  if (params?.api_key_prefix) q.set('api_key_prefix', params.api_key_prefix)
  if (params?.limit) q.set('limit', String(params.limit))
  return apiFetch<import('@/types/api').ApprovalList>(
    `/approvals${q.toString() ? '?' + q.toString() : ''}`,
    apiKey
  )
}

export async function createApproval(
  apiKey: string,
  body: { request_type: string; request?: Record<string, unknown>; reason?: string }
): Promise<import('@/types/api').ApprovalResponse> {
  return apiFetch<import('@/types/api').ApprovalResponse>('/approvals', apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function approveApproval(
  apiKey: string,
  id: string,
  note?: string
): Promise<import('@/types/api').ApprovalResponse> {
  return apiFetch<import('@/types/api').ApprovalResponse>(`/approvals/${id}/approve`, apiKey, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ note: note ?? null }),
  })
}

export async function denyApproval(
  apiKey: string,
  id: string,
  note?: string
): Promise<import('@/types/api').ApprovalResponse> {
  return apiFetch<import('@/types/api').ApprovalResponse>(`/approvals/${id}/deny`, apiKey, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ note: note ?? null }),
  })
}

export async function cancelApproval(
  apiKey: string,
  id: string
): Promise<import('@/types/api').ApprovalResponse> {
  return apiFetch<import('@/types/api').ApprovalResponse>(`/approvals/${id}`, apiKey, {
    method: 'DELETE',
  })
}

// ── Phase 13: Auto-Approval Policies ────────────────────────────────────────

export async function listAutoApprovalPolicies(
  apiKey: string
): Promise<import('@/types/api').AutoApprovalPolicyList> {
  return apiFetch<import('@/types/api').AutoApprovalPolicyList>('/approvals/auto-policies', apiKey)
}

export async function createAutoApprovalPolicy(
  apiKey: string,
  body: { request_type: string; condition: string }
): Promise<import('@/types/api').AutoApprovalPolicy> {
  return apiFetch<import('@/types/api').AutoApprovalPolicy>('/approvals/auto-policies', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateAutoApprovalPolicy(
  apiKey: string,
  policyId: string,
  body: { request_type?: string; condition?: string }
): Promise<import('@/types/api').AutoApprovalPolicy> {
  return apiFetch<import('@/types/api').AutoApprovalPolicy>(`/approvals/auto-policies/${policyId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteAutoApprovalPolicy(
  apiKey: string,
  policyId: string
): Promise<void> {
  await apiFetch<void>(`/approvals/auto-policies/${policyId}`, apiKey, { method: 'DELETE' })
}

export async function listAuditEvents(
  apiKey: string,
  params: {
    action?: string
    actor_user_id?: string
    target_type?: string
    target_id?: string
    access_group_id?: string
    api_key_prefix?: string
    limit?: number
    offset?: number
  } = {}
): Promise<AuditEventList> {
  const q = new URLSearchParams()
  if (params.action) q.set('action', params.action)
  if (params.actor_user_id) q.set('actor_user_id', params.actor_user_id)
  if (params.target_type) q.set('target_type', params.target_type)
  if (params.target_id) q.set('target_id', params.target_id)
  if (params.access_group_id) q.set('access_group_id', params.access_group_id)
  if (params.api_key_prefix) q.set('api_key_prefix', params.api_key_prefix)
  q.set('limit', String(params.limit ?? 50))
  q.set('offset', String(params.offset ?? 0))
  return apiFetch<AuditEventList>(`/audit/events?${q.toString()}`, apiKey)
}

export async function getAuditEvent(
  apiKey: string,
  eventId: string
): Promise<import('@/types/api').AuditEvent> {
  return apiFetch<import('@/types/api').AuditEvent>(`/audit/events/${eventId}`, apiKey)
}

export async function listRetentionPolicies(apiKey: string): Promise<RetentionPolicyList> {
  return apiFetch<RetentionPolicyList>('/retention/policies', apiKey)
}

export async function createRetentionPolicy(
  apiKey: string,
  body: {
    resource_type: RetentionResourceType
    action: RetentionActionType
    scope?: RetentionScopeType
    scope_value?: string | null
    max_age_days?: number | null
    is_active?: boolean
  }
): Promise<RetentionPolicy> {
  return apiFetch<RetentionPolicy>('/retention/policies', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateRetentionPolicy(
  apiKey: string,
  policyId: string,
  body: { max_age_days?: number | null; is_active?: boolean; scope_value?: string | null }
): Promise<RetentionPolicy> {
  return apiFetch<RetentionPolicy>(`/retention/policies/${policyId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteRetentionPolicy(apiKey: string, policyId: string): Promise<void> {
  await apiFetch<void>(`/retention/policies/${policyId}`, apiKey, { method: 'DELETE' })
}

export async function purgeRetention(
  apiKey: string,
  body: {
    policy_id?: string | null
    resource_type?: RetentionResourceType | null
    action?: RetentionActionType | null
    scope?: RetentionScopeType
    scope_value?: string | null
    max_age_days?: number | null
    dry_run?: boolean
  }
): Promise<PurgeResult> {
  return apiFetch<PurgeResult>('/retention/purge', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

// ── Phase 13: Policy Dry Run ─────────────────────────────────────────────────

export async function policyDryRun(
  apiKey: string,
  body: {
    end_user_id?: string
    feature_tag?: string
    tool_name?: string
    model_alias?: string
    dry_run: true
  }
): Promise<PolicyCheckResponse> {
  return apiFetch<PolicyCheckResponse>('/policies/check', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getPolicyDryRunReport(
  apiKey: string,
  params?: { from?: string; to?: string; limit?: number }
): Promise<PolicyDryRunReport> {
  const q = new URLSearchParams()
  if (params?.from) q.set('from', params.from)
  if (params?.to) q.set('to', params.to)
  if (params?.limit) q.set('limit', String(params.limit))
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<PolicyDryRunReport>(`/policies/dry-run-report${qs}`, apiKey)
}

export async function promotePolicy(
  apiKey: string,
  body: { policy_type: string; enforce: boolean }
): Promise<{ status: string; message: string }> {
  return apiFetch<{ status: string; message: string }>('/policies/promote', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

// ── Phase 13: Governance Audit Pack ─────────────────────────────────────────

export async function getGovernanceAuditPack(
  apiKey: string,
  params?: { from?: string; to?: string; org_id?: string; workspace_id?: string; user_id?: string; access_group_id?: string; api_key_id?: string }
): Promise<import('@/types/api').GovernanceAuditPack> {
  const q = new URLSearchParams()
  if (params?.from) q.set('from', params.from)
  if (params?.to) q.set('to', params.to)
  if (params?.org_id) q.set('org_id', params.org_id)
  if (params?.workspace_id) q.set('workspace_id', params.workspace_id)
  if (params?.user_id) q.set('user_id', params.user_id)
  if (params?.access_group_id) q.set('access_group_id', params.access_group_id)
  if (params?.api_key_id) q.set('api_key_id', params.api_key_id)
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<import('@/types/api').GovernanceAuditPack>(`/governance/audit-pack${qs}`, apiKey)
}

// -- Phase 14: Guardrails, Content Safety & Policy Engine --

export async function listGuardrailRules(
  apiKey: string,
  params?: { rule_type?: string; status?: string; mode?: string; limit?: number; offset?: number }
): Promise<import('@/types/api').GuardrailRuleList> {
  const q = new URLSearchParams()
  if (params?.rule_type) q.set('rule_type', params.rule_type)
  if (params?.status) q.set('status', params.status)
  if (params?.mode) q.set('mode', params.mode)
  if (params?.limit) q.set('limit', String(params.limit))
  if (params?.offset) q.set('offset', String(params.offset))
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<import('@/types/api').GuardrailRuleList>(`/guardrails${qs}`, apiKey)
}

export async function createGuardrailRule(
  apiKey: string,
  body: import('@/types/api').GuardrailRuleCreate
): Promise<import('@/types/api').GuardrailRuleResponse> {
  return apiFetch<import('@/types/api').GuardrailRuleResponse>('/guardrails', apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function getGuardrailRule(
  apiKey: string,
  id: string
): Promise<import('@/types/api').GuardrailRuleResponse> {
  return apiFetch<import('@/types/api').GuardrailRuleResponse>(`/guardrails/${id}`, apiKey)
}

export async function updateGuardrailRule(
  apiKey: string,
  id: string,
  body: import('@/types/api').GuardrailRuleUpdate
): Promise<import('@/types/api').GuardrailRuleResponse> {
  return apiFetch<import('@/types/api').GuardrailRuleResponse>(`/guardrails/${id}`, apiKey, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function deleteGuardrailRule(apiKey: string, id: string): Promise<void> {
  return apiFetch<void>(`/guardrails/${id}`, apiKey, { method: 'DELETE' })
}

export async function testGuardrailRule(
  apiKey: string,
  id: string,
  body: import('@/types/api').GuardrailTestInput
): Promise<import('@/types/api').GuardrailTestResponse> {
  return apiFetch<import('@/types/api').GuardrailTestResponse>(`/guardrails/${id}/test`, apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function testAllGuardrails(
  apiKey: string,
  body: import('@/types/api').GuardrailTestInput
): Promise<import('@/types/api').GuardrailTestResponse> {
  return apiFetch<import('@/types/api').GuardrailTestResponse>('/guardrails/test', apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function listGuardrailTemplates(
  apiKey: string
): Promise<import('@/types/api').GuardrailTemplate[]> {
  return apiFetch<import('@/types/api').GuardrailTemplate[]>('/guardrails/templates', apiKey)
}

export async function listContentFilters(
  apiKey: string
): Promise<import('@/types/api').ContentFilterListResponse> {
  return apiFetch<import('@/types/api').ContentFilterListResponse>('/guardrails/filters', apiKey)
}

export async function activateContentFilters(
  apiKey: string,
  body: { filters: import('@/types/api').ContentFilterConfig[] }
): Promise<import('@/types/api').ContentFilterListResponse> {
  return apiFetch<import('@/types/api').ContentFilterListResponse>('/guardrails/filters', apiKey, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function getGuardrailStats(
  apiKey: string,
  hours?: number
): Promise<import('@/types/api').GuardrailStats> {
  const qs = hours ? `?hours=${hours}` : ''
  return apiFetch<import('@/types/api').GuardrailStats>(`/guardrails/stats${qs}`, apiKey)
}

export async function listGuardrailEvents(
  apiKey: string,
  params?: {
    decision?: string
    guardrail_name?: string
    mode?: string
    violations_only?: boolean
    false_positive?: boolean
    limit?: number
    offset?: number
  }
): Promise<import('@/types/api').GuardrailEventList> {
  const q = new URLSearchParams()
  if (params?.decision) q.set('decision', params.decision)
  if (params?.guardrail_name) q.set('guardrail_name', params.guardrail_name)
  if (params?.mode) q.set('mode', params.mode)
  if (params?.violations_only !== undefined) q.set('violations_only', String(params.violations_only))
  if (params?.false_positive !== undefined) q.set('false_positive', String(params.false_positive))
  if (params?.limit) q.set('limit', String(params.limit))
  if (params?.offset) q.set('offset', String(params.offset))
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<import('@/types/api').GuardrailEventList>(`/guardrails/events${qs}`, apiKey)
}

export async function listPartnerGuardrails(
  apiKey: string,
  params?: { provider?: string }
): Promise<import('@/types/api').PartnerGuardrailList> {
  const q = new URLSearchParams()
  if (params?.provider) q.set('provider', params.provider)
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<import('@/types/api').PartnerGuardrailList>(`/guardrails/partners${qs}`, apiKey)
}

export async function createPartnerGuardrail(
  apiKey: string,
  body: Record<string, unknown>
): Promise<import('@/types/api').PartnerGuardrailResponse> {
  return apiFetch<import('@/types/api').PartnerGuardrailResponse>('/guardrails/partners', apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function updatePartnerGuardrail(
  apiKey: string,
  id: string,
  body: Record<string, unknown>
): Promise<import('@/types/api').PartnerGuardrailResponse> {
  return apiFetch<import('@/types/api').PartnerGuardrailResponse>(`/guardrails/partners/${id}`, apiKey, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function deletePartnerGuardrail(apiKey: string, id: string): Promise<void> {
  return apiFetch<void>(`/guardrails/partners/${id}`, apiKey, { method: 'DELETE' })
}

export async function healthCheckPartner(
  apiKey: string,
  id: string
): Promise<import('@/types/api').PartnerGuardrailResponse> {
  return apiFetch<import('@/types/api').PartnerGuardrailResponse>(
    `/guardrails/partners/${id}/health`,
    apiKey,
    { method: 'POST' }
  )
}

export async function listGuardrailTestCases(
  apiKey: string,
  params?: { guardrail_rule_id?: string }
): Promise<import('@/types/api').GuardrailTestCaseList> {
  const q = new URLSearchParams()
  if (params?.guardrail_rule_id) q.set('guardrail_rule_id', params.guardrail_rule_id)
  const qs = q.toString() ? `?${q}` : ''
  return apiFetch<import('@/types/api').GuardrailTestCaseList>(`/guardrails/test-cases${qs}`, apiKey)
}

export async function createGuardrailTestCase(
  apiKey: string,
  body: Record<string, unknown>
): Promise<import('@/types/api').GuardrailTestCaseResponse> {
  return apiFetch<import('@/types/api').GuardrailTestCaseResponse>('/guardrails/test-cases', apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function deleteGuardrailTestCase(apiKey: string, id: string): Promise<void> {
  return apiFetch<void>(`/guardrails/test-cases/${id}`, apiKey, { method: 'DELETE' })
}

export async function runGuardrailRegression(
  apiKey: string,
  guardrailId: string
): Promise<import('@/types/api').GuardrailRegressionReport> {
  return apiFetch<import('@/types/api').GuardrailRegressionReport>(
    `/guardrails/${guardrailId}/regression`,
    apiKey,
    { method: 'POST' }
  )
}

export async function submitGuardrailFeedback(
  apiKey: string,
  eventId: string,
  body: import('@/types/api').GuardrailFeedbackInput
): Promise<import('@/types/api').GuardrailEventResponse> {
  return apiFetch<import('@/types/api').GuardrailEventResponse>(
    `/guardrails/events/${eventId}/feedback`,
    apiKey,
    { method: 'POST', body: JSON.stringify(body), headers: { 'Content-Type': 'application/json' } }
  )
}

export async function listGuardrailAlerts(
  apiKey: string,
  params?: { alert_type?: string; status?: string; limit?: number; offset?: number }
): Promise<import('@/types/api').GuardrailAlertList> {
  const sp = new URLSearchParams()
  if (params?.alert_type) sp.set('alert_type', params.alert_type)
  if (params?.status) sp.set('status', params.status)
  if (params?.limit) sp.set('limit', String(params.limit))
  if (params?.offset) sp.set('offset', String(params.offset))
  const qs = sp.toString()
  return apiFetch<import('@/types/api').GuardrailAlertList>(
    `/guardrails/alerts${qs ? `?${qs}` : ''}`,
    apiKey
  )
}

export async function evaluateGuardrailAlerts(
  apiKey: string,
  windowHours?: number,
  baselineHours?: number
): Promise<Record<string, unknown>[]> {
  const sp = new URLSearchParams()
  if (windowHours) sp.set('window_hours', String(windowHours))
  if (baselineHours) sp.set('baseline_hours', String(baselineHours))
  const qs = sp.toString()
  return apiFetch<Record<string, unknown>[]>(
    `/guardrails/alerts/evaluate${qs ? `?${qs}` : ''}`,
    apiKey,
    { method: 'POST' }
  )
}

export async function acknowledgeGuardrailAlert(
  apiKey: string,
  alertId: string
): Promise<import('@/types/api').GuardrailAlertResponse> {
  return apiFetch<import('@/types/api').GuardrailAlertResponse>(
    `/guardrails/alerts/${alertId}/acknowledge`,
    apiKey,
    { method: 'POST' }
  )
}

// ── Projects ─────────────────────────────────────────────────────────────

// ── Team Models ──────────────────────────────────────────────────────────

// Workspace control surfaces

export async function getTags(
  apiKey: string,
  params: { category?: string; include_inactive?: boolean } = {}
): Promise<import('@/types/api').TagListResponse> {
  const qs = new URLSearchParams()
  if (params.category) qs.set('category', params.category)
  if (params.include_inactive) qs.set('include_inactive', 'true')
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').TagListResponse>(`/tags${query}`, apiKey)
}

export async function getTagTree(
  apiKey: string,
  params: { category?: string } = {}
): Promise<import('@/types/api').TagTreeResponse> {
  const qs = new URLSearchParams()
  if (params.category) qs.set('category', params.category)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').TagTreeResponse>(`/tags/tree${query}`, apiKey)
}

export async function getAutoTagRules(
  apiKey: string
): Promise<import('@/types/api').AutoTaggingRuleListResponse> {
  return apiFetch<import('@/types/api').AutoTaggingRuleListResponse>('/tags/auto-rules', apiKey)
}

export async function createTag(
  apiKey: string,
  data: {
    category: string
    key: string
    value: string
    description?: string | null
    parent_tag_id?: string | null
    is_active?: boolean
  }
): Promise<import('@/types/api').TagResponse> {
  return apiFetch<import('@/types/api').TagResponse>('/tags', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTag(
  apiKey: string,
  tagId: string,
  data: Partial<{
    category: string
    key: string
    value: string
    description: string | null
    parent_tag_id: string | null
    is_active: boolean
  }>
): Promise<import('@/types/api').TagResponse> {
  return apiFetch<import('@/types/api').TagResponse>(`/tags/${tagId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteTag(apiKey: string, tagId: string): Promise<void> {
  await apiFetch<void>(`/tags/${tagId}`, apiKey, { method: 'DELETE' })
}

export async function createAutoTagRule(
  apiKey: string,
  data: {
    name: string
    description?: string | null
    match_type: 'equals' | 'contains' | 'regex' | 'prefix' | 'suffix'
    match_field: string
    match_pattern: string
    tag_key: string
    tag_value: string
    priority?: number
    is_active?: boolean
  }
): Promise<import('@/types/api').AutoTaggingRuleResponse> {
  return apiFetch<import('@/types/api').AutoTaggingRuleResponse>('/tags/auto-rules', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateAutoTagRule(
  apiKey: string,
  ruleId: string,
  data: Partial<{
    name: string
    description: string | null
    match_type: 'equals' | 'contains' | 'regex' | 'prefix' | 'suffix'
    match_field: string
    match_pattern: string
    tag_key: string
    tag_value: string
    priority: number
    is_active: boolean
  }>
): Promise<import('@/types/api').AutoTaggingRuleResponse> {
  return apiFetch<import('@/types/api').AutoTaggingRuleResponse>(`/tags/auto-rules/${ruleId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteAutoTagRule(apiKey: string, ruleId: string): Promise<void> {
  await apiFetch<void>(`/tags/auto-rules/${ruleId}`, apiKey, { method: 'DELETE' })
}

export async function simulateAutoTagging(
  apiKey: string,
  data: { fields: Record<string, string> }
): Promise<import('@/types/api').AutoTaggingSimulationResponse> {
  return apiFetch<import('@/types/api').AutoTaggingSimulationResponse>('/tags/auto-rules/simulate', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getSearchTools(
  apiKey: string,
  params: { include_inactive?: boolean } = {}
): Promise<import('@/types/api').SearchToolListResponse> {
  const qs = new URLSearchParams()
  if (params.include_inactive) qs.set('include_inactive', 'true')
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').SearchToolListResponse>(`/search-tools${query}`, apiKey)
}

export async function createSearchTool(
  apiKey: string,
  data: {
    name: string
    description?: string | null
    tool_type: string
    endpoint_url?: string | null
    auth_type?: string | null
    auth_config?: Record<string, unknown>
    rate_limit_rpm?: number | null
    cost_per_query?: number
    is_active?: boolean
    avg_quality_score?: number | null
    config?: Record<string, unknown>
  }
): Promise<import('@/types/api').SearchToolResponse> {
  return apiFetch<import('@/types/api').SearchToolResponse>('/search-tools', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateSearchTool(
  apiKey: string,
  toolId: string,
  data: Partial<{
    name: string
    description: string | null
    tool_type: string
    endpoint_url: string | null
    auth_type: string | null
    auth_config: Record<string, unknown>
    rate_limit_rpm: number | null
    cost_per_query: number
    is_active: boolean
    avg_quality_score: number | null
    config: Record<string, unknown>
  }>
): Promise<import('@/types/api').SearchToolResponse> {
  return apiFetch<import('@/types/api').SearchToolResponse>(`/search-tools/${toolId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteSearchTool(apiKey: string, toolId: string): Promise<void> {
  await apiFetch<void>(`/search-tools/${toolId}`, apiKey, {
    method: 'DELETE',
  })
}

export async function getSearchToolPolicies(
  apiKey: string,
  toolId: string
): Promise<import('@/types/api').SearchToolPolicySummary> {
  return apiFetch<import('@/types/api').SearchToolPolicySummary>(`/search-tools/${toolId}/policies`, apiKey)
}

export async function getToolPolicies(
  apiKey: string,
  params: { tool_name?: string; include_inactive?: boolean } = {}
): Promise<import('@/types/api').ToolPolicyListResponse> {
  const qs = new URLSearchParams()
  if (params.tool_name) qs.set('tool_name', params.tool_name)
  if (params.include_inactive) qs.set('include_inactive', 'true')
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').ToolPolicyListResponse>(`/tool-policies${query}`, apiKey)
}

export async function createToolPolicy(
  apiKey: string,
  data: {
    name: string
    description?: string
    tool_name: string
    action: string
    condition_type?: string
    condition_config?: Record<string, unknown>
    scope_type?: string
    scope_id?: string
    priority?: number
  }
): Promise<import('@/types/api').ToolPolicyResponse> {
  return apiFetch<import('@/types/api').ToolPolicyResponse>('/tool-policies', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateToolPolicy(
  apiKey: string,
  id: string,
  data: Partial<{
    name: string
    description: string
    tool_name: string
    action: string
    condition_type: string | null
    condition_config: Record<string, unknown>
    scope_type: string
    scope_id: string | null
    priority: number
    is_active: boolean
  }>
): Promise<import('@/types/api').ToolPolicyResponse> {
  return apiFetch<import('@/types/api').ToolPolicyResponse>(`/tool-policies/${id}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteToolPolicy(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/tool-policies/${id}`, apiKey, { method: 'DELETE' })
}

export async function simulateToolPolicy(
  apiKey: string,
  data: {
    tool_name: string
    tool_type?: string
    risk_score?: number
    end_user_id?: string
    feature_tag?: string
    context?: Record<string, unknown>
    api_key_id?: string
    access_group_ids?: string[]
    server_id?: string
    arguments?: Record<string, unknown>
  }
): Promise<import('@/types/api').ToolPolicySimulationResponse> {
  return apiFetch<import('@/types/api').ToolPolicySimulationResponse>('/tool-policies/simulate', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getToolPolicyAnalytics(
  apiKey: string,
  limit = 500
): Promise<import('@/types/api').ToolUsageAnalyticsResponse> {
  return apiFetch<import('@/types/api').ToolUsageAnalyticsResponse>(`/tool-policies/analytics?limit=${limit}`, apiKey)
}

/** Policy simulator: replay the last `days` of real tool calls against a draft policy before saving it. */
export async function simulateToolPolicyImpact(
  apiKey: string,
  data: {
    policy?: Record<string, unknown>
    policy_id?: string
    remove?: boolean
    days?: number
  }
): Promise<import('@/types/api').ToolPolicyImpactResponse> {
  return apiFetch<import('@/types/api').ToolPolicyImpactResponse>('/tool-policies/simulate-impact', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
