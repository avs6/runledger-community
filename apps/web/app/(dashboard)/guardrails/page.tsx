'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  Activity,
  BellRing,
  CheckCircle2,
  CheckSquare,
  Edit2,
  Play,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  TestTube2,
  Trash2,
  TriangleAlert,
  Wand2,
  X,
  Square,
} from 'lucide-react'
import {
  acknowledgeGuardrailAlert,
  activateContentFilters,
  createGuardrailRule,
  createGuardrailTestCase,
  createPartnerGuardrail,
  deleteGuardrailRule,
  deleteGuardrailTestCase,
  deletePartnerGuardrail,
  evaluateGuardrailAlerts,
  getGuardrailStats,
  healthCheckPartner,
  listContentFilters,
  listGuardrailAlerts,
  listGuardrailEvents,
  listGuardrailRules,
  listGuardrailTemplates,
  listGuardrailTestCases,
  listPartnerGuardrails,
  runGuardrailRegression,
  submitGuardrailFeedback,
  testAllGuardrails,
  testGuardrailRule,
  updateGuardrailRule,
  updatePartnerGuardrail,
  getGuardrailsObservePosture,
} from '@/lib/api'
import type {
  ContentFilterStatus,
  GuardrailAlertResponse,
  GuardrailEventList,
  GuardrailRegressionReport,
  GuardrailRuleResponse,
  GuardrailStats,
  GuardrailTemplate,
  GuardrailTestCaseResponse,
  GuardrailTestResponse,
  PartnerGuardrailResponse,
  GuardrailsObservePosture,
} from '@/types/api'

function pct(value: number | null | undefined) {
  if (value == null) return '--'
  return `${(value * 100).toFixed(1)}%`
}

function fmtCurrency(value: number | null | undefined) {
  if (value == null) return '$0.00'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value)
}

const severityColors: Record<string, string> = {
  off: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700',
  low: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900',
  medium: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 border-blue-200 dark:border-blue-900',
  high: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 border-amber-200 dark:border-amber-900',
  strict: 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300 border-rose-200 dark:border-rose-900',
  critical: 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300 border-rose-200 dark:border-rose-900',
}

const decisionColors: Record<string, string> = {
  allow: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300',
  block: 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300',
  modify: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
}

const inputCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'

type FilterDraft = ContentFilterStatus

type PartnerFormState = {
  id?: string
  provider: string
  name: string
  mode: string
  endpoint_url: string
  timeout_ms: number
  fallback_action: string
  priority: number
  status: string
  config_text: string
  credentials_text: string
}

function emptyPartnerForm(): PartnerFormState {
  return {
    provider: 'presidio',
    name: '',
    mode: 'pre_call',
    endpoint_url: '',
    timeout_ms: 2000,
    fallback_action: 'allow',
    priority: 200,
    status: 'active',
    config_text: '{}',
    credentials_text: '{}',
  }
}

export default function GuardrailsPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey

  const [rules, setRules] = useState<GuardrailRuleResponse[]>([])
  const [stats, setStats] = useState<GuardrailStats | null>(null)
  const [events, setEvents] = useState<GuardrailEventList | null>(null)
  const [templates, setTemplates] = useState<GuardrailTemplate[]>([])
  const [partners, setPartners] = useState<PartnerGuardrailResponse[]>([])
  const [filters, setFilters] = useState<FilterDraft[]>([])
  const [testCases, setTestCases] = useState<GuardrailTestCaseResponse[]>([])
  const [alerts, setAlerts] = useState<GuardrailAlertResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshingAlerts, setRefreshingAlerts] = useState(false)
  const [observePosture, setObservePosture] = useState<GuardrailsObservePosture | null>(null)
  const [savingFilters, setSavingFilters] = useState(false)

  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedRuleIds, setSelectedRuleIds] = useState<string[]>([])
  const [bulkUpdatingRules, setBulkUpdatingRules] = useState(false)

  const [showRuleModal, setShowRuleModal] = useState(false)
  const [editingRule, setEditingRule] = useState<GuardrailRuleResponse | null>(null)
  const [ruleName, setRuleName] = useState('')
  const [ruleDescription, setRuleDescription] = useState('')
  const [ruleMode, setRuleMode] = useState('pre_call')
  const [ruleType, setRuleType] = useState('custom')
  const [ruleSeverity, setRuleSeverity] = useState('medium')
  const [ruleLogic, setRuleLogic] = useState('')
  const [ruleConfigText, setRuleConfigText] = useState('{}')
  const [ruleSkipSystemMessages, setRuleSkipSystemMessages] = useState(false)
  const [savingRule, setSavingRule] = useState(false)

  const [showPartnerModal, setShowPartnerModal] = useState(false)
  const [partnerForm, setPartnerForm] = useState<PartnerFormState>(emptyPartnerForm())
  const [savingPartner, setSavingPartner] = useState(false)

  const [playgroundRuleId, setPlaygroundRuleId] = useState<'all' | string>('all')
  const [playgroundText, setPlaygroundText] = useState('')
  const [playgroundModel, setPlaygroundModel] = useState('gpt-4.1-mini')
  const [playgroundResponse, setPlaygroundResponse] = useState<GuardrailTestResponse | null>(null)
  const [runningPlayground, setRunningPlayground] = useState(false)

  const [testCaseRuleId, setTestCaseRuleId] = useState('')
  const [testCaseName, setTestCaseName] = useState('')
  const [testCaseInput, setTestCaseInput] = useState('')
  const [testCaseExpectedDecision, setTestCaseExpectedDecision] = useState('block')
  const [savingTestCase, setSavingTestCase] = useState(false)

  const [selectedRegressionRuleId, setSelectedRegressionRuleId] = useState('')
  const [runningRegression, setRunningRegression] = useState(false)
  const [regressionReport, setRegressionReport] = useState<GuardrailRegressionReport | null>(null)

  const activeRules = useMemo(
    () => rules.filter((rule) => rule.status === 'active'),
    [rules]
  )

  const filteredRules = useMemo(() => {
    return rules.filter((rule) => {
      const matchesSearch =
        rule.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (rule.description || '').toLowerCase().includes(searchQuery.toLowerCase())
      const matchesStatus = statusFilter === 'all' || rule.status === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [rules, searchQuery, statusFilter])

  const testCaseCounts = useMemo(() => {
    const counts = new Map<string, number>()
    for (const item of testCases) {
      counts.set(item.guardrail_rule_id, (counts.get(item.guardrail_rule_id) || 0) + 1)
    }
    return counts
  }, [testCases])

  const selectedRules = useMemo(
    () => rules.filter((rule) => selectedRuleIds.includes(rule.id)),
    [rules, selectedRuleIds]
  )

  async function loadData() {
    if (!apiKey) return
    setLoading(true)
    try {
      const [
        rulesRes,
        statsRes,
        eventsRes,
        templatesRes,
        partnersRes,
        filtersRes,
        testCasesRes,
        alertsRes,
      ] = await Promise.all([
        listGuardrailRules(apiKey, { limit: 100 }),
        getGuardrailStats(apiKey, 24).catch(() => null),
        listGuardrailEvents(apiKey, { limit: 12 }).catch(() => null),
        listGuardrailTemplates(apiKey).catch(() => []),
        listPartnerGuardrails(apiKey).catch(() => null),
        listContentFilters(apiKey).catch(() => null),
        listGuardrailTestCases(apiKey).catch(() => null),
        listGuardrailAlerts(apiKey, { limit: 12 }).catch(() => null),
      ])

      setRules(rulesRes.items)
      setStats(statsRes)
      setEvents(eventsRes)
      setTemplates(templatesRes)
      setPartners(partnersRes?.items || [])
      setFilters(filtersRes?.filters || [])
      setTestCases(testCasesRes?.items || [])
      setAlerts(alertsRes?.items || [])

      if (!testCaseRuleId && rulesRes.items.length > 0) {
        setTestCaseRuleId(rulesRes.items[0].id)
      }
      if (!selectedRegressionRuleId && rulesRes.items.length > 0) {
        setSelectedRegressionRuleId(rulesRes.items[0].id)
      }
      setSelectedRuleIds((current) =>
        current.filter((id) => rulesRes.items.some((rule) => rule.id === id))
      )
    } catch (err) {
      console.error(err)
      toast.error('Failed to load guardrails')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    if (apiKey) {
      getGuardrailsObservePosture(apiKey).then(setObservePosture).catch(() => {})
    }
  }, [apiKey])

  function resetRuleForm() {
    setRuleName('')
    setRuleDescription('')
    setRuleMode('pre_call')
    setRuleType('custom')
    setRuleSeverity('medium')
    setRuleLogic('')
    setRuleConfigText('{}')
    setRuleSkipSystemMessages(false)
    setEditingRule(null)
  }

  function openRuleEdit(rule: GuardrailRuleResponse) {
    setEditingRule(rule)
    setRuleName(rule.name)
    setRuleDescription(rule.description || '')
    setRuleMode(rule.mode || 'pre_call')
    setRuleType(rule.rule_type || 'custom')
    setRuleSeverity(rule.severity || 'medium')
    setRuleLogic(rule.logic || '')
    setRuleConfigText(JSON.stringify(rule.config || {}, null, 2))
    setRuleSkipSystemMessages(rule.skip_system_messages || false)
    setShowRuleModal(true)
  }

  function applyTemplate(template: GuardrailTemplate) {
    resetRuleForm()
    setRuleName(template.name)
    setRuleDescription(template.description || '')
    setRuleMode(template.mode || 'pre_call')
    setRuleType('template')
    setRuleSeverity('medium')
    setRuleLogic(template.default_logic || '')
    setRuleConfigText(JSON.stringify(template.default_config || {}, null, 2))
    setShowRuleModal(true)
  }

  function openPartnerEdit(partner: PartnerGuardrailResponse) {
    setPartnerForm({
      id: partner.id,
      provider: partner.provider,
      name: partner.name,
      mode: partner.mode,
      endpoint_url: partner.endpoint_url || '',
      timeout_ms: partner.timeout_ms,
      fallback_action: partner.fallback_action,
      priority: partner.priority,
      status: partner.status,
      config_text: JSON.stringify(partner.config || {}, null, 2),
      credentials_text: '{}',
    })
    setShowPartnerModal(true)
  }

  function resetPartnerForm() {
    setPartnerForm(emptyPartnerForm())
  }

  async function handleSaveRule(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !ruleName.trim()) return
    setSavingRule(true)
    try {
      const parsedConfig = ruleConfigText.trim() ? JSON.parse(ruleConfigText) : {}
      if (editingRule) {
        await updateGuardrailRule(apiKey, editingRule.id, {
          name: ruleName.trim(),
          description: ruleDescription.trim() || undefined,
          mode: ruleMode,
          severity: ruleSeverity,
          logic: ruleLogic.trim() || undefined,
          config: parsedConfig,
          skip_system_messages: ruleSkipSystemMessages,
        })
        toast.success('Guardrail rule updated')
      } else {
        await createGuardrailRule(apiKey, {
          name: ruleName.trim(),
          description: ruleDescription.trim() || undefined,
          mode: ruleMode,
          rule_type: ruleType,
          severity: ruleSeverity,
          logic: ruleLogic.trim() || undefined,
          config: parsedConfig,
          status: 'active',
          skip_system_messages: ruleSkipSystemMessages,
        })
        toast.success('Guardrail rule created')
      }
      setShowRuleModal(false)
      resetRuleForm()
      await loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to save guardrail rule')
    } finally {
      setSavingRule(false)
    }
  }

  async function handleDeleteRule(rule: GuardrailRuleResponse) {
    if (!apiKey || !confirm(`Delete guardrail rule "${rule.name}"?`)) return
    try {
      await deleteGuardrailRule(apiKey, rule.id)
      toast.success('Guardrail rule deleted')
      await loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to delete guardrail rule')
    }
  }

  async function handleToggleRuleStatus(rule: GuardrailRuleResponse) {
    if (!apiKey) return
    try {
      await updateGuardrailRule(apiKey, rule.id, {
        status: rule.status === 'active' ? 'disabled' : 'active',
      })
      toast.success(
        rule.status === 'active' ? 'Guardrail paused' : 'Guardrail activated'
      )
      await loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to update guardrail')
    }
  }

  async function handleBulkRuleStatus(nextStatus: 'active' | 'disabled') {
    if (!apiKey || selectedRuleIds.length === 0) return
    setBulkUpdatingRules(true)
    try {
      await Promise.all(
        selectedRuleIds.map((id) =>
          updateGuardrailRule(apiKey, id, {
            status: nextStatus,
          })
        )
      )
      toast.success(
        nextStatus === 'active'
          ? `Activated ${selectedRuleIds.length} guardrail${selectedRuleIds.length === 1 ? '' : 's'}`
          : `Paused ${selectedRuleIds.length} guardrail${selectedRuleIds.length === 1 ? '' : 's'}`
      )
      setSelectedRuleIds([])
      await loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to update selected guardrails')
    } finally {
      setBulkUpdatingRules(false)
    }
  }

  function toggleRuleSelection(ruleId: string) {
    setSelectedRuleIds((current) =>
      current.includes(ruleId)
        ? current.filter((id) => id !== ruleId)
        : [...current, ruleId]
    )
  }

  function toggleAllVisibleRules() {
    const visibleIds = filteredRules.map((rule) => rule.id)
    const allVisibleSelected =
      visibleIds.length > 0 && visibleIds.every((id) => selectedRuleIds.includes(id))
    if (allVisibleSelected) {
      setSelectedRuleIds((current) => current.filter((id) => !visibleIds.includes(id)))
      return
    }
    setSelectedRuleIds((current) => Array.from(new Set([...current, ...visibleIds])))
  }

  async function handleSaveFilters() {
    if (!apiKey) return
    setSavingFilters(true)
    try {
      await activateContentFilters(apiKey, {
        filters: filters.map((filter) => ({
          filter_name: filter.filter_name,
          severity: filter.severity,
          enabled: filter.enabled,
        })),
      })
      toast.success('Content filters updated')
      await loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to save content filters')
    } finally {
      setSavingFilters(false)
    }
  }

  async function handleRunPlayground() {
    if (!apiKey || !playgroundText.trim()) return
    setRunningPlayground(true)
    setPlaygroundResponse(null)
    try {
      const payload = {
        texts: [playgroundText.trim()],
        model: playgroundModel.trim() || undefined,
      }
      const result =
        playgroundRuleId === 'all'
          ? await testAllGuardrails(apiKey, payload)
          : await testGuardrailRule(apiKey, playgroundRuleId, payload)
      setPlaygroundResponse(result)
      toast.success('Guardrail test complete')
    } catch (err) {
      console.error(err)
      toast.error('Failed to run guardrail test')
    } finally {
      setRunningPlayground(false)
    }
  }

  async function handleCreateTestCase(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !testCaseRuleId || !testCaseName.trim() || !testCaseInput.trim()) return
    setSavingTestCase(true)
    try {
      await createGuardrailTestCase(apiKey, {
        guardrail_rule_id: testCaseRuleId,
        name: testCaseName.trim(),
        input_text: testCaseInput.trim(),
        expected_decision: testCaseExpectedDecision,
      })
      toast.success('Test case created')
      setTestCaseName('')
      setTestCaseInput('')
      await loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to create test case')
    } finally {
      setSavingTestCase(false)
    }
  }

  async function handleDeleteTestCase(testCase: GuardrailTestCaseResponse) {
    if (!apiKey || !confirm(`Delete test case "${testCase.name}"?`)) return
    try {
      await deleteGuardrailTestCase(apiKey, testCase.id)
      toast.success('Test case deleted')
      await loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to delete test case')
    }
  }

  async function handleRunRegression(ruleId?: string) {
    const targetRuleId = ruleId || selectedRegressionRuleId
    if (!apiKey || !targetRuleId) return
    setRunningRegression(true)
    setRegressionReport(null)
    try {
      const report = await runGuardrailRegression(apiKey, targetRuleId)
      setRegressionReport(report)
      toast.success(`Regression finished: ${report.passed}/${report.total_cases} passed`)
    } catch (err) {
      console.error(err)
      toast.error('Failed to run regression')
    } finally {
      setRunningRegression(false)
    }
  }

  async function handleSavePartner(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !partnerForm.name.trim()) return
    setSavingPartner(true)
    try {
      const config = partnerForm.config_text.trim()
        ? JSON.parse(partnerForm.config_text)
        : {}
      const credentials = partnerForm.credentials_text.trim()
        ? JSON.parse(partnerForm.credentials_text)
        : {}
      const payload = {
        provider: partnerForm.provider,
        name: partnerForm.name.trim(),
        mode: partnerForm.mode,
        endpoint_url: partnerForm.endpoint_url.trim() || undefined,
        timeout_ms: partnerForm.timeout_ms,
        fallback_action: partnerForm.fallback_action,
        priority: partnerForm.priority,
        status: partnerForm.status,
        config,
        credentials,
      }

      if (partnerForm.id) {
        await updatePartnerGuardrail(apiKey, partnerForm.id, payload)
        toast.success('Partner guardrail updated')
      } else {
        await createPartnerGuardrail(apiKey, payload)
        toast.success('Partner guardrail created')
      }
      setShowPartnerModal(false)
      resetPartnerForm()
      await loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to save partner guardrail')
    } finally {
      setSavingPartner(false)
    }
  }

  async function handleDeletePartner(partner: PartnerGuardrailResponse) {
    if (!apiKey || !confirm(`Delete partner guardrail "${partner.name}"?`)) return
    try {
      await deletePartnerGuardrail(apiKey, partner.id)
      toast.success('Partner guardrail deleted')
      await loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to delete partner guardrail')
    }
  }

  async function handleHealthCheckPartner(partner: PartnerGuardrailResponse) {
    if (!apiKey) return
    try {
      await healthCheckPartner(apiKey, partner.id)
      toast.success(`Health check ran for ${partner.name}`)
      await loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to run partner health check')
    }
  }

  async function handleTogglePartnerStatus(partner: PartnerGuardrailResponse) {
    if (!apiKey) return
    try {
      await updatePartnerGuardrail(apiKey, partner.id, {
        status: partner.status === 'active' ? 'disabled' : 'active',
      })
      toast.success(partner.status === 'active' ? 'Partner paused' : 'Partner activated')
      await loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to update partner')
    }
  }

  async function handleMarkFalsePositive(eventId: string) {
    if (!apiKey) return
    const reason = prompt('Why is this a false positive? (optional)') || ''
    try {
      await submitGuardrailFeedback(apiKey, eventId, {
        is_false_positive: true,
        reason: reason.trim() || undefined,
      })
      toast.success('Event marked as false positive')
      await loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to save feedback')
    }
  }

  async function handleEvaluateAlerts() {
    if (!apiKey) return
    setRefreshingAlerts(true)
    try {
      const created = await evaluateGuardrailAlerts(apiKey, 1, 24)
      await loadData()
      toast.success(
        created.length > 0
          ? `Generated ${created.length} alert${created.length === 1 ? '' : 's'}`
          : 'No new alerts generated'
      )
    } catch (err) {
      console.error(err)
      toast.error('Failed to evaluate alerts')
    } finally {
      setRefreshingAlerts(false)
    }
  }

  async function handleAcknowledgeAlert(alertId: string) {
    if (!apiKey) return
    try {
      await acknowledgeGuardrailAlert(apiKey, alertId)
      toast.success('Alert acknowledged')
      await loadData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to acknowledge alert')
    }
  }

  if (!apiKey) {
    return <div className="p-8 text-slate-500">Sign in to view guardrails.</div>
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6 md:p-10">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">
            Guardrails and Safety Engine
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Manage content filters, custom rules, partner checks, test coverage,
            live enforcement telemetry, and alerts from one operator surface.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link href="/users" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Users</Link>
          <Link href="/workspace" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Workspaces</Link>
          <Link href="/gateway" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Gateway</Link>
          <Link href="/monitoring" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Telemetry</Link>
        </div>

        {observePosture && (
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Guardrails Observe Posture</h2>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Observability context for guardrail enforcement — evaluations, outcomes, latency, and feedback over the last {observePosture.period_days} days.
            </p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-xs text-slate-500 dark:text-slate-400">Total Evaluations</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.evaluations.total.toLocaleString()}</p>
                <p className="text-xs text-slate-400">{observePosture.evaluations.distinct_rules_fired} rules fired</p>
              </div>
              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-xs text-slate-500 dark:text-slate-400">Blocks</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.evaluations.blocks.toLocaleString()}</p>
                <p className="text-xs text-slate-400">{(observePosture.evaluations.block_rate * 100).toFixed(1)}% block rate</p>
              </div>
              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-xs text-slate-500 dark:text-slate-400">Modifications</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.evaluations.modifications.toLocaleString()}</p>
                <p className="text-xs text-slate-400">{(observePosture.evaluations.modification_rate * 100).toFixed(1)}% modification rate</p>
              </div>
              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-xs text-slate-500 dark:text-slate-400">Avg Latency</p>
                <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.performance.avg_latency_ms !== null ? `${observePosture.performance.avg_latency_ms.toFixed(0)}ms` : '—'}</p>
                <p className="text-xs text-slate-400">max {observePosture.performance.max_latency_ms !== null ? `${observePosture.performance.max_latency_ms.toFixed(0)}ms` : '—'}</p>
              </div>
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-xs text-slate-500 dark:text-slate-400">Rule Coverage</p>
                <p className="mt-1 text-sm text-slate-900 dark:text-white"><strong>{observePosture.rules.active_rules}</strong> active of <strong>{observePosture.rules.total_rules}</strong> total</p>
              </div>
              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-xs text-slate-500 dark:text-slate-400">Mode Breakdown</p>
                <p className="mt-1 text-sm text-slate-900 dark:text-white"><strong>{observePosture.mode_breakdown.pre_call.toLocaleString()}</strong> pre-call · <strong>{observePosture.mode_breakdown.post_call.toLocaleString()}</strong> post-call</p>
              </div>
              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <p className="text-xs text-slate-500 dark:text-slate-400">Feedback</p>
                <p className="mt-1 text-sm text-slate-900 dark:text-white"><strong>{observePosture.feedback.false_positive_count}</strong> false positives flagged</p>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-3">
              <Link href="/monitoring/runs" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Runs</Link>
              <Link href="/monitoring/sessions" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Request Flow</Link>
              <Link href="/monitoring/requests" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Request Explorer</Link>
              <Link href="/analytics/outcomes" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Outcomes & ROI</Link>
              <Link href="/analytics/engineering" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Engineering</Link>
              <Link href="/monitoring" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Monitoring</Link>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => {
              resetRuleForm()
              setShowRuleModal(true)
            }}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Add rule
          </button>
          <button
            onClick={() => {
              resetPartnerForm()
              setShowPartnerModal(true)
            }}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <ShieldCheck className="h-4 w-4" />
            Add partner
          </button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Evaluations" value={String(stats?.total_evaluations ?? '--')} />
        <MetricCard label="Block Rate" value={pct(stats?.block_rate)} />
        <MetricCard
          label="Average Latency"
          value={stats?.avg_latency_ms != null ? `${stats.avg_latency_ms.toFixed(1)} ms` : '--'}
        />
        <MetricCard label="False Positives" value={pct(stats?.false_positive_rate)} />
        <MetricCard label="Partner Checks" value={String(partners.length)} />
      </div>

      <section className="rounded-3xl border border-slate-200 bg-gradient-to-br from-cyan-50 via-white to-blue-50 p-6 shadow-sm dark:border-slate-800 dark:from-slate-900 dark:via-slate-950 dark:to-slate-900">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-200 bg-white/80 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-cyan-700 dark:border-cyan-900 dark:bg-slate-900/80 dark:text-cyan-300">
              <Sparkles className="h-3.5 w-3.5" />
              Guardrail templates
            </div>
            <h2 className="mt-3 text-xl font-semibold text-slate-900 dark:text-white">
              Start from proven safety patterns
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Templates seed real rules that you can customize, test, and enforce
              immediately. They are a starting point, not a separate product path.
            </p>
          </div>
          <div className="text-sm text-slate-500">
            {templates.length} preset{templates.length === 1 ? '' : 's'}
          </div>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {templates.map((template) => (
            <article
              key={template.template_id}
              className="group flex h-full flex-col justify-between overflow-hidden rounded-2xl border border-white/70 bg-white/90 p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-slate-900/85"
            >
              <div>
                <div className="flex items-center justify-between gap-3">
                  <span className="rounded-full bg-cyan-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300">
                    {template.category.replaceAll('_', ' ')}
                  </span>
                  <span className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                    {template.mode}
                  </span>
                </div>
                <h3 className="mt-4 text-base font-semibold text-slate-900 dark:text-white">
                  {template.name}
                </h3>
                <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
                  {template.description}
                </p>
                <div className="mt-4 rounded-2xl bg-slate-950 p-3 text-[11px] leading-5 text-cyan-100 dark:bg-slate-950">
                  <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-cyan-300">
                    Default logic
                  </div>
                  <pre className="overflow-hidden whitespace-pre-wrap break-words">
                    {template.default_logic || 'No logic preview available.'}
                  </pre>
                </div>
              </div>
              <button
                onClick={() => applyTemplate(template)}
                className="mt-5 inline-flex items-center justify-center gap-2 rounded-xl border border-cyan-200 bg-cyan-50 px-3 py-2 text-sm font-semibold text-cyan-700 transition hover:bg-cyan-100 dark:border-cyan-900 dark:bg-cyan-950 dark:text-cyan-300 dark:hover:bg-cyan-900/60"
              >
                <Wand2 className="h-4 w-4" />
                Create from template
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/85">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Built-in content filters
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Toggle the baseline filters that run alongside your custom rules.
              </p>
            </div>
            <button
              onClick={handleSaveFilters}
              disabled={savingFilters}
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
            >
              {savingFilters ? 'Saving...' : 'Save filters'}
            </button>
          </div>

          <div className="mt-5 grid gap-3">
            {filters.map((filter, index) => (
              <div
                key={filter.filter_name}
                className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-950/60 lg:grid-cols-[1.2fr,0.7fr,0.5fr]"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                      {filter.filter_name.replaceAll('_', ' ')}
                    </h3>
                    <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                      {filter.category}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-500">{filter.description}</p>
                </div>
                <label className="flex flex-col gap-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                  Severity
                  <select
                    value={filter.severity}
                    onChange={(e) =>
                      setFilters((current) =>
                        current.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, severity: e.target.value } : item
                        )
                      )
                    }
                    className={inputCls}
                  >
                    <option value="off">Off</option>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="strict">Strict</option>
                  </select>
                </label>
                <div className="flex items-center gap-3 lg:justify-end">
                  <button
                    onClick={() =>
                      setFilters((current) =>
                        current.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, enabled: !item.enabled } : item
                        )
                      )
                    }
                    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
                      filter.enabled ? 'bg-emerald-600' : 'bg-slate-300 dark:bg-slate-700'
                    }`}
                    aria-label={`Toggle ${filter.filter_name}`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition ${
                        filter.enabled ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                  <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                    {filter.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/85">
          <div className="flex items-center gap-3">
            <TestTube2 className="h-5 w-5 text-blue-600 dark:text-blue-300" />
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Test playground
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Run one rule or the full active set before you ship changes to live
                traffic.
              </p>
            </div>
          </div>

          <div className="mt-5 space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Rule scope
                <select
                  value={playgroundRuleId}
                  onChange={(e) => setPlaygroundRuleId(e.target.value)}
                  className={`${inputCls} mt-1`}
                >
                  <option value="all">All active guardrails</option>
                  {activeRules.map((rule) => (
                    <option key={rule.id} value={rule.id}>
                      {rule.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Model hint
                <input
                  value={playgroundModel}
                  onChange={(e) => setPlaygroundModel(e.target.value)}
                  className={`${inputCls} mt-1`}
                  placeholder="gpt-4.1-mini"
                />
              </label>
            </div>

            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              Sample text
              <textarea
                value={playgroundText}
                onChange={(e) => setPlaygroundText(e.target.value)}
                placeholder="Paste a prompt or response sample to evaluate."
                className={`${inputCls} mt-1 min-h-32`}
              />
            </label>

            <div className="flex flex-wrap gap-3">
              <button
                onClick={handleRunPlayground}
                disabled={runningPlayground || !playgroundText.trim()}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
              >
                <Play className="h-4 w-4" />
                {runningPlayground ? 'Running...' : 'Run test'}
              </button>
              <button
                onClick={() => {
                  if (!playgroundText.trim()) return
                  setTestCaseInput(playgroundText)
                  if (playgroundRuleId !== 'all') setTestCaseRuleId(playgroundRuleId)
                  toast.success('Copied sample into the test case form')
                }}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                <Plus className="h-4 w-4" />
                Save as test case
              </button>
            </div>

            {playgroundResponse && (
              <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-800 dark:bg-slate-950/60">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-sm font-semibold text-slate-900 dark:text-white">
                    Overall decision
                  </span>
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold uppercase ${
                      decisionColors[playgroundResponse.overall_decision] || decisionColors.allow
                    }`}
                  >
                    {playgroundResponse.overall_decision}
                  </span>
                  <span className="text-xs text-slate-500">
                    {playgroundResponse.total_latency_ms.toFixed(1)} ms total
                  </span>
                </div>
                <div className="mt-4 space-y-3">
                  {playgroundResponse.results.map((result) => (
                    <div
                      key={result.guardrail_id}
                      className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="font-medium text-slate-900 dark:text-white">
                          {result.guardrail_name}
                        </div>
                        <span
                          className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${
                            decisionColors[result.decision] || decisionColors.allow
                          }`}
                        >
                          {result.decision}
                        </span>
                      </div>
                      <div className="mt-2 text-sm text-slate-500">
                        {result.reason || 'No reason returned'}
                      </div>
                      {result.modified_texts && result.modified_texts.length > 0 && (
                        <div className="mt-3 rounded-xl bg-amber-50 p-3 text-xs text-amber-800 dark:bg-amber-950/50 dark:text-amber-200">
                          <div className="mb-1 font-semibold">Modified text</div>
                          <pre className="whitespace-pre-wrap break-words">
                            {result.modified_texts.join('\n\n')}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/85">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Guardrail rules
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Live rules that participate in request enforcement on gateway traffic.
            </p>
            <p className="mt-2 text-xs text-slate-500">
              Enforcement model: active rules are enforced at runtime, disabled rules are skipped,
              API keys can scope to selected rule IDs, and every violation is written into the
              guardrail event log below.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex items-center gap-2">
              {['all', 'active', 'disabled', 'draft'].map((status) => (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold capitalize transition ${
                    statusFilter === status
                      ? 'bg-blue-600 text-white'
                      : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300'
                  }`}
                >
                  {status} (
                  {status === 'all'
                    ? rules.length
                    : rules.filter((rule) => rule.status === status).length}
                  )
                </button>
              ))}
            </div>

            <div className="relative w-full sm:w-72">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search rules..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={`${inputCls} pl-9`}
              />
            </div>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-800 dark:bg-slate-950/60 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600 dark:text-slate-300">
            <button
              onClick={toggleAllVisibleRules}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              {filteredRules.length > 0 &&
              filteredRules.every((rule) => selectedRuleIds.includes(rule.id)) ? (
                <CheckSquare className="h-4 w-4" />
              ) : (
                <Square className="h-4 w-4" />
              )}
              Select visible
            </button>
            <span>
              {selectedRules.length} selected
            </span>
            <span>
              {activeRules.length} active and enforceable
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => void handleBulkRuleStatus('active')}
              disabled={bulkUpdatingRules || selectedRuleIds.length === 0}
              className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-100 disabled:opacity-50 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300"
            >
              Enable selected
            </button>
            <button
              onClick={() => void handleBulkRuleStatus('disabled')}
              disabled={bulkUpdatingRules || selectedRuleIds.length === 0}
              className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700 transition hover:bg-amber-100 disabled:opacity-50 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300"
            >
              Disable selected
            </button>
          </div>
        </div>

        {loading ? (
          <div className="mt-5 rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
            Loading guardrails...
          </div>
        ) : filteredRules.length === 0 ? (
          <div className="mt-5 rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
            No guardrail rules found.
          </div>
        ) : (
          <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {filteredRules.map((rule) => {
              const isEnforced = rule.status === 'active'
              return (
                <div
                  key={rule.id}
                  className={`flex flex-col justify-between rounded-2xl border p-5 shadow-sm transition hover:shadow-md ${
                    isEnforced
                      ? 'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900'
                      : 'border-slate-200/60 bg-slate-50/60 opacity-80 dark:border-slate-800/60 dark:bg-slate-950/30'
                  }`}
                >
                  <div>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <button
                          onClick={() => toggleRuleSelection(rule.id)}
                          className="mt-1 rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                          title={
                            selectedRuleIds.includes(rule.id) ? 'Deselect rule' : 'Select rule'
                          }
                        >
                          {selectedRuleIds.includes(rule.id) ? (
                            <CheckSquare className="h-4 w-4" />
                          ) : (
                            <Square className="h-4 w-4" />
                          )}
                        </button>
                        <span
                          className={`rounded-xl p-2 ${
                            isEnforced
                              ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400'
                              : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500'
                          }`}
                        >
                          <ShieldCheck className="h-4 w-4" />
                        </span>
                        <div>
                          <h3 className="font-semibold text-slate-900 dark:text-white">
                            {rule.name}
                          </h3>
                          <p className="mt-1 text-sm text-slate-500">
                            {rule.description || 'No description provided.'}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleToggleRuleStatus(rule)}
                        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
                          isEnforced ? 'bg-emerald-600' : 'bg-slate-300 dark:bg-slate-700'
                        }`}
                        title={isEnforced ? 'Disable rule' : 'Enable rule'}
                      >
                        <span
                          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition ${
                            isEnforced ? 'translate-x-5' : 'translate-x-0'
                          }`}
                        />
                      </button>
                    </div>

                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                        {rule.mode}
                      </span>
                      <span
                        className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${
                          severityColors[rule.severity] || severityColors.low
                        }`}
                      >
                        {rule.severity}
                      </span>
                      <span className="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                        {rule.rule_type}
                      </span>
                      {rule.skip_system_messages && (
                        <span className="rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                          Skip system messages
                        </span>
                      )}
                    </div>

                    <div className="mt-4 grid gap-3 rounded-2xl bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-950/60 dark:text-slate-300">
                      <div className="flex items-center justify-between">
                        <span>Regression cases</span>
                        <span className="font-semibold">{testCaseCounts.get(rule.id) || 0}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Status</span>
                        <span className="font-semibold capitalize">{rule.status}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 flex flex-wrap gap-2">
                    <button
                      onClick={() => openRuleEdit(rule)}
                      className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                    >
                      <Edit2 className="h-4 w-4" />
                      Edit
                    </button>
                    <button
                      onClick={() => {
                        setSelectedRegressionRuleId(rule.id)
                        void handleRunRegression(rule.id)
                      }}
                      className="inline-flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700 transition hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300"
                    >
                      <Play className="h-4 w-4" />
                      Run regression
                    </button>
                    <button
                      onClick={() => handleDeleteRule(rule)}
                      className="inline-flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-100 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300"
                    >
                      <Trash2 className="h-4 w-4" />
                      Delete
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr,1.05fr]">
        <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/85">
          <div className="flex items-center gap-3">
            <Activity className="h-5 w-5 text-emerald-600 dark:text-emerald-300" />
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Test cases and regression
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Capture expected behavior and rerun it when rules change.
              </p>
            </div>
          </div>

          <form onSubmit={handleCreateTestCase} className="mt-5 space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Guardrail rule
                <select
                  value={testCaseRuleId}
                  onChange={(e) => setTestCaseRuleId(e.target.value)}
                  className={`${inputCls} mt-1`}
                >
                  <option value="">Select a rule</option>
                  {rules.map((rule) => (
                    <option key={rule.id} value={rule.id}>
                      {rule.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Expected decision
                <select
                  value={testCaseExpectedDecision}
                  onChange={(e) => setTestCaseExpectedDecision(e.target.value)}
                  className={`${inputCls} mt-1`}
                >
                  <option value="allow">allow</option>
                  <option value="block">block</option>
                  <option value="modify">modify</option>
                </select>
              </label>
            </div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              Test case name
              <input
                value={testCaseName}
                onChange={(e) => setTestCaseName(e.target.value)}
                placeholder="PII should be blocked"
                className={`${inputCls} mt-1`}
              />
            </label>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              Input text
              <textarea
                value={testCaseInput}
                onChange={(e) => setTestCaseInput(e.target.value)}
                className={`${inputCls} mt-1 min-h-24`}
                placeholder="Enter the sample text that should trigger this decision."
              />
            </label>
            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={savingTestCase || !testCaseRuleId || !testCaseName.trim() || !testCaseInput.trim()}
                className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
              >
                {savingTestCase ? 'Saving...' : 'Add test case'}
              </button>
              <select
                value={selectedRegressionRuleId}
                onChange={(e) => setSelectedRegressionRuleId(e.target.value)}
                className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
              >
                <option value="">Run regression for...</option>
                {rules.map((rule) => (
                  <option key={rule.id} value={rule.id}>
                    {rule.name}
                  </option>
                ))}
              </select>
              <button
                onClick={() => void handleRunRegression()}
                type="button"
                disabled={runningRegression || !selectedRegressionRuleId}
                className="inline-flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 transition hover:bg-blue-100 disabled:opacity-50 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300"
              >
                <Play className="h-4 w-4" />
                {runningRegression ? 'Running...' : 'Run regression'}
              </button>
            </div>
          </form>

          <div className="mt-5 space-y-3">
            {testCases.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
                No test cases yet.
              </div>
            ) : (
              testCases.slice(0, 10).map((testCase) => (
                <div
                  key={testCase.id}
                  className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-800 dark:bg-slate-950/60"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium text-slate-900 dark:text-white">
                        {testCase.name}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        Expected: {testCase.expected_decision}
                      </div>
                      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                        {testCase.input_text}
                      </p>
                    </div>
                    <button
                      onClick={() => handleDeleteTestCase(testCase)}
                      className="rounded-lg p-2 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/50 dark:hover:text-rose-300"
                      title="Delete test case"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          {regressionReport && (
            <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-800 dark:bg-slate-950/60">
              <div className="flex flex-wrap items-center gap-3">
                <div className="font-semibold text-slate-900 dark:text-white">
                  Regression report: {regressionReport.guardrail_name}
                </div>
                <span className="text-sm text-slate-500">
                  {regressionReport.passed}/{regressionReport.total_cases} passed
                </span>
              </div>
              <div className="mt-4 space-y-2">
                {regressionReport.results.map((result) => (
                  <div
                    key={result.test_case_id}
                    className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"
                  >
                    <div>
                      <div className="font-medium text-slate-900 dark:text-white">
                        {result.test_case_name}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        Expected {result.expected_decision} | Actual {result.actual_decision} |{' '}
                        {result.latency_ms.toFixed(1)} ms
                      </div>
                      {result.reason && (
                        <div className="mt-1 text-sm text-slate-500">{result.reason}</div>
                      )}
                    </div>
                    <span
                      className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase ${
                        result.passed
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                          : 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300'
                      }`}
                    >
                      {result.passed ? 'Passed' : 'Failed'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/85">
          <div className="flex items-center gap-3">
            <BellRing className="h-5 w-5 text-amber-600 dark:text-amber-300" />
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Alerts and live events
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Review what fired in production, mark false positives, and acknowledge anomalies.
              </p>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              onClick={handleEvaluateAlerts}
              disabled={refreshingAlerts}
              className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-amber-600 disabled:opacity-50"
            >
              <TriangleAlert className="h-4 w-4" />
              {refreshingAlerts ? 'Evaluating...' : 'Evaluate alerts'}
            </button>
            <Link
              href="/guardrails/violations"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              <Activity className="h-4 w-4" />
              Open violations log
            </Link>
          </div>

          <div className="mt-5 grid gap-3">
            {alerts.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
                No alerts recorded yet.
              </div>
            ) : (
              alerts.map((alert) => (
                <div
                  key={alert.id}
                  className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-800 dark:bg-slate-950/60"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-medium text-slate-900 dark:text-white">
                          {alert.title}
                        </h3>
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                            severityColors[alert.severity] || severityColors.medium
                          }`}
                        >
                          {alert.severity}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-slate-500">
                        {alert.description || 'No description'}
                      </p>
                      <div className="mt-2 text-xs text-slate-500">
                        Type: {alert.alert_type} {alert.guardrail_name ? `- ${alert.guardrail_name}` : ''}
                      </div>
                    </div>
                    {alert.status !== 'acknowledged' && (
                      <button
                        onClick={() => handleAcknowledgeAlert(alert.id)}
                        className="inline-flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-100 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300"
                      >
                        <CheckCircle2 className="h-4 w-4" />
                        Acknowledge
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="mt-6 rounded-2xl border border-slate-200 dark:border-slate-800">
            <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-800">
              <h3 className="font-medium text-slate-900 dark:text-white">
                Recent enforcement events
              </h3>
            </div>
            <div className="max-h-[28rem] overflow-auto">
              {events?.items?.length ? (
                <div className="divide-y divide-slate-200 dark:divide-slate-800">
                  {events.items.map((event) => (
                    <div key={event.id} className="p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium text-slate-900 dark:text-white">
                              {event.guardrail_name}
                            </span>
                            <span
                              className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                                decisionColors[event.decision] || decisionColors.allow
                              }`}
                            >
                              {event.decision}
                            </span>
                            {event.is_false_positive && (
                              <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-violet-700 dark:bg-violet-950 dark:text-violet-300">
                                false positive
                              </span>
                            )}
                          </div>
                          <div className="mt-1 text-sm text-slate-500">
                            {event.reason || 'No reason recorded'}
                          </div>
                          <div className="mt-2 text-xs text-slate-500">
                            Model: {event.model || '--'} | {event.latency_ms.toFixed(1)} ms |{' '}
                            {new Date(event.created_at).toLocaleString()}
                          </div>
                        </div>
                        {!event.is_false_positive && event.decision !== 'allow' && (
                          <button
                            onClick={() => handleMarkFalsePositive(event.id)}
                            className="rounded-xl border border-violet-200 bg-violet-50 px-3 py-2 text-sm font-semibold text-violet-700 transition hover:bg-violet-100 dark:border-violet-900 dark:bg-violet-950 dark:text-violet-300"
                          >
                            Mark false positive
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-6 text-sm text-slate-500">No recent events.</div>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/85">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Partner guardrails
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              External moderation and safety vendors that can run alongside custom rules.
            </p>
          </div>
          <div className="text-sm text-slate-500">
            {partners.length} configured partner{partners.length === 1 ? '' : 's'}
          </div>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          {partners.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-sm text-slate-500">
              No partner guardrails configured.
            </div>
          ) : (
            partners.map((partner) => (
              <div
                key={partner.id}
                className="rounded-2xl border border-slate-200 bg-slate-50/80 p-5 dark:border-slate-800 dark:bg-slate-950/60"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-slate-900 dark:text-white">
                        {partner.name}
                      </h3>
                      <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                        {partner.provider}
                      </span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                          partner.health_status === 'healthy'
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                            : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                        }`}
                      >
                        {partner.health_status || 'unchecked'}
                      </span>
                    </div>
                    <div className="mt-2 text-sm text-slate-500">
                      {partner.mode} mode | timeout {partner.timeout_ms} ms | fallback{' '}
                      {partner.fallback_action}
                    </div>
                    <div className="mt-1 text-xs text-slate-500">
                      Total calls {partner.total_calls} | Cost {fmtCurrency(partner.total_cost_usd)}
                    </div>
                  </div>
                  <button
                    onClick={() => handleTogglePartnerStatus(partner)}
                    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
                      partner.status === 'active'
                        ? 'bg-emerald-600'
                        : 'bg-slate-300 dark:bg-slate-700'
                    }`}
                    title={partner.status === 'active' ? 'Disable partner' : 'Enable partner'}
                  >
                    <span
                      className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition ${
                        partner.status === 'active' ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>

                <div className="mt-5 flex flex-wrap gap-2">
                  <button
                    onClick={() => openPartnerEdit(partner)}
                    className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    <Edit2 className="h-4 w-4" />
                    Edit
                  </button>
                  <button
                    onClick={() => handleHealthCheckPartner(partner)}
                    className="inline-flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700 transition hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300"
                  >
                    <Activity className="h-4 w-4" />
                    Health check
                  </button>
                  <button
                    onClick={() => handleDeletePartner(partner)}
                    className="inline-flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-100 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {showRuleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl dark:border dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                {editingRule ? 'Edit guardrail rule' : 'Create guardrail rule'}
              </h2>
              <button
                onClick={() => setShowRuleModal(false)}
                className="rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSaveRule} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                  Rule name
                </label>
                <input
                  required
                  value={ruleName}
                  onChange={(e) => setRuleName(e.target.value)}
                  className={`${inputCls} mt-1`}
                  placeholder="Redact PII in prompts"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                  Description
                </label>
                <textarea
                  value={ruleDescription}
                  onChange={(e) => setRuleDescription(e.target.value)}
                  className={`${inputCls} mt-1 min-h-20`}
                  placeholder="What should this guardrail prevent?"
                />
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Mode
                  <select
                    value={ruleMode}
                    onChange={(e) => setRuleMode(e.target.value)}
                    className={`${inputCls} mt-1`}
                  >
                    <option value="pre_call">pre_call</option>
                    <option value="post_call">post_call</option>
                    <option value="during_call">during_call</option>
                    <option value="both">both</option>
                  </select>
                </label>
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Rule type
                  <select
                    value={ruleType}
                    onChange={(e) => setRuleType(e.target.value)}
                    disabled={Boolean(editingRule)}
                    className={`${inputCls} mt-1`}
                  >
                    <option value="custom">custom</option>
                    <option value="template">template</option>
                  </select>
                </label>
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Severity
                  <select
                    value={ruleSeverity}
                    onChange={(e) => setRuleSeverity(e.target.value)}
                    className={`${inputCls} mt-1`}
                  >
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                    <option value="strict">strict</option>
                  </select>
                </label>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                  Logic
                </label>
                <textarea
                  value={ruleLogic}
                  onChange={(e) => setRuleLogic(e.target.value)}
                  className={`${inputCls} mt-1 min-h-36 font-mono text-xs`}
                  placeholder="result = block('Detected secret')"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                  Config JSON
                </label>
                <textarea
                  value={ruleConfigText}
                  onChange={(e) => setRuleConfigText(e.target.value)}
                  className={`${inputCls} mt-1 min-h-24 font-mono text-xs`}
                  placeholder='{"threshold": 0.8}'
                />
              </div>
              <label className="flex items-center gap-3 rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-700 dark:border-slate-800 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={ruleSkipSystemMessages}
                  onChange={(e) => setRuleSkipSystemMessages(e.target.checked)}
                />
                Skip system messages during evaluation
              </label>
              <div className="flex justify-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowRuleModal(false)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingRule || !ruleName.trim()}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
                >
                  {savingRule ? 'Saving...' : editingRule ? 'Update rule' : 'Create rule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showPartnerModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl dark:border dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                {partnerForm.id ? 'Edit partner guardrail' : 'Add partner guardrail'}
              </h2>
              <button
                onClick={() => setShowPartnerModal(false)}
                className="rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSavePartner} className="mt-4 space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Provider
                  <select
                    value={partnerForm.provider}
                    onChange={(e) =>
                      setPartnerForm((current) => ({ ...current, provider: e.target.value }))
                    }
                    disabled={Boolean(partnerForm.id)}
                    className={`${inputCls} mt-1`}
                  >
                    <option value="presidio">presidio</option>
                    <option value="bedrock">bedrock</option>
                    <option value="lakera">lakera</option>
                    <option value="openai_moderation">openai_moderation</option>
                    <option value="google_model_armor">google_model_armor</option>
                    <option value="guardrails_ai">guardrails_ai</option>
                    <option value="prompt_security">prompt_security</option>
                    <option value="lasso">lasso</option>
                  </select>
                </label>
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Name
                  <input
                    value={partnerForm.name}
                    onChange={(e) =>
                      setPartnerForm((current) => ({ ...current, name: e.target.value }))
                    }
                    className={`${inputCls} mt-1`}
                  />
                </label>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Mode
                  <select
                    value={partnerForm.mode}
                    onChange={(e) =>
                      setPartnerForm((current) => ({ ...current, mode: e.target.value }))
                    }
                    className={`${inputCls} mt-1`}
                  >
                    <option value="pre_call">pre_call</option>
                    <option value="post_call">post_call</option>
                    <option value="during_call">during_call</option>
                    <option value="both">both</option>
                  </select>
                </label>
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Timeout (ms)
                  <input
                    type="number"
                    min={100}
                    max={30000}
                    value={partnerForm.timeout_ms}
                    onChange={(e) =>
                      setPartnerForm((current) => ({
                        ...current,
                        timeout_ms: Number(e.target.value) || 2000,
                      }))
                    }
                    className={`${inputCls} mt-1`}
                  />
                </label>
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Priority
                  <input
                    type="number"
                    min={0}
                    value={partnerForm.priority}
                    onChange={(e) =>
                      setPartnerForm((current) => ({
                        ...current,
                        priority: Number(e.target.value) || 200,
                      }))
                    }
                    className={`${inputCls} mt-1`}
                  />
                </label>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Endpoint URL
                  <input
                    value={partnerForm.endpoint_url}
                    onChange={(e) =>
                      setPartnerForm((current) => ({
                        ...current,
                        endpoint_url: e.target.value,
                      }))
                    }
                    className={`${inputCls} mt-1`}
                    placeholder="https://..."
                  />
                </label>
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Fallback action
                  <select
                    value={partnerForm.fallback_action}
                    onChange={(e) =>
                      setPartnerForm((current) => ({
                        ...current,
                        fallback_action: e.target.value,
                      }))
                    }
                    className={`${inputCls} mt-1`}
                  >
                    <option value="allow">allow</option>
                    <option value="block">block</option>
                  </select>
                </label>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Config JSON
                  <textarea
                    value={partnerForm.config_text}
                    onChange={(e) =>
                      setPartnerForm((current) => ({
                        ...current,
                        config_text: e.target.value,
                      }))
                    }
                    className={`${inputCls} mt-1 min-h-32 font-mono text-xs`}
                  />
                </label>
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Credentials JSON
                  <textarea
                    value={partnerForm.credentials_text}
                    onChange={(e) =>
                      setPartnerForm((current) => ({
                        ...current,
                        credentials_text: e.target.value,
                      }))
                    }
                    className={`${inputCls} mt-1 min-h-32 font-mono text-xs`}
                  />
                </label>
              </div>

              <div className="flex justify-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowPartnerModal(false)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingPartner || !partnerForm.name.trim()}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
                >
                  {savingPartner ? 'Saving...' : partnerForm.id ? 'Update partner' : 'Create partner'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{value}</p>
    </div>
  )
}
