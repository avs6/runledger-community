'use client'

import { useSession } from 'next-auth/react'
import { useTheme } from 'next-themes'
import { useState, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { toast } from 'sonner'
import {
  Key, Bell, Shield, Settings2, Users, Building2, Plug, Terminal, CheckCheck, Lock,
  Search, X, SlidersHorizontal, Radio, Trash2, HardDrive, Mail, Github,
} from 'lucide-react'
import type {
  LedgerSnapshotResponse,
  LedgerVerifyResult,
} from '@/types/api'
import {
  listLedgerSnapshots,
  generateLedgerSnapshot,
  verifyLedgerSnapshot,
} from '@/lib/api'
import { useRole } from '@/components/rbac/useRole'
import OrgTab from '@/components/settings/OrgTab'
import RetentionTab from '@/components/settings/RetentionTab'
import SsoTab from '@/components/settings/SsoTab'
import WarehouseTab from '@/components/settings/WarehouseTab'
import GitTab from '@/components/settings/GitTab'
import type { AlertRule, AlertFiring, ApiKeyResponse, TenantResponse, AdminWorkspaceResponse, CapturePolicyResponse, EmailPreference, EmailLogItem, KafkaExportConfig, KafkaExportDelivery } from '@/types/api'
import {
  listApiKeys,
  createApiKey,
  revokeApiKey,
  testSlackWebhook,
  getCapturePolicy,
  upsertCapturePolicy,
  listTenants,
  createTenant,
  listAdminWorkspaces,
  createAdminWorkspace,
  listAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  listAlertHistory,
  emailAnalyticsReport,
  getOtlpStats,
  listOtlpBatches,
  getEmailPreferences,
  updateEmailPreferences,
  testEmailSend,
  getEmailLog,
  listKafkaExportConfigs,
  createKafkaExportConfig,
  updateKafkaExportConfig,
  deleteKafkaExportConfig,
  testKafkaExportConfig,
  listKafkaExportDeliveries,
} from '@/lib/api'
import type { OtlpStats, OtlpBatchList } from '@/types/api'

interface WorkspaceUser {
  user_id: string
  workspace_id: string
  email: string
  full_name: string | null
  role: string
  is_active: boolean
  last_login_at: string | null
  joined_at: string
}

// Shared input/select class with full dark mode support
const inputCls =
  'rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400'

const TABS = [
  { id: 'api-keys', label: 'API Keys', icon: Key, adminOnly: false },
  { id: 'mcp', label: 'MCP', icon: Plug, adminOnly: false },
  { id: 'alerts', label: 'Alert Rules', icon: Bell, adminOnly: false },
  { id: 'integrations', label: 'Integrations', icon: Settings2, adminOnly: false },
  { id: 'git', label: 'Git Sync', icon: Github, adminOnly: false },
  { id: 'privacy', label: 'Data Capture', icon: Shield, adminOnly: false },
  { id: 'otlp', label: 'OTLP', icon: Radio, adminOnly: false },
  { id: 'compliance', label: 'Compliance', icon: Lock, adminOnly: false },
  { id: 'retention', label: 'Data Retention', icon: Trash2, adminOnly: true },
  { id: 'warehouse', label: 'Warehouse Export', icon: HardDrive, adminOnly: true },
  { id: 'email', label: 'Email', icon: Mail, adminOnly: false },
  { id: 'sso', label: 'SSO / SCIM', icon: Shield, adminOnly: true },
]

export default function SettingsPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { theme, setTheme } = useTheme()
  const searchParams = useSearchParams()
  const router = useRouter()
  const { isWorkspaceAdmin, isOrgAdmin, isPlatformAdmin } = useRole()

  const activeTab = searchParams.get('tab') || 'api-keys'
  const setTab = (tab: string) => router.push(`/settings?tab=${tab}`)

  // ── API Keys ────────────────────────────────────────────────────────────────
  const [apiKeys, setApiKeys] = useState<ApiKeyResponse[]>([])
  const [keySearch, setKeySearch] = useState('')
  const [keyUserFilter, setKeyUserFilter] = useState('')
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyEnv, setNewKeyEnv] = useState('dev')
  const [creatingKey, setCreatingKey] = useState(false)
  const [newRawKey, setNewRawKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [mcpCopied, setMcpCopied] = useState<'cli' | 'json' | null>(null)
  const [mcpSelectedKey, setMcpSelectedKey] = useState<string>('')


  // ── Integrations ────────────────────────────────────────────────────────────
  const [slackWebhookUrl, setSlackWebhookUrl] = useState('')
  const [slackTestResult, setSlackTestResult] = useState<{ ok: boolean; error: string | null } | null>(null)
  const [testingSlack, setTestingSlack] = useState(false)

  // Kafka Export
  const [kafkaConfigs, setKafkaConfigs] = useState<KafkaExportConfig[]>([])
  const [kafkaLoaded, setKafkaLoaded] = useState(false)
  const [showKafkaForm, setShowKafkaForm] = useState(false)
  const [kafkaForm, setKafkaForm] = useState({
    label: 'kafka export',
    bootstrap_servers: '',
    topic_prefix: 'runledger',
    security_protocol: 'PLAINTEXT',
    sasl_mechanism: '',
    sasl_username: '',
    sasl_password: '',
    ssl_ca_cert: '',
    event_types: ['run.completed', 'run.failed', 'alert.fired', 'budget.breached', 'score.submitted'] as string[],
  })
  const [savingKafka, setSavingKafka] = useState(false)
  const [kafkaTestResults, setKafkaTestResults] = useState<Record<string, { ok: boolean; error: string | null; topic: string | null }>>({})
  const [testingKafkaId, setTestingKafkaId] = useState<string | null>(null)
  const [kafkaDeliveries, setKafkaDeliveries] = useState<Record<string, KafkaExportDelivery[]>>({})
  const [expandedKafkaId, setExpandedKafkaId] = useState<string | null>(null)

  // ── Privacy capture policy ──────────────────────────────────────────────────
  const [capturePolicy, setCapturePolicy] = useState<CapturePolicyResponse | null>(null)
  const [privacyMode, setPrivacyMode] = useState('METADATA_ONLY')
  const [sampledRate, setSampledRate] = useState('')
  const [savingPrivacy, setSavingPrivacy] = useState(false)

  // ── Tenant management ───────────────────────────────────────────────────────
  const [adminSecret, setAdminSecret] = useState(process.env.NEXT_PUBLIC_ADMIN_SECRET ?? '')
  const [adminAuthed, setAdminAuthed] = useState(false)
  const [tenants, setTenants] = useState<TenantResponse[]>([])
  const [newTenantSlug, setNewTenantSlug] = useState('')
  const [newTenantName, setNewTenantName] = useState('')
  const [newTenantPlan, setNewTenantPlan] = useState('free')
  const [creatingTenant, setCreatingTenant] = useState(false)
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null)
  const [workspaces, setWorkspaces] = useState<AdminWorkspaceResponse[]>([])
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false)
  const [newWorkspaceName, setNewWorkspaceName] = useState('')
  const [creatingWorkspace, setCreatingWorkspace] = useState(false)

  // ── Alert Rules ──────────────────────────────────────────────────────────────
  const [alertRules, setAlertRules] = useState<AlertRule[]>([])
  const [alertHistory, setAlertHistory] = useState<AlertFiring[]>([])
  const [newAlertName, setNewAlertName] = useState('')
  const [newAlertMetric, setNewAlertMetric] = useState('error_rate')
  const [newAlertOperator, setNewAlertOperator] = useState('gt')
  const [newAlertThreshold, setNewAlertThreshold] = useState('')
  const [newAlertWindow, setNewAlertWindow] = useState('60')
  const [newAlertEmailEnabled, setNewAlertEmailEnabled] = useState(false)
  const [creatingAlert, setCreatingAlert] = useState(false)
  const [sendingReport, setSendingReport] = useState(false)


  // ── Compliance (Ledger) ────────────────────────────────────────────────────────
  const [snapshots, setSnapshots] = useState<LedgerSnapshotResponse[]>([])
  const [verifyResults, setVerifyResults] = useState<Record<string, LedgerVerifyResult>>({})
  const [generatingSnap, setGeneratingSnap] = useState(false)
  const [verifyingSnap, setVerifyingSnap] = useState<string | null>(null)
  const [loadingCompliance, setLoadingCompliance] = useState(false)
  const [complianceAttempted, setComplianceAttempted] = useState(false)

  // ── OTLP ─────────────────────────────────────────────────────────────────────
  const [otlpStats, setOtlpStats] = useState<OtlpStats | null>(null)
  const [otlpBatches, setOtlpBatches] = useState<OtlpBatchList | null>(null)
  const [loadingOtlp, setLoadingOtlp] = useState(false)
  const [otlpAttempted, setOtlpAttempted] = useState(false)

  // ── Workspace users ──────────────────────────────────────────────────────────
  const [wsUsers, setWsUsers] = useState<WorkspaceUser[]>([])
  const [loadingUsers, setLoadingUsers] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')
  const [inviting, setInviting] = useState(false)
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // ── Email Preferences ─────────────────────────────────────────────────────────
  const [emailPrefs, setEmailPrefs] = useState<EmailPreference | null>(null)
  const [emailLog, setEmailLog] = useState<EmailLogItem[]>([])
  const [loadingEmailPrefs, setLoadingEmailPrefs] = useState(false)
  const [emailPrefsAttempted, setEmailPrefsAttempted] = useState(false)
  const [savingEmailPrefs, setSavingEmailPrefs] = useState(false)
  const [testingEmail, setTestingEmail] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey) return
    try {
      const [keys, policy, alertsData, historyData] = await Promise.all([
        listApiKeys(apiKey),
        getCapturePolicy(apiKey),
        listAlertRules(apiKey, true),
        listAlertHistory(apiKey, 10),
      ])
      setApiKeys(keys.filter((k) => !k.is_session))
      if (policy) {
        setCapturePolicy(policy)
        setPrivacyMode(policy.privacy_mode)
        setSampledRate(policy.sampled_rate ? String(parseFloat(policy.sampled_rate) * 100) : '')
      }
      setAlertRules(alertsData.items)
      setAlertHistory(historyData.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load settings')
    }
  }, [apiKey])

  useEffect(() => { load() }, [load])

  const loadWsUsers = useCallback(async () => {
    if (!apiKey) return
    setLoadingUsers(true)
    try {
      const r = await fetch(`${apiBase}/users`, {
        headers: { Authorization: `Bearer ${apiKey}` },
      })
      if (r.ok) setWsUsers(await r.json())
    } catch (err) {
      console.error(err)
    } finally {
      setLoadingUsers(false)
    }
  }, [apiKey, apiBase])

  useEffect(() => {
    if (activeTab === 'users') loadWsUsers()
  }, [activeTab, loadWsUsers])

  const loadCompliance = useCallback(async () => {
    if (!apiKey) return
    setComplianceAttempted(true)
    setLoadingCompliance(true)
    try {
      const snapList = await listLedgerSnapshots(apiKey)
      setSnapshots(snapList.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load compliance data')
    } finally {
      setLoadingCompliance(false)
    }
  }, [apiKey])

  useEffect(() => {
    if (activeTab === 'compliance' && !complianceAttempted) loadCompliance()
  }, [activeTab, complianceAttempted, loadCompliance])

  const loadOtlp = useCallback(async () => {
    if (!apiKey) return
    setOtlpAttempted(true)
    setLoadingOtlp(true)
    try {
      const [stats, batches] = await Promise.all([
        getOtlpStats(apiKey),
        listOtlpBatches(apiKey, 20, 0),
      ])
      setOtlpStats(stats)
      setOtlpBatches(batches)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load OTLP data')
    } finally {
      setLoadingOtlp(false)
    }
  }, [apiKey])

  useEffect(() => {
    if (activeTab === 'otlp' && !otlpAttempted) loadOtlp()
  }, [activeTab, otlpAttempted, loadOtlp])

  const loadEmailPrefs = useCallback(async () => {
    if (!apiKey) return
    setEmailPrefsAttempted(true)
    setLoadingEmailPrefs(true)
    try {
      const [prefs, logData] = await Promise.all([
        getEmailPreferences(apiKey),
        getEmailLog(apiKey),
      ])
      setEmailPrefs(prefs)
      setEmailLog(logData.items.slice(0, 20))
    } catch (err) {
      console.error(err)
      toast.error('Failed to load email settings')
    } finally {
      setLoadingEmailPrefs(false)
    }
  }, [apiKey])

  useEffect(() => {
    if (activeTab === 'email' && !emailPrefsAttempted) loadEmailPrefs()
  }, [activeTab, emailPrefsAttempted, loadEmailPrefs])

  // ── API Key handlers ────────────────────────────────────────────────────────

  async function handleCreateKey(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setCreatingKey(true)
    try {
      const created = await createApiKey(apiKey, {
        name: newKeyName.trim() || null,
        environment: newKeyEnv,
        scopes: [],
        created_by: session?.user?.email ?? null,
      })
      setNewRawKey(created.key)
      setCopied(false)
      setApiKeys((prev) => [created, ...prev])
      setNewKeyName('')
      setNewKeyEnv('dev')
      toast.success('API key created — save it now')
    } catch (err) {
      console.error(err)
      toast.error('Failed to create API key')
    } finally {
      setCreatingKey(false)
    }
  }

  async function handleRevoke(keyId: string) {
    if (!apiKey) return
    if (!confirm('Revoke this API key? This cannot be undone.')) return
    try {
      await revokeApiKey(apiKey, keyId)
      setApiKeys((prev) => prev.filter((k) => k.id !== keyId))
      if (newRawKey) setNewRawKey(null)
      toast.success('API key revoked')
    } catch (err) {
      console.error(err)
      toast.error('Failed to revoke API key')
    }
  }

  async function handleCopy() {
    if (!newRawKey) return
    await navigator.clipboard.writeText(newRawKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // ── Integrations handlers ───────────────────────────────────────────────────

  async function handleTestSlack(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !slackWebhookUrl.trim()) return
    setTestingSlack(true)
    setSlackTestResult(null)
    try {
      const result = await testSlackWebhook(apiKey, slackWebhookUrl.trim())
      setSlackTestResult(result)
      if (result.ok) {
        toast.success('Test message sent to Slack')
      } else {
        toast.error(`Slack test failed: ${result.error}`)
      }
    } catch (err) {
      const msg = String(err)
      setSlackTestResult({ ok: false, error: msg })
      toast.error(`Slack test failed: ${msg}`)
    } finally {
      setTestingSlack(false)
    }
  }

  // ── Kafka handlers ──────────────────────────────────────────────────────────

  const loadKafkaConfigs = useCallback(async () => {
    if (!apiKey || kafkaLoaded) return
    try {
      const data = await listKafkaExportConfigs(apiKey)
      setKafkaConfigs(data.items)
      setKafkaLoaded(true)
    } catch {
      toast.error('Failed to load Kafka configs')
    }
  }, [apiKey, kafkaLoaded])

  useEffect(() => {
    if (activeTab === 'integrations') loadKafkaConfigs()
  }, [activeTab, loadKafkaConfigs])

  async function handleCreateKafka(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setSavingKafka(true)
    try {
      const cfg = await createKafkaExportConfig(apiKey, {
        label: kafkaForm.label,
        bootstrap_servers: kafkaForm.bootstrap_servers,
        topic_prefix: kafkaForm.topic_prefix,
        security_protocol: kafkaForm.security_protocol,
        sasl_mechanism: kafkaForm.sasl_mechanism || null,
        sasl_username: kafkaForm.sasl_username || null,
        sasl_password: kafkaForm.sasl_password || null,
        ssl_ca_cert: kafkaForm.ssl_ca_cert || null,
        event_types: kafkaForm.event_types,
      })
      setKafkaConfigs(prev => [cfg, ...prev])
      setShowKafkaForm(false)
      setKafkaForm({
        label: 'kafka export', bootstrap_servers: '', topic_prefix: 'runledger',
        security_protocol: 'PLAINTEXT', sasl_mechanism: '', sasl_username: '',
        sasl_password: '', ssl_ca_cert: '', event_types: ['run.completed','run.failed','alert.fired','budget.breached','score.submitted'],
      })
      toast.success('Kafka export config created')
    } catch (err) {
      toast.error(`Failed to create Kafka config: ${err}`)
    } finally {
      setSavingKafka(false)
    }
  }

  async function handleToggleKafka(cfg: KafkaExportConfig) {
    if (!apiKey) return
    try {
      const updated = await updateKafkaExportConfig(apiKey, cfg.id, { enabled: !cfg.enabled })
      setKafkaConfigs(prev => prev.map(c => c.id === cfg.id ? updated : c))
      toast.success(updated.enabled ? 'Kafka export enabled' : 'Kafka export disabled')
    } catch {
      toast.error('Failed to update Kafka config')
    }
  }

  async function handleDeleteKafka(id: string) {
    if (!apiKey) return
    try {
      await deleteKafkaExportConfig(apiKey, id)
      setKafkaConfigs(prev => prev.filter(c => c.id !== id))
      toast.success('Kafka export config deleted')
    } catch {
      toast.error('Failed to delete Kafka config')
    }
  }

  async function handleTestKafka(id: string) {
    if (!apiKey) return
    setTestingKafkaId(id)
    try {
      const result = await testKafkaExportConfig(apiKey, id)
      setKafkaTestResults(prev => ({ ...prev, [id]: result }))
      if (result.ok) {
        toast.success(`Test event published to ${result.topic}`)
      } else {
        toast.error(`Kafka test failed: ${result.error}`)
      }
    } catch (err) {
      toast.error(`Kafka test error: ${err}`)
    } finally {
      setTestingKafkaId(null)
    }
  }

  async function handleExpandKafka(id: string) {
    if (expandedKafkaId === id) {
      setExpandedKafkaId(null)
      return
    }
    setExpandedKafkaId(id)
    if (!kafkaDeliveries[id] && apiKey) {
      try {
        const data = await listKafkaExportDeliveries(apiKey, id)
        setKafkaDeliveries(prev => ({ ...prev, [id]: data.items }))
      } catch {
        setKafkaDeliveries(prev => ({ ...prev, [id]: [] }))
      }
    }
  }

  // ── Privacy handlers ────────────────────────────────────────────────────────

  async function handleSavePrivacy(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setSavingPrivacy(true)
    try {
      const rate = privacyMode === 'SAMPLED' && sampledRate.trim()
        ? parseFloat(sampledRate) / 100
        : null
      const updated = await upsertCapturePolicy(apiKey, {
        privacy_mode: privacyMode,
        sampled_rate: rate,
      })
      setCapturePolicy(updated)
      toast.success('Capture policy saved')
    } catch (err) {
      console.error(err)
      toast.error('Failed to save capture policy')
    } finally {
      setSavingPrivacy(false)
    }
  }

  // ── Alert rule handlers ──────────────────────────────────────────────────────

  async function handleCreateAlert(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !newAlertName.trim() || !newAlertThreshold) return
    setCreatingAlert(true)
    try {
      const rule = await createAlertRule(apiKey, {
        name: newAlertName.trim(),
        metric: newAlertMetric,
        operator: newAlertOperator,
        threshold: parseFloat(newAlertThreshold),
        window_minutes: parseInt(newAlertWindow, 10),
        email_enabled: newAlertEmailEnabled,
      })
      setAlertRules((prev) => [rule, ...prev])
      setNewAlertName('')
      setNewAlertThreshold('')
      setNewAlertEmailEnabled(false)
      toast.success('Alert rule created')
    } catch (err) {
      console.error(err)
      toast.error('Failed to create alert rule')
    } finally {
      setCreatingAlert(false)
    }
  }

  async function handleToggleAlert(rule: AlertRule) {
    if (!apiKey) return
    try {
      const updated = await updateAlertRule(apiKey, rule.id, { is_active: !rule.is_active })
      setAlertRules((prev) => prev.map((r) => (r.id === rule.id ? updated : r)))
      toast.success(updated.is_active ? 'Rule enabled' : 'Rule disabled')
    } catch (err) {
      console.error(err)
      toast.error('Failed to update rule')
    }
  }

  async function handleDeleteAlert(ruleId: string) {
    if (!apiKey || !confirm('Delete this alert rule?')) return
    try {
      await deleteAlertRule(apiKey, ruleId)
      setAlertRules((prev) => prev.filter((r) => r.id !== ruleId))
      toast.success('Alert rule deleted')
    } catch (err) {
      console.error(err)
      toast.error('Failed to delete rule')
    }
  }

  async function handleSendReport() {
    if (!apiKey) return
    setSendingReport(true)
    try {
      const result = await emailAnalyticsReport(apiKey, 7)
      toast.success(`Report sent to ${result.recipients} recipient${result.recipients !== 1 ? 's' : ''}`)
    } catch (err) {
      console.error(err)
      toast.error('Failed to send report')
    } finally {
      setSendingReport(false)
    }
  }

  // ── Compliance handlers ─────────────────────────────────────────────────────

  async function handleGenerateSnapshot() {
    if (!apiKey) return
    setGeneratingSnap(true)
    try {
      const snap = await generateLedgerSnapshot(apiKey)
      setSnapshots((prev) => [snap, ...prev.filter((s) => s.snapshot_date !== snap.snapshot_date)])
      toast.success('Snapshot generated')
    } catch { toast.error('Failed to generate snapshot') }
    finally { setGeneratingSnap(false) }
  }

  async function handleVerifySnapshot(snap: LedgerSnapshotResponse) {
    if (!apiKey) return
    setVerifyingSnap(snap.snapshot_date)
    try {
      const result = await verifyLedgerSnapshot(apiKey, snap.snapshot_date)
      setVerifyResults((prev) => ({ ...prev, [snap.snapshot_date]: result }))
      if (result.match) toast.success('Snapshot integrity verified')
      else toast.error(`Integrity check failed: ${result.status}`)
    } catch { toast.error('Failed to verify snapshot') }
    finally { setVerifyingSnap(null) }
  }

  // ── Tenant management handlers ──────────────────────────────────────────────

  async function handleAdminAuth(e: React.FormEvent) {
    e.preventDefault()
    if (!adminSecret.trim()) return
    try {
      const data = await listTenants(adminSecret.trim())
      setTenants(data)
      setAdminAuthed(true)
    } catch {
      toast.error('Invalid admin secret or server error')
    }
  }

  async function handleCreateTenant(e: React.FormEvent) {
    e.preventDefault()
    if (!adminSecret.trim() || !newTenantSlug.trim() || !newTenantName.trim()) return
    setCreatingTenant(true)
    try {
      const tenant = await createTenant(adminSecret.trim(), {
        slug: newTenantSlug.trim(),
        name: newTenantName.trim(),
        plan: newTenantPlan,
      })
      setTenants((prev) => [tenant, ...prev])
      setNewTenantSlug('')
      setNewTenantName('')
      setNewTenantPlan('free')
      toast.success(`Tenant "${tenant.name}" created`)
    } catch (err) {
      console.error(err)
      toast.error('Failed to create tenant')
    } finally {
      setCreatingTenant(false)
    }
  }

  async function handleSelectTenant(tenantId: string) {
    if (selectedTenantId === tenantId) {
      setSelectedTenantId(null)
      setWorkspaces([])
      return
    }
    setSelectedTenantId(tenantId)
    setLoadingWorkspaces(true)
    try {
      const ws = await listAdminWorkspaces(adminSecret, tenantId)
      setWorkspaces(ws)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load workspaces')
    } finally {
      setLoadingWorkspaces(false)
    }
  }

  async function handleCreateWorkspace(e: React.FormEvent) {
    e.preventDefault()
    if (!adminSecret.trim() || !selectedTenantId || !newWorkspaceName.trim()) return
    setCreatingWorkspace(true)
    try {
      const ws = await createAdminWorkspace(adminSecret, {
        tenant_id: selectedTenantId,
        name: newWorkspaceName.trim(),
      })
      setWorkspaces((prev) => [...prev, ws])
      setNewWorkspaceName('')
      toast.success(`Workspace "${ws.name}" created`)
    } catch (err) {
      console.error(err)
      toast.error('Failed to create workspace')
    } finally {
      setCreatingWorkspace(false)
    }
  }

  // ── Users handlers ──────────────────────────────────────────────────────────

  async function handleInviteUser(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !inviteEmail.trim()) return
    setInviting(true)
    try {
      const r = await fetch(`${apiBase}/users/invite`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: inviteEmail.trim(), role: inviteRole }),
      })
      if (!r.ok) {
        const d = await r.json()
        toast.error(d.detail || 'Failed to invite user')
        return
      }
      setInviteEmail('')
      toast.success('Invitation sent')
      await loadWsUsers()
    } catch (err) {
      console.error(err)
      toast.error('Failed to invite user')
    } finally {
      setInviting(false)
    }
  }

  async function handleRemoveUser(userId: string, email: string) {
    if (!apiKey || !confirm(`Remove ${email} from this workspace?`)) return
    try {
      await fetch(`${apiBase}/users/${userId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${apiKey}` },
      })
      setWsUsers((prev) => prev.filter((u) => u.user_id !== userId))
      toast.success('User removed from workspace')
    } catch (err) {
      console.error(err)
      toast.error('Failed to remove user')
    }
  }

  async function handleChangeRole(userId: string, role: string) {
    if (!apiKey) return
    try {
      await fetch(`${apiBase}/users/${userId}/role`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ role }),
      })
      setWsUsers((prev) => prev.map((u) => u.user_id === userId ? { ...u, role } : u))
      toast.success('Role updated')
    } catch (err) {
      console.error(err)
      toast.error('Failed to update role')
    }
  }

  // ── API key filtering ────────────────────────────────────────────────────────

  const currentUserEmail = (session as Record<string, unknown> | null)?.email as string | undefined
  const workspaceName = (session as Record<string, unknown> | null)?.workspaceName as string | undefined
  const tenantName = ((session as Record<string, unknown> | null)?.tenantName ?? (session as Record<string, unknown> | null)?.orgName) as string | undefined

  const filteredApiKeys = useMemo(() => {
    let rows = apiKeys
    // Non-admins only see their own keys
    if (!isWorkspaceAdmin && !isPlatformAdmin && currentUserEmail) {
      rows = rows.filter((k) => k.created_by === currentUserEmail)
    }
    if (keyUserFilter.trim()) {
      const u = keyUserFilter.toLowerCase()
      rows = rows.filter((k) => (k.created_by ?? '').toLowerCase().includes(u))
    }
    if (keySearch.trim()) {
      const q = keySearch.toLowerCase()
      rows = rows.filter(
        (k) =>
          (k.name ?? '').toLowerCase().includes(q) ||
          k.key_prefix.toLowerCase().includes(q) ||
          (k.created_by ?? '').toLowerCase().includes(q)
      )
    }
    return rows
  }, [apiKeys, keySearch, keyUserFilter, isWorkspaceAdmin, isPlatformAdmin, currentUserEmail])

  // ── Tab content ─────────────────────────────────────────────────────────────

  const visibleTabs = TABS.filter((t) => !t.adminOnly || isOrgAdmin)

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-52 shrink-0 border-r border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 py-4 px-2">
        <div className="mb-3 px-2 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">Settings</div>
        <nav className="flex flex-col gap-0.5">
          {visibleTabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-left w-full transition-colors ${
                activeTab === id
                  ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm font-medium'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-white/70 dark:hover:bg-slate-800/70 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </button>
          ))}
        </nav>

        {/* Appearance at bottom */}
        <div className="mt-6 px-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2">Appearance</div>
          <select
            value={theme ?? 'system'}
            onChange={(e) => setTheme(e.target.value)}
            className="w-full rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">System</option>
          </select>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">

        {/* ── API Keys ─────────────────────────────────────────────────────────── */}
        {activeTab === 'api-keys' && (
          <div className="space-y-6 max-w-4xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold dark:text-white">API Keys</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  Manage API keys for SDK and MCP authentication. Each key is scoped to the current workspace — runs, sessions, and analytics are automatically filtered to this workspace.
                </p>
              </div>
              {workspaceName && (
                <div className="shrink-0 flex flex-col items-end gap-0.5">
                  {tenantName && <span className="text-[10px] text-slate-400 dark:text-slate-500">{tenantName}</span>}
                  <span className="rounded-full bg-violet-100 px-2.5 py-1 text-xs font-semibold text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
                    {workspaceName}
                  </span>
                </div>
              )}
            </div>

            {newRawKey && (
              <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 dark:border-amber-700 dark:bg-amber-950">
                <p className="mb-1 text-sm font-medium text-amber-800 dark:text-amber-200">
                  Save this key — it won&apos;t be shown again.
                </p>
                <p className="mb-3 text-xs text-amber-600 dark:text-amber-400">
                  This key is scoped to <strong>{workspaceName ?? 'your workspace'}</strong>. Use it in your SDK or MCP config to send runs here.
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 rounded bg-white px-3 py-1.5 font-mono text-xs text-gray-800 shadow-inner dark:bg-gray-900 dark:text-gray-100">
                    {newRawKey}
                  </code>
                  <button onClick={handleCopy} className="rounded bg-amber-600 px-3 py-1.5 text-xs text-white hover:bg-amber-700">
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                  <button
                    onClick={() => { setTab('mcp'); setMcpSelectedKey(newRawKey) }}
                    className="rounded bg-violet-600 px-3 py-1.5 text-xs text-white hover:bg-violet-700"
                  >
                    Set up MCP →
                  </button>
                  <button onClick={() => setNewRawKey(null)} className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                    Dismiss
                  </button>
                </div>
              </div>
            )}

            <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-700 dark:bg-slate-800/40">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3">Create new key for <span className="text-violet-600 dark:text-violet-400">{workspaceName ?? 'this workspace'}</span></p>
              <form onSubmit={handleCreateKey} className="flex flex-wrap gap-2">
                <input type="text" placeholder="Key name (optional)" value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)} className={inputCls} />
                <select value={newKeyEnv} onChange={(e) => setNewKeyEnv(e.target.value)} className={inputCls}>
                  <option value="dev">dev</option>
                  <option value="staging">staging</option>
                  <option value="prod">prod</option>
                </select>
                <button type="submit" disabled={creatingKey} className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
                  {creatingKey ? 'Creating…' : 'Create Key'}
                </button>
              </form>
            </div>

            {/* Filter bar */}
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 px-4 py-3 space-y-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                <SlidersHorizontal className="h-3.5 w-3.5" /> Filters
              </div>
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                {(isWorkspaceAdmin || isPlatformAdmin) && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500 dark:text-slate-400 w-16 shrink-0">Created by</span>
                    <div className="relative">
                      <input
                        value={keyUserFilter}
                        onChange={(e) => setKeyUserFilter(e.target.value)}
                        placeholder="email…"
                        className={`${inputCls} w-44`}
                      />
                      {keyUserFilter && (
                        <button onClick={() => setKeyUserFilter('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                          <X className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                )}
                {keyUserFilter && (
                  <button onClick={() => { setKeyUserFilter('') }}
                    className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-white ml-auto">
                    <X className="h-3.5 w-3.5" /> Clear filters
                  </button>
                )}
              </div>
            </div>

            {/* Search */}
            <div className="flex items-center gap-2">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                <input
                  value={keySearch}
                  onChange={(e) => setKeySearch(e.target.value)}
                  placeholder={`Search within ${filteredApiKeys.length} key${filteredApiKeys.length !== 1 ? 's' : ''}…`}
                  className={`${inputCls} pl-8 w-full`}
                />
                {keySearch && (
                  <button onClick={() => setKeySearch('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
              {filteredApiKeys.length !== apiKeys.length && (
                <span className="text-xs font-medium text-violet-600 dark:text-violet-400">
                  {filteredApiKeys.length} of {apiKeys.length} keys
                </span>
              )}
              {!isWorkspaceAdmin && !isPlatformAdmin && (
                <span className="text-xs text-slate-400 italic">Showing your keys only</span>
              )}
            </div>

            <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                  <tr>
                    <th className="px-4 py-2 text-left">Prefix</th>
                    <th className="px-4 py-2 text-left">Name</th>
                    <th className="px-4 py-2 text-left">Created</th>
                    <th className="px-4 py-2 text-left">Created By</th>
                    <th className="px-4 py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {filteredApiKeys.length === 0 ? (
                    <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400 dark:text-gray-500">
                      {apiKeys.length === 0 ? 'No active API keys.' : 'No keys match your filters.'}
                    </td></tr>
                  ) : (
                    filteredApiKeys.map((k) => (
                      <tr key={k.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">{k.key_prefix}…</td>
                        <td className="px-4 py-2 text-gray-600 dark:text-gray-400">{k.name ?? '—'}</td>
                        <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-500">{new Date(k.created_at).toLocaleString()}</td>
                        <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">{k.created_by ?? '—'}</td>
                        <td className="px-4 py-2 text-right">
                          <button onClick={() => handleRevoke(k.id)} className="text-xs text-red-500 hover:text-red-700 hover:underline dark:text-red-400">Revoke</button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

          </div>
        )}

        {/* ── MCP ──────────────────────────────────────────────────────────────── */}
        {activeTab === 'mcp' && (() => {
          const mcpKey = mcpSelectedKey || newRawKey || ''
          const mcpKeyDisplay = mcpKey || '<your-api-key>'
          return (
            <div className="space-y-6 max-w-3xl">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold dark:text-white">MCP Setup</h2>
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                    Connect Claude Desktop or Claude Code to your RunLedger workspace via the Model Context Protocol.
                    All MCP tool calls are attributed to <strong className="text-slate-700 dark:text-slate-200">{workspaceName ?? 'your workspace'}</strong>.
                  </p>
                </div>
                <span className="shrink-0 rounded-full bg-violet-100 px-2.5 py-1 text-xs font-semibold text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
                  /mcp
                </span>
              </div>

              {/* Key selector */}
              <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-700 dark:bg-slate-800/40 space-y-3">
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Select API key to use</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  The key below will be pre-filled in the snippets. It must belong to{' '}
                  <strong className="text-violet-600 dark:text-violet-400">{workspaceName ?? 'this workspace'}</strong>.
                </p>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={mcpSelectedKey}
                    onChange={(e) => setMcpSelectedKey(e.target.value)}
                    placeholder="Paste your API key here (rl_…)"
                    className={`${inputCls} flex-1 font-mono`}
                  />
                  <button
                    onClick={() => setTab('api-keys')}
                    className="shrink-0 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 hover:border-violet-300 hover:text-violet-700 dark:hover:border-violet-600 dark:hover:text-violet-400 transition-colors"
                  >
                    + Create key
                  </button>
                </div>
                {newRawKey && !mcpSelectedKey && (
                  <button
                    onClick={() => setMcpSelectedKey(newRawKey)}
                    className="text-[11px] text-violet-600 dark:text-violet-400 hover:underline"
                  >
                    ↑ Use your recently created key
                  </button>
                )}
                {!mcpKey && (
                  <p className="text-[11px] text-amber-600 dark:text-amber-400">
                    Paste an API key or create a new one — snippets will auto-fill.
                  </p>
                )}
              </div>

              {/* Claude Code CLI */}
              <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                <div className="flex items-center gap-2.5 border-b border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/60">
                  <Terminal className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Claude Code</h3>
                  <span className="text-xs text-slate-400">— one command to register</span>
                </div>
                <div className="p-4 space-y-3">
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Run this once in your terminal. Claude Code will remember the server across sessions.
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 overflow-x-auto rounded-lg bg-slate-900 px-3 py-2.5 font-mono text-xs text-emerald-400 dark:bg-slate-950">
                      {`RUNLEDGER_API_KEY=${mcpKeyDisplay} claude mcp add --transport http runledger ${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/mcp`}
                    </code>
                    <button
                      onClick={async () => {
                        await navigator.clipboard.writeText(
                          `RUNLEDGER_API_KEY=${mcpKeyDisplay} claude mcp add --transport http runledger ${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/mcp`
                        )
                        setMcpCopied('cli')
                        setTimeout(() => setMcpCopied(null), 2000)
                      }}
                      className="shrink-0 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-violet-300 hover:text-violet-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-violet-600 dark:hover:text-violet-400"
                    >
                      {mcpCopied === 'cli' ? <CheckCheck className="h-3.5 w-3.5 text-emerald-500" /> : 'Copy'}
                    </button>
                  </div>
                </div>
              </div>

              {/* Claude Desktop JSON */}
              <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                <div className="flex items-center gap-2.5 border-b border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/60">
                  <Key className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Claude Desktop</h3>
                  <span className="text-xs text-slate-400">— add to <code className="font-mono">claude_desktop_config.json</code></span>
                </div>
                <div className="p-4 space-y-3">
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Add the block below to your Claude Desktop config file, then restart the app.
                  </p>
                  <div className="flex items-start gap-2">
                    <pre className="flex-1 overflow-x-auto rounded-lg bg-slate-900 px-3 py-3 font-mono text-xs text-slate-300 dark:bg-slate-950 dark:text-slate-200">{`{
  "mcpServers": {
    "runledger": {
      "url": "${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/mcp",
      "env": {
        "RUNLEDGER_API_KEY": "${mcpKeyDisplay}"
      }
    }
  }
}`}</pre>
                    <button
                      onClick={async () => {
                        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
                        const json = `{\n  "mcpServers": {\n    "runledger": {\n      "url": "${apiUrl}/mcp",\n      "env": {\n        "RUNLEDGER_API_KEY": "${mcpKeyDisplay}"\n      }\n    }\n  }\n}`
                        await navigator.clipboard.writeText(json)
                        setMcpCopied('json')
                        setTimeout(() => setMcpCopied(null), 2000)
                      }}
                      className="shrink-0 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-violet-300 hover:text-violet-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-violet-600 dark:hover:text-violet-400"
                    >
                      {mcpCopied === 'json' ? <CheckCheck className="h-3.5 w-3.5 text-emerald-500" /> : 'Copy'}
                    </button>
                  </div>
                </div>
              </div>

              {/* Info */}
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/30 px-4 py-3 text-xs text-slate-500 dark:text-slate-400 space-y-1">
                <p className="font-semibold text-slate-700 dark:text-slate-300">How it works</p>
                <ul className="list-disc list-inside space-y-0.5 pl-1">
                  <li>The MCP server exposes RunLedger tools to Claude (query runs, budgets, analytics).</li>
                  <li>All tool calls are authenticated with your workspace API key — data is scoped to <strong className="text-violet-600 dark:text-violet-400">{workspaceName ?? 'this workspace'}</strong>.</li>
                  <li>Switch workspaces by changing <code className="font-mono">RUNLEDGER_API_KEY</code> to a key from the target workspace.</li>
                </ul>
              </div>
            </div>
          )
        })()}

        {/* ── Users ────────────────────────────────────────────────────────────── */}
        {activeTab === 'users' && (
          <div className="space-y-6 max-w-4xl">
            <div>
              <h2 className="text-xl font-semibold dark:text-white">Workspace Users</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Manage who has access to this workspace.</p>
            </div>

            {isWorkspaceAdmin && (
              <form onSubmit={handleInviteUser} className="flex flex-wrap gap-2">
                <input
                  type="email"
                  placeholder="user@example.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className={inputCls}
                  required
                />
                <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)} className={inputCls}>
                  <option value="workspace_admin">Admin</option>
                  <option value="member">Member</option>
                  <option value="viewer">Viewer</option>
                </select>
                <button type="submit" disabled={inviting} className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
                  {inviting ? 'Inviting…' : 'Invite User'}
                </button>
              </form>
            )}

            <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                  <tr>
                    <th className="px-4 py-2 text-left">User</th>
                    <th className="px-4 py-2 text-left">Role</th>
                    <th className="px-4 py-2 text-left">Joined</th>
                    {isWorkspaceAdmin && <th className="px-4 py-2" />}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {loadingUsers ? (
                    <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400">Loading…</td></tr>
                  ) : wsUsers.length === 0 ? (
                    <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400 dark:text-gray-500">No users in this workspace.</td></tr>
                  ) : (
                    wsUsers.map((u) => (
                      <tr key={u.user_id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="px-4 py-2">
                          <p className="font-medium dark:text-gray-200">{u.full_name || '—'}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{u.email}</p>
                        </td>
                        <td className="px-4 py-2">
                          {isWorkspaceAdmin ? (
                            <select
                              value={u.role}
                              onChange={(e) => handleChangeRole(u.user_id, e.target.value)}
                              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
                            >
                              <option value="workspace_admin">Admin</option>
                              <option value="member">Member</option>
                              <option value="viewer">Viewer</option>
                            </select>
                          ) : (
                            <span className="rounded bg-slate-100 dark:bg-slate-700 px-2 py-0.5 text-xs text-slate-600 dark:text-slate-300">{u.role}</span>
                          )}
                        </td>
                        <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">{new Date(u.joined_at).toLocaleDateString()}</td>
                        {isWorkspaceAdmin && (
                          <td className="px-4 py-2 text-right">
                            <button onClick={() => handleRemoveUser(u.user_id, u.email)} className="text-xs text-red-500 hover:text-red-700 hover:underline dark:text-red-400">Remove</button>
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {/* ── Alert Rules ───────────────────────────────────────────────────────── */}
        {activeTab === 'alerts' && (
          <div className="space-y-6 max-w-4xl">
            <div>
              <h2 className="text-xl font-semibold dark:text-white">Alert Rules</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Fire Slack notifications when a metric crosses a threshold. Evaluated every 5 minutes.</p>
            </div>

            <form onSubmit={handleCreateAlert} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <input className={inputCls} placeholder="Rule name (e.g. High error rate)" value={newAlertName} onChange={(e) => setNewAlertName(e.target.value)} required />
              <select className={inputCls} value={newAlertMetric} onChange={(e) => setNewAlertMetric(e.target.value)}>
                <option value="error_rate">Error Rate</option>
                <option value="p95_latency">P95 Latency (ms)</option>
                <option value="avg_score">Avg Score</option>
                <option value="spend_velocity">Spend Velocity ($)</option>
              </select>
              <div className="flex gap-2">
                <select className={`${inputCls} w-24`} value={newAlertOperator} onChange={(e) => setNewAlertOperator(e.target.value)}>
                  <option value="gt">&gt; (above)</option>
                  <option value="lt">&lt; (below)</option>
                </select>
                <input className={`${inputCls} flex-1`} type="number" step="any" min="0" placeholder="Threshold" value={newAlertThreshold} onChange={(e) => setNewAlertThreshold(e.target.value)} required />
              </div>
              <div className="flex items-center gap-2">
                <input className={`${inputCls} w-24`} type="number" min="5" max="1440" placeholder="60" value={newAlertWindow} onChange={(e) => setNewAlertWindow(e.target.value)} />
                <span className="text-sm text-gray-500 dark:text-gray-400">min window</span>
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={newAlertEmailEnabled}
                  onChange={(e) => setNewAlertEmailEnabled(e.target.checked)}
                  className="rounded border-gray-300 dark:border-gray-600"
                />
                Email workspace admins
              </label>
              <button type="submit" disabled={creatingAlert} className="rounded bg-indigo-600 px-4 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
                {creatingAlert ? 'Creating…' : 'Add Rule'}
              </button>
            </form>

            {alertRules.length === 0 ? (
              <p className="text-sm text-gray-400 dark:text-gray-500">No alert rules yet.</p>
            ) : (
              <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                    <tr>
                      <th className="px-4 py-2 text-left">Name</th>
                      <th className="px-4 py-2 text-left">Metric</th>
                      <th className="px-4 py-2 text-left">Condition</th>
                      <th className="px-4 py-2 text-left">Window</th>
                      <th className="px-4 py-2 text-left">Email</th>
                      <th className="px-4 py-2 text-left">Status</th>
                      <th className="px-4 py-2 text-left" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {alertRules.map((rule) => (
                      <tr key={rule.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="px-4 py-2 font-medium dark:text-gray-200">{rule.name}</td>
                        <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">{rule.metric}</td>
                        <td className="px-4 py-2 text-xs dark:text-gray-300">{rule.operator === 'gt' ? '>' : '<'} {rule.threshold}</td>
                        <td className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400">{rule.window_minutes}m</td>
                        <td className="px-4 py-2">
                          <span className={`text-xs ${rule.email_enabled ? 'text-violet-600 dark:text-violet-400' : 'text-gray-400 dark:text-gray-600'}`}>
                            {rule.email_enabled ? 'On' : 'Off'}
                          </span>
                        </td>
                        <td className="px-4 py-2">
                          <button onClick={() => handleToggleAlert(rule)} className={`rounded px-2 py-0.5 text-xs font-medium ${rule.is_active ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'}`}>
                            {rule.is_active ? 'Active' : 'Paused'}
                          </button>
                        </td>
                        <td className="px-4 py-2">
                          <button onClick={() => handleDeleteAlert(rule.id)} className="text-xs text-red-500 hover:underline">Delete</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {alertHistory.length > 0 && (
              <div>
                <h3 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">Recent Firings</h3>
                <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50 uppercase text-gray-400 dark:bg-gray-800">
                      <tr>
                        <th className="px-3 py-2 text-left">Rule</th>
                        <th className="px-3 py-2 text-left">Value</th>
                        <th className="px-3 py-2 text-left">Fired At</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                      {alertHistory.map((f) => (
                        <tr key={f.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                          <td className="px-3 py-2 font-medium dark:text-gray-200">{f.rule_name}</td>
                          <td className="px-3 py-2 font-mono dark:text-gray-300">{parseFloat(f.metric_value).toFixed(4)}</td>
                          <td className="px-3 py-2 text-gray-500 dark:text-gray-400">{new Date(f.fired_at).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* ── Email Reports card ── */}
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5">
              <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-1">Email Reports</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                Weekly analytics reports (last 7 days) are automatically emailed every Monday at 07:00 UTC to all workspace admins.
                You can also send a report on demand.
              </p>
              <button
                onClick={handleSendReport}
                disabled={sendingReport}
                className="rounded bg-violet-600 px-4 py-1.5 text-sm text-white hover:bg-violet-700 disabled:opacity-50"
              >
                {sendingReport ? 'Sending…' : 'Send Report Now'}
              </button>
            </div>
          </div>
        )}
        {/* ── Integrations ──────────────────────────────────────────────────────── */}
        {activeTab === 'integrations' && (
          <div className="space-y-8 max-w-2xl">
            <div>
              <h2 className="text-xl font-semibold dark:text-white">Integrations</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Connect external services for notifications and event streaming.</p>
            </div>

            {/* ── Slack ──────────────────────────────────────────────────────── */}
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4 space-y-3">
              <div className="font-medium text-gray-800 dark:text-gray-200">Slack Webhook</div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Paste an incoming webhook URL to test connectivity before configuring budget notifications
                via <code className="rounded bg-gray-100 px-1 font-mono dark:bg-gray-800">POST /budgets/{'{id}'}/notifications</code>.
              </p>
              <form onSubmit={handleTestSlack} className="flex flex-wrap gap-2">
                <input type="url" placeholder="https://hooks.slack.com/services/..." value={slackWebhookUrl} onChange={(e) => setSlackWebhookUrl(e.target.value)} className={`flex-1 ${inputCls}`} required />
                <button type="submit" disabled={testingSlack || !slackWebhookUrl.trim()} className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
                  {testingSlack ? 'Sending…' : 'Test'}
                </button>
              </form>
              {slackTestResult && (
                <div className={`rounded border px-3 py-2 text-sm ${slackTestResult.ok ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300' : 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300'}`}>
                  {slackTestResult.ok ? '✓ Test message sent successfully.' : <>✗ Failed: {slackTestResult.error}</>}
                </div>
              )}
            </div>

            {/* ── Kafka Export ───────────────────────────────────────────────── */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-800 dark:text-gray-200">Kafka Export</div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    Stream run completions, alert firings, budget breaches, and scores to your Kafka cluster.
                  </p>
                </div>
                <button
                  onClick={() => setShowKafkaForm(v => !v)}
                  className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700"
                >
                  {showKafkaForm ? 'Cancel' : '+ Add Config'}
                </button>
              </div>

              {/* Topic routing reference */}
              <div className="rounded border border-gray-100 bg-gray-50 dark:border-gray-700 dark:bg-gray-900 p-3 text-xs text-gray-600 dark:text-gray-400 space-y-1">
                <div className="font-medium text-gray-700 dark:text-gray-300 mb-1">Topic routing</div>
                {[
                  ['run.completed / run.failed', '{prefix}.runs'],
                  ['alert.fired', '{prefix}.alerts'],
                  ['budget.breached', '{prefix}.budgets'],
                  ['score.submitted', '{prefix}.scores'],
                ].map(([ev, topic]) => (
                  <div key={ev} className="flex gap-2">
                    <code className="font-mono">{ev}</code>
                    <span className="text-gray-400">→</span>
                    <code className="font-mono text-indigo-600 dark:text-indigo-400">{topic}</code>
                  </div>
                ))}
              </div>

              {/* Add form */}
              {showKafkaForm && (
                <form onSubmit={handleCreateKafka} className="rounded-lg border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-950 p-4 space-y-3">
                  <div className="text-sm font-medium text-indigo-800 dark:text-indigo-200">New Kafka Export Config</div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Label</label>
                      <input className={inputCls} value={kafkaForm.label} onChange={e => setKafkaForm(f => ({...f, label: e.target.value}))} required />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Topic Prefix</label>
                      <input className={inputCls} value={kafkaForm.topic_prefix} onChange={e => setKafkaForm(f => ({...f, topic_prefix: e.target.value}))} required />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Bootstrap Servers</label>
                    <input className={`w-full ${inputCls}`} placeholder="broker1:9092,broker2:9092" value={kafkaForm.bootstrap_servers} onChange={e => setKafkaForm(f => ({...f, bootstrap_servers: e.target.value}))} required />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Security Protocol</label>
                      <select className={`w-full ${inputCls}`} value={kafkaForm.security_protocol} onChange={e => setKafkaForm(f => ({...f, security_protocol: e.target.value}))}>
                        {['PLAINTEXT','SSL','SASL_PLAINTEXT','SASL_SSL'].map(p => <option key={p}>{p}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">SASL Mechanism</label>
                      <select className={`w-full ${inputCls}`} value={kafkaForm.sasl_mechanism} onChange={e => setKafkaForm(f => ({...f, sasl_mechanism: e.target.value}))}>
                        <option value="">— none —</option>
                        {['PLAIN','SCRAM-SHA-256','SCRAM-SHA-512'].map(m => <option key={m}>{m}</option>)}
                      </select>
                    </div>
                  </div>

                  {(kafkaForm.security_protocol.includes('SASL') || kafkaForm.sasl_mechanism) && (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">SASL Username</label>
                        <input className={`w-full ${inputCls}`} value={kafkaForm.sasl_username} onChange={e => setKafkaForm(f => ({...f, sasl_username: e.target.value}))} />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">SASL Password</label>
                        <input type="password" className={`w-full ${inputCls}`} value={kafkaForm.sasl_password} onChange={e => setKafkaForm(f => ({...f, sasl_password: e.target.value}))} />
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Event Types</label>
                    <div className="flex flex-wrap gap-2">
                      {(['run.completed','run.failed','alert.fired','budget.breached','score.submitted'] as const).map(et => (
                        <label key={et} className="flex items-center gap-1 text-xs text-gray-700 dark:text-gray-300 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={kafkaForm.event_types.includes(et)}
                            onChange={e => setKafkaForm(f => ({
                              ...f,
                              event_types: e.target.checked ? [...f.event_types, et] : f.event_types.filter(x => x !== et)
                            }))}
                          />
                          {et}
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className="flex justify-end gap-2 pt-1">
                    <button type="button" onClick={() => setShowKafkaForm(false)} className="rounded border px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">Cancel</button>
                    <button type="submit" disabled={savingKafka || !kafkaForm.bootstrap_servers.trim()} className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
                      {savingKafka ? 'Saving…' : 'Save Config'}
                    </button>
                  </div>
                </form>
              )}

              {/* Config list */}
              {kafkaConfigs.length === 0 && !showKafkaForm ? (
                <div className="rounded border border-dashed border-gray-200 dark:border-gray-700 py-8 text-center text-sm text-gray-400 dark:text-gray-500">
                  No Kafka export configs yet. Add one to start streaming events.
                </div>
              ) : (
                <div className="space-y-3">
                  {kafkaConfigs.map(cfg => (
                    <div key={cfg.id} className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                      {/* Header */}
                      <div className="flex items-center gap-3 px-4 py-3 bg-white dark:bg-gray-900">
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-gray-800 dark:text-gray-200 text-sm truncate">{cfg.label}</div>
                          <div className="text-xs text-gray-500 dark:text-gray-400 font-mono truncate">{cfg.bootstrap_servers}</div>
                          <div className="flex flex-wrap gap-1 mt-1">
                            <span className="inline-block rounded bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-xs text-gray-600 dark:text-gray-400">{cfg.security_protocol}</span>
                            <span className="inline-block rounded bg-indigo-50 dark:bg-indigo-950 px-1.5 py-0.5 text-xs text-indigo-600 dark:text-indigo-400">prefix: {cfg.topic_prefix}</span>
                            {cfg.event_types.map(et => (
                              <span key={et} className="inline-block rounded bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 text-xs text-slate-600 dark:text-slate-400">{et}</span>
                            ))}
                          </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {/* Enable toggle */}
                          <button
                            onClick={() => handleToggleKafka(cfg)}
                            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${cfg.enabled ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'}`}
                            title={cfg.enabled ? 'Enabled — click to disable' : 'Disabled — click to enable'}
                          >
                            <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${cfg.enabled ? 'translate-x-4' : 'translate-x-0.5'}`} />
                          </button>
                          {/* Test */}
                          <button
                            onClick={() => handleTestKafka(cfg.id)}
                            disabled={testingKafkaId === cfg.id}
                            className="rounded border border-gray-200 dark:border-gray-600 px-2 py-1 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50"
                          >
                            {testingKafkaId === cfg.id ? 'Testing…' : 'Test'}
                          </button>
                          {/* Deliveries */}
                          <button
                            onClick={() => handleExpandKafka(cfg.id)}
                            className="rounded border border-gray-200 dark:border-gray-600 px-2 py-1 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                          >
                            {expandedKafkaId === cfg.id ? 'Hide log' : 'Log'}
                          </button>
                          {/* Delete */}
                          <button
                            onClick={() => handleDeleteKafka(cfg.id)}
                            className="rounded border border-red-200 dark:border-red-800 px-2 py-1 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950"
                          >
                            Delete
                          </button>
                        </div>
                      </div>

                      {/* Test result */}
                      {kafkaTestResults[cfg.id] && (
                        <div className={`px-4 py-2 text-xs border-t ${kafkaTestResults[cfg.id].ok ? 'bg-green-50 dark:bg-green-950 border-green-100 dark:border-green-900 text-green-700 dark:text-green-300' : 'bg-red-50 dark:bg-red-950 border-red-100 dark:border-red-900 text-red-700 dark:text-red-300'}`}>
                          {kafkaTestResults[cfg.id].ok
                            ? <>✓ Test event published to <code className="font-mono">{kafkaTestResults[cfg.id].topic}</code></>
                            : <>✗ {kafkaTestResults[cfg.id].error}</>
                          }
                        </div>
                      )}

                      {/* Delivery log */}
                      {expandedKafkaId === cfg.id && (
                        <div className="border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 px-4 py-3">
                          <div className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">Recent deliveries</div>
                          {(kafkaDeliveries[cfg.id] ?? []).length === 0 ? (
                            <div className="text-xs text-gray-400 dark:text-gray-500">No deliveries yet.</div>
                          ) : (
                            <table className="w-full text-xs">
                              <thead>
                                <tr className="text-gray-500 dark:text-gray-400">
                                  <th className="text-left font-medium pb-1">Event</th>
                                  <th className="text-left font-medium pb-1">Topic</th>
                                  <th className="text-left font-medium pb-1">Status</th>
                                  <th className="text-left font-medium pb-1">When</th>
                                </tr>
                              </thead>
                              <tbody>
                                {(kafkaDeliveries[cfg.id] ?? []).map(d => (
                                  <tr key={d.id} className="border-t border-gray-100 dark:border-gray-800">
                                    <td className="py-1 font-mono text-gray-700 dark:text-gray-300">{d.event_type}</td>
                                    <td className="py-1 font-mono text-indigo-600 dark:text-indigo-400">{d.topic}</td>
                                    <td className="py-1">
                                      <span className={`inline-block rounded px-1.5 py-0.5 ${d.status === 'success' ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300' : d.status === 'failed' ? 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'}`}>
                                        {d.status}
                                      </span>
                                      {d.error_detail && <span className="ml-1 text-red-500 dark:text-red-400 truncate max-w-[12rem] inline-block align-middle">{d.error_detail}</span>}
                                    </td>
                                    <td className="py-1 text-gray-400 dark:text-gray-500">{new Date(d.created_at).toLocaleString()}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Data Capture Policy ───────────────────────────────────────────────── */}
        {activeTab === 'privacy' && (
          <div className="space-y-6 max-w-2xl">
            <div>
              <h2 className="text-xl font-semibold dark:text-white">Data Capture Policy</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Controls what payload data the SDK sends to the collector. Affects privacy and storage.</p>
            </div>

            {capturePolicy && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500 dark:text-gray-400">Current:</span>
                <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">{capturePolicy.privacy_mode}</span>
                {capturePolicy.sampled_rate && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">@ {(parseFloat(capturePolicy.sampled_rate) * 100).toFixed(0)}% sample rate</span>
                )}
              </div>
            )}

            <form onSubmit={handleSavePrivacy} className="space-y-4">
              <div className="flex flex-wrap items-end gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-500 dark:text-gray-400">Privacy mode</label>
                  <select value={privacyMode} onChange={(e) => setPrivacyMode(e.target.value)} className={inputCls}>
                    <option value="METADATA_ONLY">METADATA_ONLY — tokens, model, latency only (default)</option>
                    <option value="ERRORS_ONLY">ERRORS_ONLY — metadata + error messages</option>
                    <option value="SAMPLED">SAMPLED — full payload on a % of runs</option>
                    <option value="FULL">FULL — complete request/response payloads</option>
                  </select>
                </div>
                {privacyMode === 'SAMPLED' && (
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-500 dark:text-gray-400">Sample rate (%)</label>
                    <input type="number" min="0" max="100" step="1" placeholder="10" value={sampledRate} onChange={(e) => setSampledRate(e.target.value)} className={`w-24 ${inputCls}`} required />
                  </div>
                )}
              </div>
              <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
                <strong>FULL</strong> mode stores raw prompts and completions. Ensure you have user consent and appropriate data retention policies before enabling.
              </div>
              <button type="submit" disabled={savingPrivacy} className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
                {savingPrivacy ? 'Saving…' : 'Save Policy'}
              </button>
            </form>
          </div>
        )}

        {/* ── Compliance ────────────────────────────────────────────────────────── */}
        {activeTab === 'compliance' && (
          <div className="space-y-8">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-semibold dark:text-white">Compliance</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  Tamper-evident HMAC-signed ledger snapshots and agent tool audit registry.
                </p>
              </div>
              <button
                onClick={() => { setComplianceAttempted(false) }}
                disabled={loadingCompliance}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
              >
                <svg className={`h-4 w-4 ${loadingCompliance ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                {loadingCompliance ? 'Loading…' : 'Refresh'}
              </button>
            </div>

            {/* Ledger Snapshots */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-medium dark:text-gray-100">Daily Snapshots</h3>
                <button
                  onClick={handleGenerateSnapshot}
                  disabled={generatingSnap}
                  className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {generatingSnap ? 'Generating…' : 'Generate Snapshot'}
                </button>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Each snapshot is an HMAC-SHA256 signed record of daily spend. Use Verify to confirm integrity hasn&apos;t been tampered.
              </p>
              <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase text-gray-500 dark:text-gray-400">
                    <tr>
                      <th className="px-4 py-2 text-left">Date</th>
                      <th className="px-4 py-2 text-right">Total Cost</th>
                      <th className="px-4 py-2 text-right">Calls</th>
                      <th className="px-4 py-2 text-left">Hash</th>
                      <th className="px-4 py-2 text-left">Integrity</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {loadingCompliance ? (
                      [1,2,3].map((i) => (
                        <tr key={i}>
                          {[1,2,3,4,5].map((j) => (
                            <td key={j} className="px-4 py-3">
                              <div className="h-4 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
                            </td>
                          ))}
                        </tr>
                      ))
                    ) : snapshots.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-4 py-6 text-center text-gray-400 dark:text-gray-500">
                          No snapshots yet. Click &ldquo;Generate Snapshot&rdquo; to create one.
                        </td>
                      </tr>
                    ) : snapshots.map((snap) => {
                      const vr = verifyResults[snap.snapshot_date]
                      return (
                        <tr key={snap.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                          <td className="px-4 py-2 font-mono dark:text-gray-200">{snap.snapshot_date}</td>
                          <td className="px-4 py-2 text-right font-mono dark:text-gray-200">${parseFloat(snap.total_cost_usd).toFixed(6)}</td>
                          <td className="px-4 py-2 text-right dark:text-gray-200">{snap.call_count}</td>
                          <td className="px-4 py-2 font-mono text-xs text-gray-500 dark:text-gray-400">{snap.hash.slice(0, 12)}…</td>
                          <td className="px-4 py-2">
                            {vr ? (
                              vr.match
                                ? <span className="rounded bg-green-100 dark:bg-green-900 px-2 py-0.5 text-xs text-green-700 dark:text-green-300">✓ ok</span>
                                : <span className="rounded bg-red-100 dark:bg-red-900 px-2 py-0.5 text-xs text-red-700 dark:text-red-300">⚠ {vr.status}</span>
                            ) : (
                              <button
                                onClick={() => handleVerifySnapshot(snap)}
                                disabled={verifyingSnap === snap.snapshot_date}
                                className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline disabled:opacity-50"
                              >
                                {verifyingSnap === snap.snapshot_date ? 'Verifying…' : 'Verify'}
                              </button>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Tool Registry moved to /tool-registry page */}
            <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4 text-sm text-slate-600 dark:text-slate-300">
              <p className="font-medium">Tool Registry</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Tool governance has moved to its own page.{' '}
                <a href="/tool-registry" className="text-violet-600 dark:text-violet-400 hover:underline">Go to Tool Registry →</a>
              </p>
            </div>
          </div>
        )}

        {/* ── OTLP Ingestion ────────────────────────────────────────────────────── */}
        {activeTab === 'otlp' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold dark:text-white">OTLP Ingestion</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Monitor traces received via <code className="font-mono text-xs bg-gray-100 dark:bg-gray-800 px-1 rounded">POST /v1/traces</code> from any OpenTelemetry-compatible sender.
              </p>
            </div>

            {/* Stats strip */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
              {[
                { label: '24h Batches', value: otlpStats?.last_24h.batches },
                { label: '24h Traces', value: otlpStats?.last_24h.traces },
                { label: '24h Spans', value: otlpStats?.last_24h.spans },
                { label: '7d Batches', value: otlpStats?.last_7d.batches },
                { label: '7d Traces', value: otlpStats?.last_7d.traces },
                { label: '7d Spans', value: otlpStats?.last_7d.spans },
              ].map((stat) => (
                <div key={stat.label} className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 text-center">
                  <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                    {loadingOtlp ? '…' : (stat.value ?? 0).toLocaleString()}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{stat.label}</div>
                </div>
              ))}
            </div>

            {/* Quick-start */}
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-4">
              <p className="text-sm font-medium dark:text-gray-200 mb-2">Quick start</p>
              <pre className="text-xs font-mono bg-gray-900 text-green-400 rounded p-3 overflow-x-auto whitespace-pre-wrap">{`# Install the OTel SDK + RunLedger-compatible exporter
pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http

# Set the endpoint + auth header
export OTEL_EXPORTER_OTLP_ENDPOINT=https://YOUR_API/v1/traces
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer YOUR_API_KEY"

# Or send manually with curl
curl -X POST https://YOUR_API/v1/traces \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"resourceSpans": [...]}'`}</pre>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                See <a href="https://github.com/anthropics/runledger/blob/main/docs/otlp.md" className="text-indigo-500 hover:underline" target="_blank" rel="noreferrer">docs/otlp.md</a> for the full integration guide and attribute conventions.
              </p>
            </div>

            {/* Batch history */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium dark:text-gray-200">Recent Ingest Batches</h3>
                <button
                  onClick={loadOtlp}
                  disabled={loadingOtlp}
                  className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline disabled:opacity-50"
                >
                  {loadingOtlp ? 'Loading…' : 'Refresh'}
                </button>
              </div>
              {loadingOtlp && !otlpBatches ? (
                <div className="space-y-2">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-8 rounded bg-gray-200 dark:bg-gray-700 animate-pulse" />
                  ))}
                </div>
              ) : !otlpBatches || otlpBatches.items.length === 0 ? (
                <div className="rounded border border-dashed border-gray-300 dark:border-gray-600 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  No batches received yet. Send a trace to get started.
                </div>
              ) : (
                <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400 uppercase">
                      <tr>
                        <th className="px-4 py-2 text-left">Time</th>
                        <th className="px-4 py-2 text-right">Traces</th>
                        <th className="px-4 py-2 text-right">Spans</th>
                        <th className="px-4 py-2 text-left">Status</th>
                        <th className="px-4 py-2 text-left">Error</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-700 bg-white dark:bg-gray-900">
                      {otlpBatches.items.map((b) => (
                        <tr key={b.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                          <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">
                            {b.created_at ? new Date(b.created_at).toLocaleString() : '—'}
                          </td>
                          <td className="px-4 py-2 text-right dark:text-gray-300">{b.trace_count}</td>
                          <td className="px-4 py-2 text-right dark:text-gray-300">{b.span_count}</td>
                          <td className="px-4 py-2">
                            <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                              b.status === 'accepted'
                                ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
                                : 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300'
                            }`}>
                              {b.status}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-xs text-red-500 dark:text-red-400 max-w-xs truncate">
                            {b.error ?? '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="px-4 py-2 text-xs text-gray-400 dark:text-gray-500 border-t border-gray-100 dark:border-gray-700">
                    Showing {otlpBatches.items.length} of {otlpBatches.total} batches
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Data Retention (Admin only) ───────────────────────────────────────── */}
        {activeTab === 'retention' && isWorkspaceAdmin && (
          <RetentionTab apiKey={apiKey ?? ''} />
        )}

        {/* ── Warehouse Export (Admin only) ─────────────────────────────────────── */}
        {activeTab === 'warehouse' && isWorkspaceAdmin && (
          <WarehouseTab apiKey={apiKey ?? ''} />
        )}

        {/* ── Organization (Admin only) ─────────────────────────────────────────── */}
        {activeTab === 'org' && isOrgAdmin && (
          <OrgTab apiKey={apiKey ?? ''} apiBase={apiBase} />
        )}

        {/* ── SSO / SCIM (Org admin only) ────────────────────────────────────────── */}
        {activeTab === 'sso' && isOrgAdmin && (
          <SsoTab apiKey={apiKey ?? ''} apiBase={apiBase} />
        )}

        {/* ── Git Sync ─────────────────────────────────────────────────────────── */}
        {activeTab === 'git' && apiKey && <GitTab apiKey={apiKey} />}

        {/* ── Email Notifications ──────────────────────────────────────────────── */}
        {activeTab === 'email' && (
          <div className="space-y-6">
            {loadingEmailPrefs && (
              <p className="text-sm text-gray-500 dark:text-gray-400">Loading email settings…</p>
            )}

            {/* Section 1: Email Preferences */}
            {emailPrefs && (
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
                <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">Email Notification Preferences</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Report Frequency
                    </label>
                    <select
                      className={inputCls}
                      value={emailPrefs.report_frequency}
                      onChange={(e) => setEmailPrefs({ ...emailPrefs, report_frequency: e.target.value })}
                    >
                      <option value="never">Never</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                  </div>

                  <div className="space-y-2">
                    {(
                      [
                        ['alerts_enabled', 'Alert rule firings'],
                        ['approvals_enabled', 'Approval requests & decisions'],
                        ['reconciliation_enabled', 'Invoice reconciliation complete'],
                        ['budget_alerts_enabled', 'Budget breach & runaway protection'],
                        ['billing_closed_enabled', 'Billing period closed'],
                        ['score_regression_enabled', 'Score regressions'],
                        ['dispute_flagged_enabled', 'Invoice lines disputed'],
                      ] as [keyof EmailPreference, string][]
                    ).map(([key, label]) => (
                      <label key={key} className="flex items-center gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={emailPrefs[key] as boolean}
                          onChange={(e) => setEmailPrefs({ ...emailPrefs, [key]: e.target.checked })}
                          className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>
                      </label>
                    ))}
                  </div>

                  <button
                    className="px-4 py-2 rounded bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
                    disabled={savingEmailPrefs}
                    onClick={async () => {
                      if (!apiKey || !emailPrefs) return
                      setSavingEmailPrefs(true)
                      try {
                        const updated = await updateEmailPreferences(apiKey, {
                          report_frequency: emailPrefs.report_frequency,
                          alerts_enabled: emailPrefs.alerts_enabled,
                          approvals_enabled: emailPrefs.approvals_enabled,
                          reconciliation_enabled: emailPrefs.reconciliation_enabled,
                          budget_alerts_enabled: emailPrefs.budget_alerts_enabled,
                          billing_closed_enabled: emailPrefs.billing_closed_enabled,
                          score_regression_enabled: emailPrefs.score_regression_enabled,
                          dispute_flagged_enabled: emailPrefs.dispute_flagged_enabled,
                        })
                        setEmailPrefs(updated)
                        toast.success('Email preferences saved')
                      } catch (err) {
                        console.error(err)
                        toast.error('Failed to save preferences')
                      } finally {
                        setSavingEmailPrefs(false)
                      }
                    }}
                  >
                    {savingEmailPrefs ? 'Saving…' : 'Save Preferences'}
                  </button>
                </div>
              </div>
            )}

            {/* Section 2: SMTP Test */}
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
              <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-2">Test Email Delivery</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                Sends a test email to the address associated with your session to verify SMTP is configured correctly.
              </p>
              <button
                className="px-4 py-2 rounded bg-gray-700 text-white text-sm font-medium hover:bg-gray-600 disabled:opacity-50"
                disabled={testingEmail}
                onClick={async () => {
                  if (!apiKey) return
                  setTestingEmail(true)
                  try {
                    const result = await testEmailSend(apiKey)
                    if (result.ok) {
                      toast.success('Test email sent!')
                    } else {
                      toast.error(`Failed: ${result.error ?? 'unknown error'}`)
                    }
                  } catch (err) {
                    toast.error('Failed to send test email')
                    console.error(err)
                  } finally {
                    setTestingEmail(false)
                  }
                }}
              >
                {testingEmail ? 'Sending…' : 'Send Test Email'}
              </button>
            </div>

            {/* Section 3: Email Log */}
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
              <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">Recent Email Log</h3>
              {emailLog.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">No emails sent yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 dark:border-gray-700">
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Sent At</th>
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">To</th>
                        <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Event Type</th>
                        <th className="text-left py-2 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {emailLog.map((item) => (
                        <tr key={item.id} className="border-b border-gray-100 dark:border-gray-800">
                          <td className="py-2 pr-4 text-gray-700 dark:text-gray-300 font-mono text-xs">
                            {new Date(item.sent_at).toLocaleString()}
                          </td>
                          <td className="py-2 pr-4 text-gray-700 dark:text-gray-300 text-xs">{item.to_email}</td>
                          <td className="py-2 pr-4 text-gray-500 dark:text-gray-400 text-xs font-mono">{item.event_type}</td>
                          <td className="py-2">
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                item.status === 'sent'
                                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                  : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                              }`}
                            >
                              {item.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
