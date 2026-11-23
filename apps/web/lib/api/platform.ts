/** Settings, org, users, admin, auth, API keys, access groups, AI hub, MCP registry, integrations and alerts. */
import type { AlertFiring, AlertHistoryList, AlertRule, AlertRuleList, AdminWorkspaceResponse, ApiKeyCreateResponse, ApiKeyResponse, CapturePolicyScope, RetentionPreview, PiiTestResult, PlatformWebhookDefaults, PlatformWebhookDefaultsTestResult, ProviderPricingResponse, SlackTestResponse, TenantResponse, TenantStatus, EmailPreference, EmailLogList, OrgEmailFeatureStatus, OpsFeatureStatus, OpsFeatureFlagsResponse, OpsPolicyEvaluation, OpsQueueStatus, OpsStorageStatus, BackupRun, BackupRunList, BackupActionResult, BackupTargetConfig, BackupSnapshotList, OnboardingStatus } from '@/types/api'
import type { WarehouseDestination, WarehouseDestinationList, WarehouseDestinationCreate, WarehouseDestinationUpdate, ConnectionTestResult, ExportJob, ExportJobList } from '@/types/api'
import type { KafkaExportConfig, KafkaExportConfigList, KafkaExportDeliveryList, KafkaTestResult } from '@/types/api'
import { apiFetch, adminFetch, TimeWindow, _analyticsQs, OrgUser, HubAccessRequestResult, SessionKey, PendingInvitation } from './client'

export async function getPlatformWebhookDefaults(apiKey: string): Promise<PlatformWebhookDefaults> {
  return apiFetch<PlatformWebhookDefaults>('/settings/webhooks/defaults', apiKey)
}

export async function updatePlatformWebhookDefaults(
  apiKey: string,
  body: { generic_webhook_url?: string | null; slack_webhook_url?: string | null; events: string[] }
): Promise<PlatformWebhookDefaults> {
  return apiFetch<PlatformWebhookDefaults>('/settings/webhooks/defaults', apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function testPlatformWebhookDefaults(apiKey: string): Promise<PlatformWebhookDefaultsTestResult> {
  return apiFetch<PlatformWebhookDefaultsTestResult>('/settings/webhooks/defaults/test', apiKey, {
    method: 'POST',
  })
}

// ── Phase 13 — Data Capture Policy Studio helpers ──────────────────────────────

export async function getRetentionPreview(
  apiKey: string,
  privacyMode: string
): Promise<RetentionPreview> {
  return apiFetch<RetentionPreview>(`/settings/capture-policy/retention-preview?privacy_mode=${encodeURIComponent(privacyMode)}`, apiKey)
}

export async function testPiiRedaction(
  apiKey: string,
  text: string
): Promise<PiiTestResult> {
  return apiFetch<PiiTestResult>('/settings/capture-policy/test-pii', apiKey, {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
}

export async function listCapturePolicyScopes(
  apiKey: string
): Promise<{ items: CapturePolicyScope[] }> {
  return apiFetch<{ items: CapturePolicyScope[] }>('/settings/capture-policy/scopes', apiKey)
}

export async function upsertCapturePolicyScope(
  apiKey: string,
  scope: { scope_type: string; scope_id: string; privacy_mode: string; sampled_rate: number | null }
): Promise<CapturePolicyScope> {
  return apiFetch<CapturePolicyScope>('/settings/capture-policy/scopes', apiKey, {
    method: 'PUT',
    body: JSON.stringify(scope),
  })
}

export async function deleteCapturePolicyScope(
  apiKey: string,
  scopeType: string,
  scopeId: string
): Promise<void> {
  const query = new URLSearchParams({ scope_type: scopeType, scope_id: scopeId }).toString()
  await apiFetch<void>(`/settings/capture-policy/scopes?${query}`, apiKey, {
    method: 'DELETE',
  })
}

// ── Phase 12 — Settings API key helpers ────────────────────────────────────────

export async function listApiKeys(apiKey: string): Promise<ApiKeyResponse[]> {
  return apiFetch<ApiKeyResponse[]>('/settings/api-keys', apiKey)
}

export async function createApiKey(
  apiKey: string,
  body: { name?: string | null; workspace_id?: string; scopes?: string[]; ownership_type?: string; owner_reference?: string | null; expires_at?: string | null }
): Promise<ApiKeyCreateResponse> {
  return apiFetch<ApiKeyCreateResponse>('/settings/api-keys', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getApiKeyDetail(apiKey: string, keyId: string): Promise<ApiKeyResponse> {
  return apiFetch<ApiKeyResponse>(`/settings/api-keys/${keyId}`, apiKey)
}

export async function updateApiKey(
  apiKey: string,
  keyId: string,
  body: import('@/types/api').ApiKeyUpdateRequest
): Promise<ApiKeyResponse> {
  return apiFetch<ApiKeyResponse>(`/settings/api-keys/${keyId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

// Workspaces in the caller's org (org-admin) — used to pick where a key is minted.
export async function listOrgWorkspaces(
  apiKey: string
): Promise<{ id: string; name: string }[]> {
  return apiFetch<{ id: string; name: string }[]>('/org/workspaces', apiKey)
}

export async function listOrgUsers(apiKey: string): Promise<OrgUser[]> {
  return apiFetch<OrgUser[]>('/users/all', apiKey)
}

export async function createOrgUser(
  apiKey: string,
  body: { email: string; full_name?: string | null; temporary_password?: string | null; skip_verification?: boolean }
): Promise<OrgUser> {
  return apiFetch<OrgUser>('/users', apiKey, { method: 'POST', body: JSON.stringify(body) })
}

export async function updateOrgUser(
  apiKey: string,
  userId: string,
  body: { full_name?: string | null; password?: string; is_active?: boolean; email_verified?: boolean }
): Promise<OrgUser> {
  return apiFetch<OrgUser>(`/users/${userId}`, apiKey, { method: 'PUT', body: JSON.stringify(body) })
}

export async function getUserFinance(apiKey: string, userId: string): Promise<import('@/types/api').UserFinanceSummary> {
  return apiFetch<import('@/types/api').UserFinanceSummary>(`/users/${userId}/finance`, apiKey)
}

export async function getUserGovernance(apiKey: string, userId: string): Promise<import('@/types/api').UserGovernanceSummary> {
  return apiFetch<import('@/types/api').UserGovernanceSummary>(`/users/${userId}/governance`, apiKey)
}

// Platform-admin: create a new organization (adds you as its org admin).
export async function createOrganization(
  apiKey: string,
  body: {
    name: string
    admin_email: string
    admin_password?: string | null
    admin_full_name?: string | null
    skip_verification?: boolean
  }
): Promise<{ id: string; name: string; temporary_password?: string | null }> {
  return apiFetch<{ id: string; name: string; temporary_password?: string | null }>('/org/tenants', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listPlatformOrganizations(apiKey: string): Promise<TenantResponse[]> {
  return apiFetch<TenantResponse[]>('/org/tenants', apiKey)
}

export async function updatePlatformOrganization(
  apiKey: string,
  tenantId: string,
  body: { name?: string; plan?: string; status?: TenantStatus }
): Promise<TenantResponse> {
  return apiFetch<TenantResponse>(`/org/tenants/${tenantId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deletePlatformOrganization(
  apiKey: string,
  tenantId: string,
  confirmation: string
): Promise<void> {
  await apiFetch<void>(`/org/tenants/${tenantId}`, apiKey, {
    method: 'DELETE',
    body: JSON.stringify({ confirmation }),
  })
}

export async function revokeApiKey(apiKey: string, keyId: string): Promise<void> {
  await apiFetch<void>(`/settings/api-keys/${keyId}`, apiKey, { method: 'DELETE' })
}

export async function testSlackWebhook(
  apiKey: string,
  webhookUrl: string
): Promise<SlackTestResponse> {
  return apiFetch<SlackTestResponse>('/integrations/slack/test', apiKey, {
    method: 'POST',
    body: JSON.stringify({ webhook_url: webhookUrl }),
  })
}

// ── Admin helpers (X-Admin-Secret) ────────────────────────────────────────────

export async function listTenants(adminSecret: string): Promise<TenantResponse[]> {
  return adminFetch<TenantResponse[]>('/admin/tenants', adminSecret)
}

export async function createTenant(
  adminSecret: string,
  body: { slug: string; name: string; plan?: string }
): Promise<TenantResponse> {
  return adminFetch<TenantResponse>('/admin/tenants', adminSecret, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listAdminWorkspaces(
  adminSecret: string,
  tenantId: string
): Promise<AdminWorkspaceResponse[]> {
  return adminFetch<AdminWorkspaceResponse[]>(`/admin/tenants/${tenantId}/workspaces`, adminSecret)
}

export async function createAdminWorkspace(
  adminSecret: string,
  body: { tenant_id: string; name: string }
): Promise<AdminWorkspaceResponse> {
  return adminFetch<AdminWorkspaceResponse>('/admin/workspaces', adminSecret, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function createGlobalPricing(
  adminSecret: string,
  body: {
    provider: string
    model: string
    input_cost_per_1m: string
    output_cost_per_1m: string
    cached_input_cost_per_1m?: string | null
  }
): Promise<ProviderPricingResponse> {
  return adminFetch<ProviderPricingResponse>('/admin/global-pricing', adminSecret, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateGlobalPricing(
  adminSecret: string,
  pricingId: string,
  body: {
    input_cost_per_1m?: string
    output_cost_per_1m?: string
    cached_input_cost_per_1m?: string | null
  }
): Promise<ProviderPricingResponse> {
  return adminFetch<ProviderPricingResponse>(`/admin/global-pricing/${pricingId}`, adminSecret, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteGlobalPricing(adminSecret: string, pricingId: string): Promise<void> {
  await adminFetch<void>(`/admin/global-pricing/${pricingId}`, adminSecret, { method: 'DELETE' })
}

// ── Phase 21A — Alert Rules ────────────────────────────────────────────────────

export async function listAlertRules(
  apiKey: string,
  includeInactive = false
): Promise<AlertRuleList> {
  const qs = includeInactive ? '?include_inactive=true' : ''
  return apiFetch<AlertRuleList>(`/alerts/rules${qs}`, apiKey)
}

export async function createAlertRule(
  apiKey: string,
  body: {
    name: string
    metric: string
    operator: string
    threshold: number
    window_minutes?: number
    channel_id?: string | null
    email_enabled?: boolean
  }
): Promise<AlertRule> {
  return apiFetch<AlertRule>('/alerts/rules', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateAlertRule(
  apiKey: string,
  ruleId: string,
  body: {
    name?: string
    metric?: string
    operator?: string
    threshold?: number
    window_minutes?: number
    is_active?: boolean
    channel_id?: string | null
    email_enabled?: boolean
  }
): Promise<AlertRule> {
  return apiFetch<AlertRule>(`/alerts/rules/${ruleId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteAlertRule(apiKey: string, ruleId: string): Promise<void> {
  await apiFetch<void>(`/alerts/rules/${ruleId}`, apiKey, { method: 'DELETE' })
}

export async function listAlertHistory(
  apiKey: string,
  limit = 50
): Promise<AlertHistoryList> {
  return apiFetch<AlertHistoryList>(`/alerts/history?limit=${limit}`, apiKey)
}

// suppress unused import warnings for AlertFiring
export type { AlertFiring }

// ── Org Dashboard ─────────────────────────────────────────────────────────────

export async function getOrgDashboard(
  apiKey: string,
  window: TimeWindow = {},
): Promise<import('@/types/api').OrgDashboard> {
  return apiFetch<import('@/types/api').OrgDashboard>(
    `/org/dashboard${_analyticsQs(window)}`,
    apiKey,
  )
}

export async function getOrgFinance(
  apiKey: string,
): Promise<import('@/types/api').OrgFinanceSummary> {
  return apiFetch<import('@/types/api').OrgFinanceSummary>('/org/finance', apiKey)
}

export async function getOrgRuntime(
  apiKey: string,
): Promise<import('@/types/api').OrgRuntimeSummary> {
  return apiFetch<import('@/types/api').OrgRuntimeSummary>('/org/runtime', apiKey)
}

export async function getOrgObserve(
  apiKey: string,
): Promise<import('@/types/api').OrgObserveSummary> {
  return apiFetch<import('@/types/api').OrgObserveSummary>('/org/observe', apiKey)
}

export async function getOrgGovernance(
  apiKey: string,
): Promise<import('@/types/api').OrgGovernanceSummary> {
  return apiFetch<import('@/types/api').OrgGovernanceSummary>('/org/governance', apiKey)
}

// ── Phase 28: Warehouse Export ────────────────────────────────────────────────
export async function listWarehouseDestinations(
  apiKey: string,
  includeInactive = false
): Promise<WarehouseDestinationList> {
  const qs = includeInactive ? '?include_inactive=true' : ''
  return apiFetch<WarehouseDestinationList>(`/warehouse/destinations${qs}`, apiKey)
}

export async function createWarehouseDestination(
  apiKey: string,
  body: WarehouseDestinationCreate
): Promise<WarehouseDestination> {
  return apiFetch<WarehouseDestination>('/warehouse/destinations', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateWarehouseDestination(
  apiKey: string,
  id: string,
  body: WarehouseDestinationUpdate
): Promise<WarehouseDestination> {
  return apiFetch<WarehouseDestination>(`/warehouse/destinations/${id}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteWarehouseDestination(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/warehouse/destinations/${id}`, apiKey, { method: 'DELETE' })
}

export async function testWarehouseDestination(
  apiKey: string,
  id: string
): Promise<ConnectionTestResult> {
  return apiFetch<ConnectionTestResult>(`/warehouse/destinations/${id}/test`, apiKey, {
    method: 'POST',
  })
}

export async function listExportJobs(
  apiKey: string,
  destinationId?: string
): Promise<ExportJobList> {
  const qs = destinationId ? `?destination_id=${destinationId}` : ''
  return apiFetch<ExportJobList>(`/warehouse/jobs${qs}`, apiKey)
}

export async function triggerExportJob(
  apiKey: string,
  body: { destination_id: string; export_date?: string; resources?: string[] }
): Promise<ExportJob> {
  return apiFetch<ExportJob>('/warehouse/jobs', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getExportJob(apiKey: string, jobId: string): Promise<ExportJob> {
  return apiFetch<ExportJob>(`/warehouse/jobs/${jobId}`, apiKey)
}

// ── Email Preferences ──────────────────────────────────────────────────────────

export async function getEmailPreferences(apiKey: string): Promise<EmailPreference> {
  return apiFetch<EmailPreference>('/settings/email/preferences', apiKey)
}

export async function updateEmailPreferences(
  apiKey: string,
  data: Partial<EmailPreference>
): Promise<EmailPreference> {
  return apiFetch<EmailPreference>('/settings/email/preferences', apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function testEmailSend(
  apiKey: string
): Promise<{ ok: boolean; error: string | null }> {
  return apiFetch<{ ok: boolean; error: string | null }>('/settings/email/test', apiKey, {
    method: 'POST',
  })
}

export async function getEmailLog(apiKey: string): Promise<EmailLogList> {
  return apiFetch<EmailLogList>('/settings/email/log', apiKey)
}

export async function getBackupHistory(apiKey: string, limit = 20): Promise<BackupRunList> {
  return apiFetch<BackupRunList>(`/settings/backups/history?limit=${limit}`, apiKey)
}

export async function getBackupConfig(apiKey: string): Promise<BackupTargetConfig | null> {
  return apiFetch<BackupTargetConfig | null>('/settings/backups/config', apiKey)
}

export async function updateBackupConfig(
  apiKey: string,
  data: {
    provider: 's3'
    bucket: string
    prefix?: string | null
    region?: string | null
    endpoint_url?: string | null
    access_key_id?: string | null
    secret_access_key?: string | null
    force_path_style?: boolean
    schedule_enabled?: boolean
    cadence?: 'daily' | 'weekly' | 'monthly'
    run_hour_utc?: number
    retention_days?: number
    include_memory_db?: boolean
    include_qdrant?: boolean
    include_kuzu?: boolean
    include_skills?: boolean
    encryption_mode?: 'none' | 'server_side'
  },
): Promise<BackupTargetConfig> {
  return apiFetch<BackupTargetConfig>('/settings/backups/config', apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function getBackupSnapshots(apiKey: string, limit = 20): Promise<BackupSnapshotList> {
  return apiFetch<BackupSnapshotList>(`/settings/backups/snapshots?limit=${limit}`, apiKey)
}

export async function runBackupNow(apiKey: string): Promise<BackupRun> {
  return apiFetch<BackupRun>('/settings/backups/run', apiKey, {
    method: 'POST',
  })
}

export async function testBackupConnection(apiKey: string): Promise<BackupActionResult> {
  return apiFetch<BackupActionResult>('/settings/backups/test', apiKey, {
    method: 'POST',
  })
}

export async function runRestoreDrill(apiKey: string): Promise<BackupRun> {
  return apiFetch<BackupRun>('/settings/backups/restore-drill', apiKey, {
    method: 'POST',
  })
}

export async function getBackupStatus(apiKey: string): Promise<BackupActionResult> {
  return apiFetch<BackupActionResult>('/settings/backups/status', apiKey)
}

export async function testEmailReport(apiKey: string): Promise<{ ok: boolean; recipient?: string; error?: string }> {
  return apiFetch<{ ok: boolean; recipient?: string; error?: string }>('/settings/email/test-report', apiKey, {
    method: 'POST',
  })
}

export async function getOrgEmailFeatureStatus(apiKey: string): Promise<OrgEmailFeatureStatus> {
  return apiFetch<OrgEmailFeatureStatus>('/settings/email/status', apiKey)
}

export async function getOpsFeatureStatus(apiKey: string): Promise<OpsFeatureStatus> {
  return apiFetch<OpsFeatureStatus>('/settings/ops/status', apiKey)
}

export async function getOpsQueueStatus(apiKey: string): Promise<OpsQueueStatus> {
  return apiFetch<OpsQueueStatus>('/settings/ops/queues', apiKey)
}

export async function getOpsStorageStatus(apiKey: string): Promise<OpsStorageStatus> {
  return apiFetch<OpsStorageStatus>('/settings/ops/storage', apiKey)
}

export async function getOpsFeatureFlags(apiKey: string): Promise<OpsFeatureFlagsResponse> {
  return apiFetch<OpsFeatureFlagsResponse>('/settings/ops/feature-flags', apiKey)
}

export async function getOpsPolicyEvaluation(apiKey: string): Promise<OpsPolicyEvaluation> {
  return apiFetch<OpsPolicyEvaluation>('/settings/ops/policy-evaluation', apiKey)
}

// ── Kafka Export ───────────────────────────────────────────────────────────────

export async function listKafkaExportConfigs(apiKey: string): Promise<KafkaExportConfigList> {
  return apiFetch<KafkaExportConfigList>('/integrations/kafka/configs', apiKey)
}

export async function createKafkaExportConfig(
  apiKey: string,
  data: {
    label: string
    bootstrap_servers: string
    topic_prefix: string
    security_protocol: string
    sasl_mechanism?: string | null
    sasl_username?: string | null
    sasl_password?: string | null
    ssl_ca_cert?: string | null
    single_topic_mode?: boolean
    single_topic_name?: string | null
    dead_letter_topic?: string | null
    redaction_mode?: 'none' | 'metadata_only'
    max_retries?: number
    retry_backoff_seconds?: number
    event_types: string[]
  }
): Promise<KafkaExportConfig> {
  return apiFetch<KafkaExportConfig>('/integrations/kafka/configs', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateKafkaExportConfig(
  apiKey: string,
  configId: string,
  data: Partial<{
    label: string
    bootstrap_servers: string
    topic_prefix: string
    security_protocol: string
    sasl_mechanism: string | null
    sasl_username: string | null
    sasl_password: string | null
    ssl_ca_cert: string | null
    single_topic_mode: boolean
    single_topic_name: string | null
    dead_letter_topic: string | null
    redaction_mode: 'none' | 'metadata_only'
    max_retries: number
    retry_backoff_seconds: number
    event_types: string[]
    enabled: boolean
  }>
): Promise<KafkaExportConfig> {
  return apiFetch<KafkaExportConfig>(`/integrations/kafka/configs/${configId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteKafkaExportConfig(apiKey: string, configId: string): Promise<void> {
  return apiFetch<void>(`/integrations/kafka/configs/${configId}`, apiKey, { method: 'DELETE' })
}

export async function testKafkaExportConfig(
  apiKey: string,
  configId: string
): Promise<KafkaTestResult> {
  return apiFetch<KafkaTestResult>(`/integrations/kafka/configs/${configId}/test`, apiKey, {
    method: 'POST',
  })
}

export async function listKafkaExportDeliveries(
  apiKey: string,
  configId: string,
  limit = 20
): Promise<KafkaExportDeliveryList> {
  return apiFetch<KafkaExportDeliveryList>(
    `/integrations/kafka/configs/${configId}/deliveries?limit=${limit}`,
    apiKey
  )
}

export async function retryKafkaExportDelivery(
  apiKey: string,
  configId: string,
  deliveryId: string
): Promise<import('@/types/api').KafkaExportDelivery> {
  return apiFetch<import('@/types/api').KafkaExportDelivery>(
    `/integrations/kafka/configs/${configId}/deliveries/${deliveryId}/retry`,
    apiKey,
    { method: 'POST' }
  )
}

// ── Phase 13: Onboarding & Demo ──────────────────────────────────────────────

export async function getOnboardingStatus(apiKey: string): Promise<OnboardingStatus> {
  return apiFetch<OnboardingStatus>('/settings/onboarding-status', apiKey)
}

export async function triggerDemoSeed(
  apiKey: string,
  profile: 'full' | 'quick' = 'full'
): Promise<import('@/types/api').DemoModeTriggerResponse> {
  return apiFetch<import('@/types/api').DemoModeTriggerResponse>(`/settings/demo-seed?profile=${profile}`, apiKey, {
    method: 'POST',
  })
}

export async function getDemoModeStatus(
  apiKey: string
): Promise<import('@/types/api').DemoModeStatus> {
  return apiFetch<import('@/types/api').DemoModeStatus>('/settings/demo-status', apiKey)
}

export async function triggerDemoReset(
  apiKey: string
): Promise<import('@/types/api').DemoModeTriggerResponse> {
  return apiFetch<import('@/types/api').DemoModeTriggerResponse>('/settings/demo-reset', apiKey, {
    method: 'POST',
  })
}


export async function registerMcpServer(
  apiKey: string,
  data: { name: string; transport: string; url?: string; command?: string; args?: string[]; env?: Record<string, string>; auth_type?: string; auth_config?: Record<string, unknown>; description?: string }
): Promise<import('@/types/api').McpServerResponse> {
  return apiFetch<import('@/types/api').McpServerResponse>('/mcp-registry', apiKey, { method: 'POST', body: JSON.stringify(data) })
}

export async function listMcpServers(apiKey: string, includeInactive = false): Promise<import('@/types/api').McpServerList> {
  const qs = includeInactive ? '?include_inactive=true' : ''
  return apiFetch<import('@/types/api').McpServerList>(`/mcp-registry${qs}`, apiKey)
}

export async function getMcpServer(apiKey: string, id: string): Promise<import('@/types/api').McpServerResponse> {
  return apiFetch<import('@/types/api').McpServerResponse>(`/mcp-registry/${id}`, apiKey)
}

export async function updateMcpServer(
  apiKey: string,
  id: string,
  data: {
    name?: string
    description?: string
    transport?: string
    url?: string
    command?: string
    args?: string[]
    env?: Record<string, string>
    auth_type?: string
    auth_config?: Record<string, unknown>
    is_active?: boolean
  }
): Promise<import('@/types/api').McpServerResponse> {
  return apiFetch<import('@/types/api').McpServerResponse>(`/mcp-registry/${id}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function seedDefaultMcpServers(apiKey: string): Promise<{ status: string; servers_added: number; total: number }> {
  return apiFetch<{ status: string; servers_added: number; total: number }>('/mcp-registry/seed-defaults', apiKey, { method: 'POST' })
}

export async function deleteMcpServer(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/mcp-registry/${id}`, apiKey, { method: 'DELETE' })
}

export async function listMcpTools(apiKey: string): Promise<import('@/types/api').McpToolListResponse> {
  return apiFetch<import('@/types/api').McpToolListResponse>('/mcp-registry/tools', apiKey)
}

export async function callMcpTool(apiKey: string, data: { server_id: string; tool_name: string; arguments?: Record<string, unknown> }): Promise<import('@/types/api').McpToolCallResponse> {
  return apiFetch<import('@/types/api').McpToolCallResponse>('/mcp-registry/tools/call', apiKey, { method: 'POST', body: JSON.stringify(data) })
}

export async function listMcpToolCalls(apiKey: string, limit = 50): Promise<import('@/types/api').McpToolCallList> {
  return apiFetch<import('@/types/api').McpToolCallList>(`/mcp-registry/tool-calls?limit=${limit}`, apiKey)
}

export async function syncHubProvider(
  apiKey: string,
  data: { provider: string; token?: string; endpoint_url?: string }
): Promise<import('@/types/api').HubProviderSyncResponse> {
  return apiFetch<import('@/types/api').HubProviderSyncResponse>('/hub/sync-provider', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function grantMcpPermission(apiKey: string, data: { mcp_server_id: string; scope_type: string; scope_id?: string; allowed_tools: string[] }): Promise<import('@/types/api').McpPermissionResponse> {
  return apiFetch<import('@/types/api').McpPermissionResponse>('/mcp-registry/permissions', apiKey, { method: 'POST', body: JSON.stringify(data) })
}

export async function listMcpPermissions(apiKey: string): Promise<import('@/types/api').McpPermissionList> {
  return apiFetch<import('@/types/api').McpPermissionList>('/mcp-registry/permissions', apiKey)
}

export async function revokeMcpPermission(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/mcp-registry/permissions/${id}`, apiKey, { method: 'DELETE' })
}

// ── AI Hub ───────────────────────────────────────────────────────────────

export async function addHubModel(
  apiKey: string,
  data: { name: string; provider: string; description?: string; capabilities?: string[]; context_window?: number; input_cost_per_1k?: number; output_cost_per_1k?: number; tags?: string[]; is_featured?: boolean; is_public?: boolean }
): Promise<import('@/types/api').HubModelResponse> {
  return apiFetch<import('@/types/api').HubModelResponse>('/hub/models', apiKey, { method: 'POST', body: JSON.stringify(data) })
}

export async function listHubModels(apiKey: string, params: { featured_only?: boolean; provider?: string; tag?: string } = {}): Promise<import('@/types/api').HubModelList> {
  const qs = new URLSearchParams()
  if (params.featured_only) qs.set('featured_only', 'true')
  if (params.provider) qs.set('provider', params.provider)
  if (params.tag) qs.set('tag', params.tag)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').HubModelList>(`/hub/models${query}`, apiKey)
}

export async function getHubModel(apiKey: string, id: string): Promise<import('@/types/api').HubModelResponse> {
  return apiFetch<import('@/types/api').HubModelResponse>(`/hub/models/${id}`, apiKey)
}

export async function updateHubModel(apiKey: string, id: string, data: Record<string, unknown>): Promise<import('@/types/api').HubModelResponse> {
  return apiFetch<import('@/types/api').HubModelResponse>(`/hub/models/${id}`, apiKey, { method: 'PUT', body: JSON.stringify(data) })
}

export async function deleteHubModel(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/hub/models/${id}`, apiKey, { method: 'DELETE' })
}

export async function requestHubAccess(apiKey: string, id: string): Promise<HubAccessRequestResult> {
  return apiFetch<HubAccessRequestResult>(`/hub/models/${id}/request-access`, apiKey, { method: 'POST' })
}

export async function getHubModelGovernance(apiKey: string, modelId: string): Promise<import('@/types/api').HubModelGovernanceStatus> {
  return apiFetch<import('@/types/api').HubModelGovernanceStatus>(`/hub/models/${modelId}/governance`, apiKey)
}

export async function getHubOrgSummary(apiKey: string): Promise<import('@/types/api').HubOrgSummary> {
  return apiFetch<import('@/types/api').HubOrgSummary>('/hub/org-summary', apiKey)
}

export async function getAccessGroups(
  apiKey: string,
  params: { include_inactive?: boolean } = {}
): Promise<import('@/types/api').AccessGroupListResponse> {
  const qs = new URLSearchParams()
  if (params.include_inactive) qs.set('include_inactive', 'true')
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').AccessGroupListResponse>(`/access-groups${query}`, apiKey)
}

export async function getAccessGroupMembers(
  apiKey: string,
  groupId: string
): Promise<import('@/types/api').AccessGroupMemberListResponse> {
  return apiFetch<import('@/types/api').AccessGroupMemberListResponse>(`/access-groups/${groupId}/members`, apiKey)
}

export async function getAccessGroupDashboard(
  apiKey: string,
  groupId?: string
): Promise<import('@/types/api').AccessGroupDashboardResponse> {
  const query = groupId ? `?group_id=${encodeURIComponent(groupId)}` : ''
  return apiFetch<import('@/types/api').AccessGroupDashboardResponse>(`/access-groups/dashboard${query}`, apiKey)
}

export async function createAccessGroup(
  apiKey: string,
  data: {
    name: string
    description?: string
    guardrail_profile?: string
    is_active?: boolean
    permissions?: Record<string, any>
  }
): Promise<import('@/types/api').AccessGroupResponse> {
  return apiFetch<import('@/types/api').AccessGroupResponse>('/access-groups', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateAccessGroup(
  apiKey: string,
  groupId: string,
  data: {
    name?: string
    description?: string
    guardrail_profile?: string
    is_active?: boolean
    permissions?: Record<string, any>
  }
): Promise<import('@/types/api').AccessGroupResponse> {
  return apiFetch<import('@/types/api').AccessGroupResponse>(`/access-groups/${groupId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteAccessGroup(
  apiKey: string,
  groupId: string
): Promise<void> {
  await apiFetch(`/access-groups/${groupId}`, apiKey, {
    method: 'DELETE',
  })
}

export async function addAccessGroupMember(
  apiKey: string,
  groupId: string,
  data: { user_id: string; role?: string }
): Promise<import('@/types/api').AccessGroupMemberResponse> {
  return apiFetch<import('@/types/api').AccessGroupMemberResponse>(`/access-groups/${groupId}/members`, apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function removeAccessGroupMember(
  apiKey: string,
  groupId: string,
  userId: string
): Promise<void> {
  await apiFetch(`/access-groups/${groupId}/members/${userId}`, apiKey, {
    method: 'DELETE',
  })
}

export async function getMySessions(apiKey: string): Promise<SessionKey[]> {
  return apiFetch<SessionKey[]>('/auth/sessions', apiKey)
}

export async function revokeMySession(apiKey: string, keyId: string): Promise<void> {
  return apiFetch<void>(`/auth/sessions/${keyId}`, apiKey, { method: 'DELETE' })
}

export async function changeMyPassword(
  apiKey: string,
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  await apiFetch('/users/me', apiKey, {
    method: 'PUT',
    body: JSON.stringify({ current_password: currentPassword, password: newPassword }),
  })
}

export async function getMyInvitations(apiKey: string): Promise<PendingInvitation[]> {
  return apiFetch<PendingInvitation[]>('/org/invitations', apiKey)
}

export async function acceptInvitation(apiKey: string, tenantId: string): Promise<void> {
  await apiFetch(`/org/invitations/${tenantId}/accept`, apiKey, { method: 'POST' })
}

export async function declineInvitation(apiKey: string, tenantId: string): Promise<void> {
  return apiFetch<void>(`/org/invitations/${tenantId}/decline`, apiKey, { method: 'POST' })
}

export async function revokeUserSessionsInOrg(apiKey: string, userId: string): Promise<{ revoked: number }> {
  return apiFetch<{ revoked: number }>(`/users/${userId}/sessions/revoke`, apiKey, { method: 'POST' })
}

export async function getHubModelCostPosture(apiKey: string, modelId: string): Promise<import('@/types/api').HubModelCostPosture> {
  return apiFetch<import('@/types/api').HubModelCostPosture>(`/hub/models/${modelId}/cost-posture`, apiKey)
}
