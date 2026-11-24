/**
 * Security stream (W1-A): secret inventory, auth providers with write-only secrets,
 * and the audit log's actor/verify endpoints.
 *
 * Secrets are write-only: the API returns SECRET_MASK for a stored value. Send the
 * mask back (or omit the field) to keep it; send a new value to replace it.
 */
import { API_URL, apiFetch, apiFetchPage, type Page } from './client'

export const SECRET_MASK = '••••••••'

// ── Secret inventory ─────────────────────────────────────────────────────────

export type SecretAgeStatus = 'fresh' | 'aging' | 'stale'

export interface SecretRecord {
  id: string
  kind: string
  label: string | null
  owner_table: string
  owner_id: string
  field: string
  key_id: string | null
  key_current: boolean
  fingerprint: string | null
  rotation_count: number
  rotated_by_label: string | null
  created_at: string
  rotated_at: string
  age_days: number
  age_status: SecretAgeStatus
  /** Secret keys inside a JSON config; rotating sends one value per key. */
  fields: string[]
}

export interface SecretInventory {
  items: SecretRecord[]
  primary_key_id: string
  using_derived_key: boolean
  max_age_days: number
  warn_days: number
}

export function listSecrets(apiKey: string): Promise<SecretInventory> {
  return apiFetch<SecretInventory>('/security/secrets', apiKey)
}

export function rotateSecret(
  apiKey: string,
  secretId: string,
  body: { value?: string; values?: Record<string, string> },
): Promise<SecretRecord> {
  return apiFetch<SecretRecord>(`/security/secrets/${secretId}/rotate`, apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function rewrapSecret(apiKey: string, secretId: string): Promise<SecretRecord> {
  return apiFetch<SecretRecord>(`/security/secrets/${secretId}/rewrap`, apiKey, { method: 'POST' })
}

export function rewrapAllSecrets(apiKey: string): Promise<{ rewrapped: number; primary_key_id: string }> {
  return apiFetch(`/security/secrets/rewrap`, apiKey, { method: 'POST' })
}

// ── Auth providers (OAuth2, LDAP) ────────────────────────────────────────────

export interface OAuth2Provider {
  id: string
  name: string
  authorization_endpoint: string
  token_endpoint: string
  userinfo_endpoint: string
  client_id: string
  client_secret: string | null
  scopes: string
  userinfo_id_field: string
  userinfo_email_field: string
  userinfo_name_field: string
  auto_provision: boolean
  default_workspace_role: string
  default_tenant_role: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface LDAPProvider {
  id: string
  name: string
  server_url: string
  bind_dn: string | null
  bind_password: string | null
  use_ssl: boolean
  start_tls: boolean
  user_search_base: string
  user_search_filter: string
  email_attribute: string
  name_attribute: string
  uid_attribute: string
  auto_provision: boolean
  default_workspace_role: string
  default_tenant_role: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type ProviderKind = 'oauth2' | 'ldap'

const providerPath: Record<ProviderKind, string> = {
  oauth2: '/security/oauth2-providers',
  ldap: '/security/ldap-providers',
}

export async function listAuthProviders<T>(apiKey: string, kind: ProviderKind): Promise<T[]> {
  const res = await apiFetch<{ items: T[] }>(providerPath[kind], apiKey)
  return res.items
}

export function saveAuthProvider<T>(
  apiKey: string,
  kind: ProviderKind,
  body: Record<string, unknown>,
  id?: string,
): Promise<T> {
  return apiFetch<T>(id ? `${providerPath[kind]}/${id}` : providerPath[kind], apiKey, {
    method: id ? 'PUT' : 'POST',
    body: JSON.stringify(body),
  })
}

export async function deleteAuthProvider(apiKey: string, kind: ProviderKind, id: string): Promise<void> {
  await apiFetch<void>(`${providerPath[kind]}/${id}`, apiKey, { method: 'DELETE' })
}

// ── Audit log ────────────────────────────────────────────────────────────────

export interface AuditFilters {
  action?: string
  actor?: string
  actor_type?: string
  api_key_prefix?: string
  access_group_id?: string
  target_type?: string
  target_id?: string
  from?: string
  to?: string
}

export interface AuditRow {
  id: string
  workspace_id: string | null
  actor_user_id: string | null
  actor_api_key_prefix: string | null
  actor_type: string | null
  actor_label: string | null
  action: string
  target_type: string | null
  target_id: string | null
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  created_at: string
  seq: number | null
  prev_hash: string | null
  hash: string | null
}

export interface AuditActor {
  actor_type: string | null
  actor_label: string | null
  actor_user_id: string | null
  actor_api_key_prefix: string | null
  events: number
  last_seen: string | null
}

export interface AuditChainVerification {
  chain_key: string
  ok: boolean
  checked: number
  unchained: number
  first_bad_seq: number | null
  first_bad_event_id: string | null
  reason: string | null
  head_hash: string | null
}

export function auditQuery(filters: AuditFilters): URLSearchParams {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(filters)) if (v) q.set(k, String(v))
  return q
}

export function listAuditPage(
  apiKey: string,
  filters: AuditFilters,
  limit: number,
  offset: number,
): Promise<Page<AuditRow>> {
  const q = auditQuery(filters)
  q.set('limit', String(limit))
  q.set('offset', String(offset))
  return apiFetchPage<AuditRow>(`/audit/events?${q}`, apiKey)
}

export async function listAuditActors(apiKey: string): Promise<AuditActor[]> {
  return (await apiFetch<{ items: AuditActor[] }>('/audit/actors', apiKey)).items
}

export function verifyAuditChain(apiKey: string): Promise<AuditChainVerification> {
  return apiFetch<AuditChainVerification>('/audit/verify', apiKey)
}

/** Download the filtered audit log (CSV or JSON) as text. */
export async function exportAuditLog(apiKey: string, filters: AuditFilters, format: 'csv' | 'json'): Promise<string> {
  const q = auditQuery(filters)
  q.set('format', format)
  const res = await fetch(`${API_URL}/audit/events/export?${q}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.text()
}
