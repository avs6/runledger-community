'use client'

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { DatabaseBackup, RadioTower, ShieldCheck } from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'
import type {
  BackupActionResult,
  BackupRun,
  BackupSnapshot,
  BackupTargetConfig,
  KafkaEventType,
  KafkaExportConfig,
  KafkaExportDelivery,
  KafkaSaslMechanism,
  KafkaSecurityProtocol,
  NotificationDelivery,
  NotificationDeliveryList,
  NotificationResponse,
  NotificationTestResult,
  OpsFeatureStatus,
} from '@/types/api'
import {
  createKafkaExportConfig,
  createBudgetNotification,
  deleteBudgetNotification,
  deleteKafkaExportConfig,
  getBackupConfig,
  getBackupHistory,
  getBackupSnapshots,
  getBackupStatus,
  getOpsFeatureStatus,
  listBudgetNotifications,
  listBudgetNotificationDeliveries,
  listKafkaExportConfigs,
  listKafkaExportDeliveries,
  retryKafkaExportDelivery,
  runBackupNow,
  runRestoreDrill,
  testBudgetNotification,
  testBackupConnection,
  testKafkaExportConfig,
  updateBudgetNotification,
  updateBackupConfig,
  updateKafkaExportConfig,
} from '@/lib/api'

const inputCls =
  'rounded border border-slate-300 bg-white text-gray-900 px-3 py-1.5 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500'

const kafkaEvents: KafkaEventType[] = [
  'run.started',
  'run.completed',
  'run.failed',
  'gateway.request.completed',
  'gateway.request.rejected',
  'budget.threshold_crossed',
  'budget.breached',
  'alert.fired',
  'optimization.applied',
  'route.changed',
  'mcp.tool.called',
  'mcp.tool.blocked',
  'approval.requested',
  'approval.decided',
  'email.report.sent',
  'backup.completed',
  'backup.failed',
  'compliance.export.ready',
]

const webhookEvents = ['budget.breach', 'runaway.detected'] as const

type KafkaConfigFormState = {
  label: string
  bootstrap_servers: string
  topic_prefix: string
  security_protocol: KafkaSecurityProtocol
  sasl_mechanism: KafkaSaslMechanism
  sasl_username: string
  sasl_password: string
  ssl_ca_cert: string
  single_topic_mode: boolean
  single_topic_name: string
  dead_letter_topic: string
  redaction_mode: 'none' | 'metadata_only'
  max_retries: number
  retry_backoff_seconds: number
  event_types: KafkaEventType[]
}

type WebhookFormState = {
  channel: 'webhook' | 'slack'
  destination_url: string
  events: string[]
}

function makeDefaultKafkaForm(): KafkaConfigFormState {
  return {
    label: 'Local Redpanda',
    bootstrap_servers: 'runledger-redpanda:9092',
    topic_prefix: 'runledger.dev',
    security_protocol: 'PLAINTEXT',
    sasl_mechanism: 'PLAIN',
    sasl_username: '',
    sasl_password: '',
    ssl_ca_cert: '',
    single_topic_mode: false,
    single_topic_name: 'runledger.events',
    dead_letter_topic: 'runledger.dead-letter',
    redaction_mode: 'metadata_only',
    max_retries: 3,
    retry_backoff_seconds: 15,
    event_types: ['run.started', 'run.completed', 'run.failed', 'alert.fired', 'budget.breached', 'route.changed'],
  }
}

function makeDefaultWebhookForm(): WebhookFormState {
  return {
    channel: 'webhook',
    destination_url: '',
    events: [...webhookEvents],
  }
}

function kafkaFormFromConfig(config: KafkaExportConfig): KafkaConfigFormState {
  return {
    label: config.label,
    bootstrap_servers: config.bootstrap_servers,
    topic_prefix: config.topic_prefix,
    security_protocol: config.security_protocol,
    sasl_mechanism: (config.sasl_mechanism ?? 'PLAIN') as KafkaSaslMechanism,
    sasl_username: config.sasl_username ?? '',
    sasl_password: '',
    ssl_ca_cert: config.ssl_ca_cert ?? '',
    single_topic_mode: config.single_topic_mode,
    single_topic_name: config.single_topic_name ?? 'runledger.events',
    dead_letter_topic: config.dead_letter_topic ?? '',
    redaction_mode: config.redaction_mode,
    max_retries: config.max_retries,
    retry_backoff_seconds: config.retry_backoff_seconds,
    event_types: [...config.event_types],
  }
}

function webhookFormFromNotification(notification: NotificationResponse): WebhookFormState {
  return {
    channel: notification.channel === 'slack' ? 'slack' : 'webhook',
    destination_url: notification.destination_url,
    events: [...notification.events],
  }
}

function makeDefaultBackupConfig(): BackupTargetConfig {
  const now = new Date().toISOString()
  return {
    id: 'draft',
    workspace_id: 'draft',
    provider: 's3',
    bucket: '',
    prefix: 'runledger',
    region: 'us-east-1',
    endpoint_url: 'http://localhost:9010',
    access_key_id: 'runledger',
    secret_access_key: 'runledgerminio',
    force_path_style: true,
    schedule_enabled: true,
    cadence: 'daily',
    run_hour_utc: 2,
    retention_days: 30,
    include_memory_db: true,
    include_qdrant: false,
    include_kuzu: true,
    include_skills: true,
    encryption_mode: 'server_side',
    last_verified_at: null,
    created_at: now,
    updated_at: now,
  }
}

function formatTimestamp(value: string | null) {
  if (!value) return '-'
  const dt = new Date(value)
  return Number.isNaN(dt.getTime()) ? value : dt.toLocaleString()
}

export function OrgDestinationsPanel() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { canManageOrgSettings } = useRole()

  const [backupConfig, setBackupConfig] = useState<BackupTargetConfig>(makeDefaultBackupConfig())
  const [backupRuns, setBackupRuns] = useState<BackupRun[]>([])
  const [backupSnapshots, setBackupSnapshots] = useState<BackupSnapshot[]>([])
  const [backupStatus, setBackupStatus] = useState<BackupActionResult | null>(null)
  const [opsStatus, setOpsStatus] = useState<OpsFeatureStatus | null>(null)
  const [loadingBackup, setLoadingBackup] = useState(false)
  const [savingBackup, setSavingBackup] = useState(false)
  const [testingBackup, setTestingBackup] = useState(false)
  const [runningBackup, setRunningBackup] = useState(false)
  const [runningRestoreDrillState, setRunningRestoreDrillState] = useState(false)

  const [kafkaConfigs, setKafkaConfigs] = useState<KafkaExportConfig[]>([])
  const [kafkaDeliveries, setKafkaDeliveries] = useState<Record<string, KafkaExportDelivery[]>>({})
  const [kafkaBusy, setKafkaBusy] = useState(false)
  const [editingKafkaId, setEditingKafkaId] = useState<string | null>(null)
  const [kafkaEditForm, setKafkaEditForm] = useState<KafkaConfigFormState | null>(null)
  const [webhookDestinations, setWebhookDestinations] = useState<NotificationResponse[]>([])
  const [webhookDeliveries, setWebhookDeliveries] = useState<Record<string, NotificationDelivery[]>>({})
  const [webhookBusy, setWebhookBusy] = useState(false)
  const [webhookTestResults, setWebhookTestResults] = useState<Record<string, NotificationTestResult>>({})
  const [editingWebhookId, setEditingWebhookId] = useState<string | null>(null)
  const [webhookEditForm, setWebhookEditForm] = useState<WebhookFormState | null>(null)
  const [webhookForm, setWebhookForm] = useState<WebhookFormState>(makeDefaultWebhookForm())
  const [kafkaForm, setKafkaForm] = useState<KafkaConfigFormState>(makeDefaultKafkaForm())

  const refreshKafkaDeliveries = useCallback(async (configId: string, limit = 20) => {
    if (!apiKey) return
    try {
      const deliveries = await listKafkaExportDeliveries(apiKey, configId, limit)
      setKafkaDeliveries((prev) => ({ ...prev, [configId]: deliveries.items }))
    } catch {
      setKafkaDeliveries((prev) => ({ ...prev, [configId]: [] }))
    }
  }, [apiKey])

  const loadDestinationData = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return
    setLoadingBackup(true)
    try {
      const [ops, config, history, snapshots, health, kafka, webhooks] = await Promise.all([
        getOpsFeatureStatus(apiKey),
        getBackupConfig(apiKey),
        getBackupHistory(apiKey, 10),
        getBackupSnapshots(apiKey, 10),
        getBackupStatus(apiKey),
        listKafkaExportConfigs(apiKey),
        listBudgetNotifications(apiKey),
      ])
      setOpsStatus(ops)
      setBackupConfig(config ?? makeDefaultBackupConfig())
      setBackupRuns(history.items)
      setBackupSnapshots(snapshots.items)
      setBackupStatus(health)
      setKafkaConfigs(kafka.items)
      setWebhookDestinations(webhooks.items)
      const webhookPairs = await Promise.all(
        webhooks.items.slice(0, 5).map(async (item) => {
          try {
            const deliveries: NotificationDeliveryList = await listBudgetNotificationDeliveries(apiKey, item.id, 10)
            return [item.id, deliveries.items] as const
          } catch {
            return [item.id, []] as const
          }
        })
      )
      setWebhookDeliveries(Object.fromEntries(webhookPairs))

      const deliveryPairs = await Promise.all(
        kafka.items.slice(0, 3).map(async (item) => {
          try {
            const deliveries = await listKafkaExportDeliveries(apiKey, item.id, 20)
            return [item.id, deliveries.items] as const
          } catch {
            return [item.id, []] as const
          }
        })
      )
      setKafkaDeliveries(Object.fromEntries(deliveryPairs))
    } catch (err) {
      console.error(err)
      toast.error('Failed to load organization destinations')
    } finally {
      setLoadingBackup(false)
    }
  }, [apiKey, canManageOrgSettings])

  useEffect(() => {
    void loadDestinationData()
  }, [loadDestinationData])

  function toggleKafkaEvent(eventType: KafkaEventType) {
    setKafkaForm((prev) => {
      const exists = prev.event_types.includes(eventType)
      return {
        ...prev,
        event_types: exists
          ? prev.event_types.filter((item) => item !== eventType)
          : [...prev.event_types, eventType],
      }
    })
  }

  function toggleKafkaEditEvent(eventType: KafkaEventType) {
    setKafkaEditForm((prev) => {
      if (!prev) return prev
      const exists = prev.event_types.includes(eventType)
      return {
        ...prev,
        event_types: exists
          ? prev.event_types.filter((item) => item !== eventType)
          : [...prev.event_types, eventType],
      }
    })
  }

  function toggleWebhookEvent(eventType: string) {
    setWebhookForm((prev) => ({
      ...prev,
      events: prev.events.includes(eventType)
        ? prev.events.filter((item) => item !== eventType)
        : [...prev.events, eventType],
    }))
  }

  function toggleWebhookEditEvent(eventType: string) {
    setWebhookEditForm((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        events: prev.events.includes(eventType)
          ? prev.events.filter((item) => item !== eventType)
          : [...prev.events, eventType],
      }
    })
  }

  async function handleSaveBackup() {
    if (!apiKey) return
    setSavingBackup(true)
    try {
      const updated = await updateBackupConfig(apiKey, {
        provider: 's3',
        bucket: backupConfig.bucket,
        prefix: backupConfig.prefix,
        region: backupConfig.region,
        endpoint_url: backupConfig.endpoint_url,
        access_key_id: backupConfig.access_key_id,
        secret_access_key: backupConfig.secret_access_key,
        force_path_style: backupConfig.force_path_style,
        schedule_enabled: backupConfig.schedule_enabled,
        cadence: backupConfig.cadence,
        run_hour_utc: backupConfig.run_hour_utc,
        retention_days: backupConfig.retention_days,
        include_memory_db: backupConfig.include_memory_db,
        include_qdrant: backupConfig.include_qdrant,
        include_kuzu: backupConfig.include_kuzu,
        include_skills: backupConfig.include_skills,
        encryption_mode: backupConfig.encryption_mode,
      })
      setBackupConfig(updated)
      toast.success('Organization storage override updated')
      await loadDestinationData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to save storage override')
    } finally {
      setSavingBackup(false)
    }
  }

  async function handleCreateKafka(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setKafkaBusy(true)
    try {
      await createKafkaExportConfig(apiKey, kafkaForm)
      toast.success('Kafka export config created')
      await loadDestinationData()
    } catch (err) {
      toast.error(`Kafka config failed: ${String(err)}`)
    } finally {
      setKafkaBusy(false)
    }
  }

  async function handleCreateWebhook(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    setWebhookBusy(true)
    try {
      await createBudgetNotification(apiKey, webhookForm)
      toast.success(`${webhookForm.channel === 'slack' ? 'Slack' : 'Webhook'} destination created`)
      setWebhookForm(makeDefaultWebhookForm())
      await loadDestinationData()
    } catch (err) {
      toast.error(`Webhook destination failed: ${String(err)}`)
    } finally {
      setWebhookBusy(false)
    }
  }

  async function handleTestKafka(config: KafkaExportConfig) {
    if (!apiKey) return
    setKafkaBusy(true)
    try {
      const result = await testKafkaExportConfig(apiKey, config.id)
      if (result.ok) {
        toast.success(`Kafka test delivered to ${result.topic}`)
      } else {
        toast.error(`Kafka test failed: ${result.error}`)
      }
      await refreshKafkaDeliveries(config.id)
    } catch (err) {
      toast.error(`Kafka test failed: ${String(err)}`)
    } finally {
      setKafkaBusy(false)
    }
  }

  async function handleToggleKafka(config: KafkaExportConfig) {
    if (!apiKey) return
    setKafkaBusy(true)
    try {
      await updateKafkaExportConfig(apiKey, config.id, { enabled: !config.enabled })
      toast.success(config.enabled ? 'Kafka export disabled' : 'Kafka export enabled')
      await loadDestinationData()
    } catch (err) {
      toast.error(`Kafka update failed: ${String(err)}`)
    } finally {
      setKafkaBusy(false)
    }
  }

  async function handleStartEditKafka(config: KafkaExportConfig) {
    setEditingKafkaId(config.id)
    setKafkaEditForm(kafkaFormFromConfig(config))
  }

  async function handleSaveKafkaEdit(configId: string) {
    if (!apiKey || !kafkaEditForm) return
    setKafkaBusy(true)
    try {
      await updateKafkaExportConfig(apiKey, configId, {
        label: kafkaEditForm.label,
        bootstrap_servers: kafkaEditForm.bootstrap_servers,
        topic_prefix: kafkaEditForm.topic_prefix,
        security_protocol: kafkaEditForm.security_protocol,
        sasl_mechanism: kafkaEditForm.sasl_mechanism,
        sasl_username: kafkaEditForm.sasl_username || null,
        sasl_password: kafkaEditForm.sasl_password || null,
        ssl_ca_cert: kafkaEditForm.ssl_ca_cert || null,
        single_topic_mode: kafkaEditForm.single_topic_mode,
        single_topic_name: kafkaEditForm.single_topic_mode ? kafkaEditForm.single_topic_name : null,
        dead_letter_topic: kafkaEditForm.dead_letter_topic || null,
        redaction_mode: kafkaEditForm.redaction_mode,
        max_retries: kafkaEditForm.max_retries,
        retry_backoff_seconds: kafkaEditForm.retry_backoff_seconds,
        event_types: kafkaEditForm.event_types,
      })
      toast.success('Kafka export config updated')
      setEditingKafkaId(null)
      setKafkaEditForm(null)
      await loadDestinationData()
    } catch (err) {
      toast.error(`Kafka update failed: ${String(err)}`)
    } finally {
      setKafkaBusy(false)
    }
  }

  async function handleDeleteKafka(config: KafkaExportConfig) {
    if (!apiKey) return
    setKafkaBusy(true)
    try {
      await deleteKafkaExportConfig(apiKey, config.id)
      toast.success('Kafka export config deleted')
      await loadDestinationData()
    } catch (err) {
      toast.error(`Kafka delete failed: ${String(err)}`)
    } finally {
      setKafkaBusy(false)
    }
  }

  async function handleRetryKafkaDelivery(config: KafkaExportConfig, delivery: KafkaExportDelivery) {
    if (!apiKey) return
    setKafkaBusy(true)
    try {
      await retryKafkaExportDelivery(apiKey, config.id, delivery.id)
      toast.success(`Retry queued for ${delivery.event_type}`)
      await refreshKafkaDeliveries(config.id)
    } catch (err) {
      toast.error(`Kafka retry failed: ${String(err)}`)
    } finally {
      setKafkaBusy(false)
    }
  }

  async function handleToggleWebhook(notification: NotificationResponse) {
    if (!apiKey) return
    setWebhookBusy(true)
    try {
      await updateBudgetNotification(apiKey, notification.id, { is_active: !notification.is_active })
      toast.success(notification.is_active ? 'Webhook destination disabled' : 'Webhook destination enabled')
      await loadDestinationData()
    } catch (err) {
      toast.error(`Webhook update failed: ${String(err)}`)
    } finally {
      setWebhookBusy(false)
    }
  }

  function handleStartEditWebhook(notification: NotificationResponse) {
    setEditingWebhookId(notification.id)
    setWebhookEditForm(webhookFormFromNotification(notification))
  }

  async function handleSaveWebhookEdit(notificationId: string) {
    if (!apiKey || !webhookEditForm) return
    setWebhookBusy(true)
    try {
      await updateBudgetNotification(apiKey, notificationId, {
        destination_url: webhookEditForm.destination_url,
        events: webhookEditForm.events,
      })
      toast.success('Webhook destination updated')
      setEditingWebhookId(null)
      setWebhookEditForm(null)
      await loadDestinationData()
    } catch (err) {
      toast.error(`Webhook update failed: ${String(err)}`)
    } finally {
      setWebhookBusy(false)
    }
  }

  async function handleDeleteWebhook(notification: NotificationResponse) {
    if (!apiKey) return
    setWebhookBusy(true)
    try {
      await deleteBudgetNotification(apiKey, notification.id)
      toast.success('Webhook destination deleted')
      await loadDestinationData()
    } catch (err) {
      toast.error(`Webhook delete failed: ${String(err)}`)
    } finally {
      setWebhookBusy(false)
    }
  }

  async function handleTestWebhook(notification: NotificationResponse) {
    if (!apiKey) return
    setWebhookBusy(true)
    try {
      const result = await testBudgetNotification(apiKey, notification.id)
      setWebhookTestResults((prev) => ({ ...prev, [notification.id]: result }))
      try {
        const deliveries = await listBudgetNotificationDeliveries(apiKey, notification.id, 10)
        setWebhookDeliveries((prev) => ({ ...prev, [notification.id]: deliveries.items }))
      } catch {}
      result.ok
        ? toast.success(`${notification.channel === 'slack' ? 'Slack' : 'Webhook'} test sent`)
        : toast.error(result.error ?? 'Webhook test failed')
    } catch (err) {
      toast.error(`Webhook test failed: ${String(err)}`)
    } finally {
      setWebhookBusy(false)
    }
  }

  if (!canManageOrgSettings) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-950">Organization Destinations</h2>
        <p className="mt-2 text-sm text-slate-500">
          Destination management requires the org admin or org manager role.
        </p>
      </div>
    )
  }

  const backupEnabled = opsStatus?.backup_enabled ?? false

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-950">Organization Destinations</h2>
        <p className="mt-2 text-sm text-slate-500">
          Own the org-scoped destinations here: workspace storage overrides for backup and export flows, plus Kafka-compatible streaming for downstream systems.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="rounded-xl bg-blue-50 p-2 text-blue-700">
            <DatabaseBackup className="h-4 w-4" />
          </span>
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-semibold text-slate-950">Storage Override</h3>
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${backupEnabled ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
                {backupEnabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-500">
              Each organization can bring its own S3-compatible target or follow the platform default pattern with an org-specific bucket and prefix.
            </p>
            {backupStatus && (
              <div className={`mt-3 rounded-xl border px-4 py-3 text-sm ${backupStatus.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-amber-200 bg-amber-50 text-amber-900'}`}>
                <div className="font-semibold">{backupStatus.ok ? 'Storage health looks good' : 'Storage needs attention'}</div>
                <p className="mt-1">{backupStatus.message}</p>
              </div>
            )}
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="text-xs font-semibold text-slate-600">
            Bucket
            <input className={`mt-1 w-full ${inputCls}`} value={backupConfig.bucket} onChange={(e) => setBackupConfig((prev) => ({ ...prev, bucket: e.target.value }))} />
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Prefix
            <input className={`mt-1 w-full ${inputCls}`} value={backupConfig.prefix ?? ''} onChange={(e) => setBackupConfig((prev) => ({ ...prev, prefix: e.target.value }))} />
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Region
            <input className={`mt-1 w-full ${inputCls}`} value={backupConfig.region ?? ''} onChange={(e) => setBackupConfig((prev) => ({ ...prev, region: e.target.value }))} />
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Endpoint
            <input className={`mt-1 w-full ${inputCls}`} value={backupConfig.endpoint_url ?? ''} onChange={(e) => setBackupConfig((prev) => ({ ...prev, endpoint_url: e.target.value }))} />
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Access key
            <input className={`mt-1 w-full ${inputCls}`} value={backupConfig.access_key_id ?? ''} onChange={(e) => setBackupConfig((prev) => ({ ...prev, access_key_id: e.target.value }))} />
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Secret key
            <input className={`mt-1 w-full ${inputCls}`} value={backupConfig.secret_access_key ?? ''} onChange={(e) => setBackupConfig((prev) => ({ ...prev, secret_access_key: e.target.value }))} />
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Schedule
            <select className={`mt-1 w-full ${inputCls}`} value={backupConfig.cadence} onChange={(e) => setBackupConfig((prev) => ({ ...prev, cadence: e.target.value as BackupTargetConfig['cadence'] }))}>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Run hour (UTC)
            <input type="number" min={0} max={23} className={`mt-1 w-full ${inputCls}`} value={backupConfig.run_hour_utc} onChange={(e) => setBackupConfig((prev) => ({ ...prev, run_hour_utc: Number(e.target.value || 0) }))} />
          </label>
        </div>

        <div className="mt-4 flex flex-wrap gap-4">
          {[
            ['schedule_enabled', 'Schedule enabled'],
            ['force_path_style', 'Force path style'],
            ['include_memory_db', 'Include memory DB'],
            ['include_qdrant', 'Include Qdrant'],
            ['include_kuzu', 'Include Kuzu'],
            ['include_skills', 'Include skills'],
          ].map(([field, label]) => (
            <label key={field} className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={Boolean(backupConfig[field as keyof BackupTargetConfig])}
                onChange={(e) => setBackupConfig((prev) => ({ ...prev, [field]: e.target.checked } as BackupTargetConfig))}
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              {label}
            </label>
          ))}
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <button className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50" disabled={savingBackup || !backupConfig.bucket.trim()} onClick={() => void handleSaveBackup()}>
            {savingBackup ? 'Saving...' : 'Save storage override'}
          </button>
          <button
            className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            disabled={testingBackup || !backupEnabled}
            onClick={async () => {
              if (!apiKey) return
              setTestingBackup(true)
              try {
                const result = await testBackupConnection(apiKey)
                setBackupStatus(result)
                result.ok ? toast.success('Storage connectivity verified') : toast.error(result.message)
              } catch (err) {
                console.error(err)
                toast.error('Backup connectivity test failed')
              } finally {
                setTestingBackup(false)
              }
            }}
          >
            {testingBackup ? 'Testing...' : 'Test connection'}
          </button>
          <button
            className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            disabled={runningBackup || !backupEnabled}
            onClick={async () => {
              if (!apiKey) return
              setRunningBackup(true)
              try {
                await runBackupNow(apiKey)
                toast.success('Backup run queued')
                await loadDestinationData()
              } catch (err) {
                console.error(err)
                toast.error('Failed to queue backup')
              } finally {
                setRunningBackup(false)
              }
            }}
          >
            {runningBackup ? 'Queueing...' : 'Run backup now'}
          </button>
          <button
            className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            disabled={runningRestoreDrillState || !backupEnabled}
            onClick={async () => {
              if (!apiKey) return
              setRunningRestoreDrillState(true)
              try {
                await runRestoreDrill(apiKey)
                toast.success('Restore drill queued')
                await loadDestinationData()
              } catch (err) {
                console.error(err)
                toast.error('Failed to queue restore drill')
              } finally {
                setRunningRestoreDrillState(false)
              }
            }}
          >
            {runningRestoreDrillState ? 'Queueing...' : 'Run restore drill'}
          </button>
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-2">
          <div className="overflow-hidden rounded-xl border border-slate-200">
            <div className="border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-900">Recent backup runs</div>
            <table className="w-full text-sm">
              <thead className="bg-white text-xs uppercase tracking-[0.08em] text-slate-500">
                <tr>
                  <th className="px-3 py-2 text-left">When</th>
                  <th className="px-3 py-2 text-left">Mode</th>
                  <th className="px-3 py-2 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loadingBackup ? (
                  <tr><td colSpan={3} className="px-3 py-4 text-center text-slate-500">Loading...</td></tr>
                ) : backupRuns.length === 0 ? (
                  <tr><td colSpan={3} className="px-3 py-4 text-center text-slate-500">No backup runs yet.</td></tr>
                ) : (
                  backupRuns.map((run) => (
                    <tr key={run.id}>
                      <td className="px-3 py-2 text-slate-600">{formatTimestamp(run.created_at)}</td>
                      <td className="px-3 py-2 text-slate-600">{run.trigger_mode}</td>
                      <td className="px-3 py-2 text-slate-600">{run.status}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200">
            <div className="border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-900">Recent snapshots</div>
            <table className="w-full text-sm">
              <thead className="bg-white text-xs uppercase tracking-[0.08em] text-slate-500">
                <tr>
                  <th className="px-3 py-2 text-left">When</th>
                  <th className="px-3 py-2 text-left">Bucket</th>
                  <th className="px-3 py-2 text-left">Integrity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loadingBackup ? (
                  <tr><td colSpan={3} className="px-3 py-4 text-center text-slate-500">Loading...</td></tr>
                ) : backupSnapshots.length === 0 ? (
                  <tr><td colSpan={3} className="px-3 py-4 text-center text-slate-500">No snapshots recorded yet.</td></tr>
                ) : (
                  backupSnapshots.map((snapshot) => (
                    <tr key={snapshot.id}>
                      <td className="px-3 py-2 text-slate-600">{formatTimestamp(snapshot.created_at)}</td>
                      <td className="px-3 py-2 text-slate-600">{snapshot.bucket}</td>
                      <td className="px-3 py-2 text-slate-600">{snapshot.integrity_status}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="rounded-xl bg-blue-50 p-2 text-blue-700">
            <RadioTower className="h-4 w-4" />
          </span>
          <div className="flex-1">
            <h3 className="text-base font-semibold text-slate-950">Kafka / Redpanda Export</h3>
            <p className="mt-1 text-sm text-slate-500">
              Stream run, gateway, governance, approval, and backup events into org-owned Kafka-compatible infrastructure.
            </p>
          </div>
        </div>

        <form onSubmit={handleCreateKafka} className="mt-5 rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
          <div className="grid gap-3 lg:grid-cols-4">
            <label className="text-xs font-semibold text-slate-600">
              Label
              <input className={`mt-1 w-full ${inputCls}`} value={kafkaForm.label} onChange={(e) => setKafkaForm((prev) => ({ ...prev, label: e.target.value }))} />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              Bootstrap servers
              <input className={`mt-1 w-full ${inputCls}`} value={kafkaForm.bootstrap_servers} onChange={(e) => setKafkaForm((prev) => ({ ...prev, bootstrap_servers: e.target.value }))} />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              Topic prefix
              <input className={`mt-1 w-full ${inputCls}`} value={kafkaForm.topic_prefix} onChange={(e) => setKafkaForm((prev) => ({ ...prev, topic_prefix: e.target.value }))} />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              Protocol
              <select className={`mt-1 w-full ${inputCls}`} value={kafkaForm.security_protocol} onChange={(e) => setKafkaForm((prev) => ({ ...prev, security_protocol: e.target.value as KafkaSecurityProtocol }))}>
                <option value="PLAINTEXT">PLAINTEXT</option>
                <option value="SSL">SSL</option>
                <option value="SASL_PLAINTEXT">SASL_PLAINTEXT</option>
                <option value="SASL_SSL">SASL_SSL</option>
              </select>
            </label>
          </div>

          <div className="mt-4 grid gap-3 lg:grid-cols-4">
            <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600">
              <input type="checkbox" checked={kafkaForm.single_topic_mode} onChange={(e) => setKafkaForm((prev) => ({ ...prev, single_topic_mode: e.target.checked }))} className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
              Single-topic mode
            </label>
            <label className="text-xs font-semibold text-slate-600 lg:col-span-2">
              Shared topic
              <input className={`mt-1 w-full ${inputCls}`} value={kafkaForm.single_topic_name} onChange={(e) => setKafkaForm((prev) => ({ ...prev, single_topic_name: e.target.value }))} disabled={!kafkaForm.single_topic_mode} />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              Dead-letter topic
              <input className={`mt-1 w-full ${inputCls}`} value={kafkaForm.dead_letter_topic} onChange={(e) => setKafkaForm((prev) => ({ ...prev, dead_letter_topic: e.target.value }))} />
            </label>
          </div>

          <div className="mt-4 grid gap-3 lg:grid-cols-4">
            <label className="text-xs font-semibold text-slate-600">
              Redaction
              <select className={`mt-1 w-full ${inputCls}`} value={kafkaForm.redaction_mode} onChange={(e) => setKafkaForm((prev) => ({ ...prev, redaction_mode: e.target.value as 'none' | 'metadata_only' }))}>
                <option value="none">none</option>
                <option value="metadata_only">metadata_only</option>
              </select>
            </label>
            <label className="text-xs font-semibold text-slate-600">
              Max retries
              <input type="number" min={0} max={10} className={`mt-1 w-full ${inputCls}`} value={kafkaForm.max_retries} onChange={(e) => setKafkaForm((prev) => ({ ...prev, max_retries: Number(e.target.value || 0) }))} />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              Retry backoff (s)
              <input type="number" min={0} max={300} className={`mt-1 w-full ${inputCls}`} value={kafkaForm.retry_backoff_seconds} onChange={(e) => setKafkaForm((prev) => ({ ...prev, retry_backoff_seconds: Number(e.target.value || 0) }))} />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              SASL mechanism
              <select className={`mt-1 w-full ${inputCls}`} value={kafkaForm.sasl_mechanism} onChange={(e) => setKafkaForm((prev) => ({ ...prev, sasl_mechanism: e.target.value as KafkaSaslMechanism }))}>
                <option value="PLAIN">PLAIN</option>
                <option value="SCRAM-SHA-256">SCRAM-SHA-256</option>
                <option value="SCRAM-SHA-512">SCRAM-SHA-512</option>
              </select>
            </label>
          </div>

          <div className="mt-4 grid gap-3 lg:grid-cols-3">
            <label className="text-xs font-semibold text-slate-600">
              SASL username
              <input className={`mt-1 w-full ${inputCls}`} value={kafkaForm.sasl_username} onChange={(e) => setKafkaForm((prev) => ({ ...prev, sasl_username: e.target.value }))} />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              SASL password or secret ref
              <input className={`mt-1 w-full ${inputCls}`} value={kafkaForm.sasl_password} onChange={(e) => setKafkaForm((prev) => ({ ...prev, sasl_password: e.target.value }))} />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              SSL CA cert
              <input className={`mt-1 w-full ${inputCls}`} value={kafkaForm.ssl_ca_cert} onChange={(e) => setKafkaForm((prev) => ({ ...prev, ssl_ca_cert: e.target.value }))} />
            </label>
          </div>

          <div className="mt-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Events</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {kafkaEvents.map((eventType) => {
                const active = kafkaForm.event_types.includes(eventType)
                return (
                  <button
                    key={eventType}
                    type="button"
                    onClick={() => toggleKafkaEvent(eventType)}
                    className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${active ? 'border-blue-300 bg-blue-100 text-blue-700' : 'border-slate-200 bg-white text-slate-500 hover:bg-blue-50'}`}
                  >
                    {eventType}
                  </button>
                )
              })}
            </div>
          </div>

          <button
            type="submit"
            disabled={kafkaBusy || !kafkaForm.label.trim() || !kafkaForm.bootstrap_servers.trim() || kafkaForm.event_types.length === 0 || (kafkaForm.single_topic_mode && !kafkaForm.single_topic_name.trim())}
            className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
          >
            Create Kafka export
          </button>
        </form>

        <div className="mt-5 space-y-3">
          {kafkaConfigs.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">
              No Kafka export configs yet.
            </div>
          ) : (
            kafkaConfigs.map((config) => (
              <div key={config.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-slate-950">{config.label}</h3>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${config.enabled ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
                        {config.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">{config.security_protocol}</span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      {config.bootstrap_servers} / {config.single_topic_mode ? (config.single_topic_name ?? 'single topic') : config.topic_prefix}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {config.event_types.map((eventType) => (
                        <span key={eventType} className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700">{eventType}</span>
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button type="button" disabled={kafkaBusy} onClick={() => void handleTestKafka(config)} className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-100 disabled:opacity-50">
                      Test
                    </button>
                    <button type="button" disabled={kafkaBusy} onClick={() => void handleStartEditKafka(config)} className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">
                      Edit
                    </button>
                    <button type="button" disabled={kafkaBusy} onClick={() => void refreshKafkaDeliveries(config.id)} className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">
                      Refresh history
                    </button>
                    <button type="button" disabled={kafkaBusy} onClick={() => void handleToggleKafka(config)} className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">
                      {config.enabled ? 'Disable' : 'Enable'}
                    </button>
                    <button type="button" disabled={kafkaBusy} onClick={() => void handleDeleteKafka(config)} className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100 disabled:opacity-50">
                      Delete
                    </button>
                  </div>
                </div>

                {editingKafkaId === config.id && kafkaEditForm && (
                  <div className="mt-4 rounded-2xl border border-blue-200 bg-blue-50/60 p-4">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <div>
                        <h4 className="text-sm font-semibold text-slate-950">Edit Kafka export</h4>
                        <p className="mt-1 text-xs text-slate-500">Update the destination, delivery policy, and subscribed event set in place.</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setEditingKafkaId(null)
                          setKafkaEditForm(null)
                        }}
                        className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        Cancel
                      </button>
                    </div>

                    <div className="grid gap-3 lg:grid-cols-4">
                      <label className="text-xs font-semibold text-slate-600">
                        Label
                        <input className={`mt-1 w-full ${inputCls}`} value={kafkaEditForm.label} onChange={(e) => setKafkaEditForm((prev) => prev ? { ...prev, label: e.target.value } : prev)} />
                      </label>
                      <label className="text-xs font-semibold text-slate-600">
                        Bootstrap servers
                        <input className={`mt-1 w-full ${inputCls}`} value={kafkaEditForm.bootstrap_servers} onChange={(e) => setKafkaEditForm((prev) => prev ? { ...prev, bootstrap_servers: e.target.value } : prev)} />
                      </label>
                      <label className="text-xs font-semibold text-slate-600">
                        Topic prefix
                        <input className={`mt-1 w-full ${inputCls}`} value={kafkaEditForm.topic_prefix} onChange={(e) => setKafkaEditForm((prev) => prev ? { ...prev, topic_prefix: e.target.value } : prev)} disabled={kafkaEditForm.single_topic_mode} />
                      </label>
                      <label className="text-xs font-semibold text-slate-600">
                        Security protocol
                        <select className={`mt-1 w-full ${inputCls}`} value={kafkaEditForm.security_protocol} onChange={(e) => setKafkaEditForm((prev) => prev ? { ...prev, security_protocol: e.target.value as KafkaSecurityProtocol } : prev)}>
                          <option value="PLAINTEXT">PLAINTEXT</option>
                          <option value="SSL">SSL</option>
                          <option value="SASL_PLAINTEXT">SASL_PLAINTEXT</option>
                          <option value="SASL_SSL">SASL_SSL</option>
                        </select>
                      </label>
                    </div>

                    <div className="mt-3 grid gap-3 lg:grid-cols-4">
                      <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600">
                        <input type="checkbox" checked={kafkaEditForm.single_topic_mode} onChange={(e) => setKafkaEditForm((prev) => prev ? { ...prev, single_topic_mode: e.target.checked } : prev)} className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
                        Single-topic mode
                      </label>
                      <label className="text-xs font-semibold text-slate-600 lg:col-span-2">
                        Shared topic
                        <input className={`mt-1 w-full ${inputCls}`} value={kafkaEditForm.single_topic_name} onChange={(e) => setKafkaEditForm((prev) => prev ? { ...prev, single_topic_name: e.target.value } : prev)} disabled={!kafkaEditForm.single_topic_mode} />
                      </label>
                      <label className="text-xs font-semibold text-slate-600">
                        Dead-letter topic
                        <input className={`mt-1 w-full ${inputCls}`} value={kafkaEditForm.dead_letter_topic} onChange={(e) => setKafkaEditForm((prev) => prev ? { ...prev, dead_letter_topic: e.target.value } : prev)} />
                      </label>
                    </div>

                    <div className="mt-3 grid gap-3 lg:grid-cols-4">
                      <label className="text-xs font-semibold text-slate-600">
                        Redaction
                        <select className={`mt-1 w-full ${inputCls}`} value={kafkaEditForm.redaction_mode} onChange={(e) => setKafkaEditForm((prev) => prev ? { ...prev, redaction_mode: e.target.value as 'none' | 'metadata_only' } : prev)}>
                          <option value="none">none</option>
                          <option value="metadata_only">metadata_only</option>
                        </select>
                      </label>
                      <label className="text-xs font-semibold text-slate-600">
                        Max retries
                        <input type="number" min={0} max={10} className={`mt-1 w-full ${inputCls}`} value={kafkaEditForm.max_retries} onChange={(e) => setKafkaEditForm((prev) => prev ? { ...prev, max_retries: Number(e.target.value || 0) } : prev)} />
                      </label>
                      <label className="text-xs font-semibold text-slate-600">
                        Retry backoff (s)
                        <input type="number" min={0} max={300} className={`mt-1 w-full ${inputCls}`} value={kafkaEditForm.retry_backoff_seconds} onChange={(e) => setKafkaEditForm((prev) => prev ? { ...prev, retry_backoff_seconds: Number(e.target.value || 0) } : prev)} />
                      </label>
                      <label className="text-xs font-semibold text-slate-600">
                        SASL mechanism
                        <select className={`mt-1 w-full ${inputCls}`} value={kafkaEditForm.sasl_mechanism} onChange={(e) => setKafkaEditForm((prev) => prev ? { ...prev, sasl_mechanism: e.target.value as KafkaSaslMechanism } : prev)}>
                          <option value="PLAIN">PLAIN</option>
                          <option value="SCRAM-SHA-256">SCRAM-SHA-256</option>
                          <option value="SCRAM-SHA-512">SCRAM-SHA-512</option>
                        </select>
                      </label>
                    </div>

                    <div className="mt-3 grid gap-3 lg:grid-cols-3">
                      <label className="text-xs font-semibold text-slate-600">
                        SASL username
                        <input className={`mt-1 w-full ${inputCls}`} value={kafkaEditForm.sasl_username} onChange={(e) => setKafkaEditForm((prev) => prev ? { ...prev, sasl_username: e.target.value } : prev)} />
                      </label>
                      <label className="text-xs font-semibold text-slate-600">
                        SASL password or secret ref
                        <input className={`mt-1 w-full ${inputCls}`} value={kafkaEditForm.sasl_password} onChange={(e) => setKafkaEditForm((prev) => prev ? { ...prev, sasl_password: e.target.value } : prev)} placeholder="Leave blank to keep current secret" />
                      </label>
                      <label className="text-xs font-semibold text-slate-600">
                        SSL CA cert
                        <input className={`mt-1 w-full ${inputCls}`} value={kafkaEditForm.ssl_ca_cert} onChange={(e) => setKafkaEditForm((prev) => prev ? { ...prev, ssl_ca_cert: e.target.value } : prev)} />
                      </label>
                    </div>

                    <div className="mt-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Events</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {kafkaEvents.map((eventType) => {
                          const active = kafkaEditForm.event_types.includes(eventType)
                          return (
                            <button
                              key={eventType}
                              type="button"
                              onClick={() => toggleKafkaEditEvent(eventType)}
                              className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${active ? 'border-blue-300 bg-blue-100 text-blue-700' : 'border-slate-200 bg-white text-slate-500 hover:bg-blue-50'}`}
                            >
                              {eventType}
                            </button>
                          )
                        })}
                      </div>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={kafkaBusy || !kafkaEditForm.label.trim() || !kafkaEditForm.bootstrap_servers.trim() || kafkaEditForm.event_types.length === 0}
                        onClick={() => void handleSaveKafkaEdit(config.id)}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
                      >
                        Save changes
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setEditingKafkaId(null)
                          setKafkaEditForm(null)
                        }}
                        className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                <div className="mt-4 overflow-hidden rounded-xl border border-slate-200">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-slate-50 text-left text-slate-500">
                        <th className="px-3 py-2 font-semibold">Event</th>
                        <th className="px-3 py-2 font-semibold">Topic</th>
                        <th className="px-3 py-2 font-semibold">Status</th>
                        <th className="px-3 py-2 font-semibold">Attempts</th>
                        <th className="px-3 py-2 font-semibold">Error</th>
                        <th className="px-3 py-2 font-semibold">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {(kafkaDeliveries[config.id] ?? []).length === 0 ? (
                        <tr><td colSpan={6} className="px-3 py-4 text-center text-slate-500">No deliveries yet.</td></tr>
                      ) : (
                        (kafkaDeliveries[config.id] ?? []).map((delivery) => (
                          <tr key={delivery.id}>
                            <td className="px-3 py-2 font-medium text-slate-700">{delivery.event_type}</td>
                            <td className="px-3 py-2 text-slate-500">{delivery.topic}</td>
                            <td className="px-3 py-2 text-slate-500">{delivery.status}</td>
                            <td className="px-3 py-2 text-slate-500">{delivery.attempt}</td>
                            <td className="max-w-sm truncate px-3 py-2 text-slate-500">{delivery.error_detail ?? '-'}</td>
                            <td className="px-3 py-2">
                              <button
                                type="button"
                                disabled={kafkaBusy || delivery.status === 'success'}
                                onClick={() => void handleRetryKafkaDelivery(config, delivery)}
                                className="rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                              >
                                Retry now
                              </button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="rounded-xl bg-blue-50 p-2 text-blue-700">
            <ShieldCheck className="h-4 w-4" />
          </span>
          <div className="flex-1">
            <h3 className="text-base font-semibold text-slate-950">Webhook Export Destinations</h3>
            <p className="mt-1 text-sm text-slate-500">
              Export-only webhooks live alongside Kafka and storage because they are org-owned outbound destinations. Slack destinations reuse the same surface, while inbound webhook ingest remains part of the integrations and ingest path.
            </p>
          </div>
        </div>

        <form onSubmit={handleCreateWebhook} className="mt-5 rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
          <div className="grid gap-3 md:grid-cols-3">
            <label className="text-xs font-semibold text-slate-600">
              Channel
              <select className={`mt-1 w-full ${inputCls}`} value={webhookForm.channel} onChange={(e) => setWebhookForm((prev) => ({ ...prev, channel: e.target.value as 'webhook' | 'slack' }))}>
                <option value="webhook">Generic webhook</option>
                <option value="slack">Slack</option>
              </select>
            </label>
            <label className="text-xs font-semibold text-slate-600 md:col-span-2">
              Destination URL
              <input className={`mt-1 w-full ${inputCls}`} value={webhookForm.destination_url} onChange={(e) => setWebhookForm((prev) => ({ ...prev, destination_url: e.target.value }))} placeholder={webhookForm.channel === 'slack' ? 'https://hooks.slack.com/services/...' : 'https://example.com/runledger-webhook'} />
            </label>
          </div>
          <div className="mt-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Events</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {['budget.breach', 'runaway.detected'].map((eventType) => {
                const active = webhookForm.events.includes(eventType)
                return (
                  <button
                    key={eventType}
                    type="button"
                    onClick={() => toggleWebhookEvent(eventType)}
                    className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${active ? 'border-blue-300 bg-blue-100 text-blue-700' : 'border-slate-200 bg-white text-slate-500 hover:bg-blue-50'}`}
                  >
                    {eventType}
                  </button>
                )
              })}
            </div>
          </div>
          <button
            type="submit"
            disabled={webhookBusy || !webhookForm.destination_url.trim() || webhookForm.events.length === 0}
            className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
          >
            Create destination
          </button>
        </form>

        <div className="mt-5 space-y-3">
          {webhookDestinations.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">
              No webhook destinations yet.
            </div>
          ) : (
            webhookDestinations.map((notification) => (
              <div key={notification.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-slate-950">{notification.channel === 'slack' ? 'Slack destination' : 'Webhook destination'}</h3>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${notification.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
                        {notification.is_active ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">{notification.destination_url}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {notification.events.map((eventType) => (
                        <span key={eventType} className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700">{eventType}</span>
                      ))}
                    </div>
                    {webhookTestResults[notification.id] && (
                      <p className={`mt-2 text-xs ${webhookTestResults[notification.id].ok ? 'text-emerald-700' : 'text-rose-700'}`}>
                        {webhookTestResults[notification.id].ok ? 'Last test succeeded.' : `Last test failed: ${webhookTestResults[notification.id].error}`}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button type="button" disabled={webhookBusy} onClick={() => void handleTestWebhook(notification)} className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-100 disabled:opacity-50">
                      Test
                    </button>
                    <button type="button" disabled={webhookBusy} onClick={() => handleStartEditWebhook(notification)} className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">
                      Edit
                    </button>
                    <button type="button" disabled={webhookBusy} onClick={() => void handleToggleWebhook(notification)} className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">
                      {notification.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button type="button" disabled={webhookBusy} onClick={() => void handleDeleteWebhook(notification)} className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100 disabled:opacity-50">
                      Delete
                    </button>
                  </div>
                </div>

                {editingWebhookId === notification.id && webhookEditForm && (
                  <div className="mt-4 rounded-2xl border border-blue-200 bg-blue-50/60 p-4">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <div>
                        <h4 className="text-sm font-semibold text-slate-950">Edit {notification.channel === 'slack' ? 'Slack' : 'Webhook'} destination</h4>
                        <p className="mt-1 text-xs text-slate-500">Update the outbound destination URL and subscribed events without recreating the record.</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setEditingWebhookId(null)
                          setWebhookEditForm(null)
                        }}
                        className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        Cancel
                      </button>
                    </div>
                    <div className="grid gap-3 md:grid-cols-3">
                      <label className="text-xs font-semibold text-slate-600">
                        Channel
                        <input className={`mt-1 w-full ${inputCls}`} value={webhookEditForm.channel} disabled />
                      </label>
                      <label className="text-xs font-semibold text-slate-600 md:col-span-2">
                        Destination URL
                        <input className={`mt-1 w-full ${inputCls}`} value={webhookEditForm.destination_url} onChange={(e) => setWebhookEditForm((prev) => prev ? { ...prev, destination_url: e.target.value } : prev)} />
                      </label>
                    </div>
                    <div className="mt-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Events</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {webhookEvents.map((eventType) => {
                          const active = webhookEditForm.events.includes(eventType)
                          return (
                            <button
                              key={eventType}
                              type="button"
                              onClick={() => toggleWebhookEditEvent(eventType)}
                              className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${active ? 'border-blue-300 bg-blue-100 text-blue-700' : 'border-slate-200 bg-white text-slate-500 hover:bg-blue-50'}`}
                            >
                              {eventType}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={webhookBusy || !webhookEditForm.destination_url.trim() || webhookEditForm.events.length === 0}
                        onClick={() => void handleSaveWebhookEdit(notification.id)}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
                      >
                        Save changes
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setEditingWebhookId(null)
                          setWebhookEditForm(null)
                        }}
                        className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                <div className="mt-4 overflow-hidden rounded-xl border border-slate-200">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-slate-50 text-left text-slate-500">
                        <th className="px-3 py-2 font-semibold">Event</th>
                        <th className="px-3 py-2 font-semibold">Status</th>
                        <th className="px-3 py-2 font-semibold">HTTP</th>
                        <th className="px-3 py-2 font-semibold">When</th>
                        <th className="px-3 py-2 font-semibold">Error</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {(webhookDeliveries[notification.id] ?? []).length === 0 ? (
                        <tr><td colSpan={5} className="px-3 py-4 text-center text-slate-500">No deliveries yet.</td></tr>
                      ) : (
                        (webhookDeliveries[notification.id] ?? []).map((delivery) => (
                          <tr key={delivery.id}>
                            <td className="px-3 py-2 text-slate-700">{delivery.event_type}</td>
                            <td className="px-3 py-2 text-slate-600">{delivery.status}</td>
                            <td className="px-3 py-2 text-slate-600">{delivery.response_status ?? '-'}</td>
                            <td className="px-3 py-2 text-slate-600">{formatTimestamp(delivery.delivered_at ?? delivery.created_at)}</td>
                            <td className="max-w-sm truncate px-3 py-2 text-slate-500">{delivery.error_detail ?? '-'}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
