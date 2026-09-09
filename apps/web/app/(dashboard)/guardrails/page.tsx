'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { useSession } from 'next-auth/react'
import { useSearchParams, useRouter } from 'next/navigation'
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
  getGuardrailsFinopsPosture,
} from '@/lib/api'
import { num } from '@/lib/utils'
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
  GuardrailsFinopsPosture,
} from '@/types/api'

const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-rose-500'

const severityColors: Record<string, string> = {
  off: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  low: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  medium: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  high: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  strict: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
  critical: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
}

const decisionColors: Record<string, string> = {
  allow: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  block: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
  modify: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
}

type Tab = 'overview' | 'rules' | 'filters' | 'test-lab' | 'partners' | 'alerts'
const TABS: Tab[] = ['overview', 'rules', 'filters', 'test-lab', 'partners', 'alerts']

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
  return { provider: 'presidio', name: '', mode: 'pre_call', endpoint_url: '', timeout_ms: 2000, fallback_action: 'allow', priority: 200, status: 'active', config_text: '{}', credentials_text: '{}' }
}

export default function GuardrailsPage() {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey
  const searchParams = useSearchParams()
  const router = useRouter()

  const activeTab = (TABS.includes(searchParams.get('tab') as Tab) ? searchParams.get('tab') as Tab : 'overview') as Tab
  function setTab(t: Tab) { const p = new URLSearchParams(searchParams.toString()); if (t === 'overview') p.delete('tab'); else p.set('tab', t); router.replace(`?${p.toString()}`, { scroll: false }) }

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
  const [finopsPosture, setFinopsPosture] = useState<GuardrailsFinopsPosture | null>(null)
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

  const activeRules = useMemo(() => rules.filter((r) => r.status === 'active'), [rules])
  const filteredRules = useMemo(() => {
    return rules.filter((r) => {
      const q = searchQuery.toLowerCase()
      const matchesSearch = r.name.toLowerCase().includes(q) || (r.description || '').toLowerCase().includes(q)
      const matchesStatus = statusFilter === 'all' || r.status === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [rules, searchQuery, statusFilter])
  const testCaseCounts = useMemo(() => { const m = new Map<string, number>(); for (const tc of testCases) m.set(tc.guardrail_rule_id, (m.get(tc.guardrail_rule_id) || 0) + 1); return m }, [testCases])

  async function loadData() {
    if (!apiKey) return
    setLoading(true)
    try {
      const [rulesRes, statsRes, eventsRes, templatesRes, partnersRes, filtersRes, testCasesRes, alertsRes] = await Promise.all([
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
      if (!testCaseRuleId && rulesRes.items.length > 0) setTestCaseRuleId(rulesRes.items[0].id)
      if (!selectedRegressionRuleId && rulesRes.items.length > 0) setSelectedRegressionRuleId(rulesRes.items[0].id)
      setSelectedRuleIds((c) => c.filter((id) => rulesRes.items.some((r) => r.id === id)))
    } catch { toast.error('Failed to load guardrails') } finally { setLoading(false) }
  }

  useEffect(() => {
    loadData()
    if (apiKey) {
      getGuardrailsObservePosture(apiKey).then(setObservePosture).catch(() => {})
      getGuardrailsFinopsPosture(apiKey).then(setFinopsPosture).catch(() => {})
    }
  }, [apiKey])

  function resetRuleForm() { setRuleName(''); setRuleDescription(''); setRuleMode('pre_call'); setRuleType('custom'); setRuleSeverity('medium'); setRuleLogic(''); setRuleConfigText('{}'); setRuleSkipSystemMessages(false); setEditingRule(null) }
  function openRuleEdit(rule: GuardrailRuleResponse) { setEditingRule(rule); setRuleName(rule.name); setRuleDescription(rule.description || ''); setRuleMode(rule.mode || 'pre_call'); setRuleType(rule.rule_type || 'custom'); setRuleSeverity(rule.severity || 'medium'); setRuleLogic(rule.logic || ''); setRuleConfigText(JSON.stringify(rule.config || {}, null, 2)); setRuleSkipSystemMessages(rule.skip_system_messages || false); setShowRuleModal(true) }
  function applyTemplate(template: GuardrailTemplate) { resetRuleForm(); setRuleName(template.name); setRuleDescription(template.description || ''); setRuleMode(template.mode || 'pre_call'); setRuleType('template'); setRuleSeverity('medium'); setRuleLogic(template.default_logic || ''); setRuleConfigText(JSON.stringify(template.default_config || {}, null, 2)); setShowRuleModal(true) }

  function openPartnerEdit(partner: PartnerGuardrailResponse) { setPartnerForm({ id: partner.id, provider: partner.provider, name: partner.name, mode: partner.mode, endpoint_url: partner.endpoint_url || '', timeout_ms: partner.timeout_ms, fallback_action: partner.fallback_action, priority: partner.priority, status: partner.status, config_text: JSON.stringify(partner.config || {}, null, 2), credentials_text: '{}' }); setShowPartnerModal(true) }

  async function handleSaveRule(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !ruleName.trim()) return
    setSavingRule(true)
    try {
      const parsedConfig = ruleConfigText.trim() ? JSON.parse(ruleConfigText) : {}
      if (editingRule) {
        await updateGuardrailRule(apiKey, editingRule.id, { name: ruleName.trim(), description: ruleDescription.trim() || undefined, mode: ruleMode, severity: ruleSeverity, logic: ruleLogic.trim() || undefined, config: parsedConfig, skip_system_messages: ruleSkipSystemMessages })
        toast.success('Guardrail rule updated')
      } else {
        await createGuardrailRule(apiKey, { name: ruleName.trim(), description: ruleDescription.trim() || undefined, mode: ruleMode, rule_type: ruleType, severity: ruleSeverity, logic: ruleLogic.trim() || undefined, config: parsedConfig, status: 'active', skip_system_messages: ruleSkipSystemMessages })
        toast.success('Guardrail rule created')
      }
      setShowRuleModal(false); resetRuleForm(); await loadData()
    } catch { toast.error('Failed to save guardrail rule') } finally { setSavingRule(false) }
  }

  async function handleDeleteRule(rule: GuardrailRuleResponse) { if (!apiKey || !confirm(`Delete "${rule.name}"?`)) return; try { await deleteGuardrailRule(apiKey, rule.id); toast.success('Deleted'); await loadData() } catch { toast.error('Failed to delete') } }
  async function handleToggleRuleStatus(rule: GuardrailRuleResponse) { if (!apiKey) return; try { await updateGuardrailRule(apiKey, rule.id, { status: rule.status === 'active' ? 'disabled' : 'active' }); toast.success(rule.status === 'active' ? 'Paused' : 'Activated'); await loadData() } catch { toast.error('Failed to update') } }

  async function handleBulkRuleStatus(nextStatus: 'active' | 'disabled') {
    if (!apiKey || selectedRuleIds.length === 0) return
    setBulkUpdatingRules(true)
    try { await Promise.all(selectedRuleIds.map((id) => updateGuardrailRule(apiKey, id, { status: nextStatus }))); toast.success(`${nextStatus === 'active' ? 'Activated' : 'Paused'} ${selectedRuleIds.length} rule(s)`); setSelectedRuleIds([]); await loadData() } catch { toast.error('Failed to update') } finally { setBulkUpdatingRules(false) }
  }

  function toggleRuleSelection(id: string) { setSelectedRuleIds((c) => c.includes(id) ? c.filter((x) => x !== id) : [...c, id]) }
  function toggleAllVisibleRules() { const vis = filteredRules.map((r) => r.id); const allSel = vis.length > 0 && vis.every((id) => selectedRuleIds.includes(id)); if (allSel) { setSelectedRuleIds((c) => c.filter((id) => !vis.includes(id))); return }; setSelectedRuleIds((c) => Array.from(new Set([...c, ...vis]))) }

  async function handleSaveFilters() { if (!apiKey) return; setSavingFilters(true); try { await activateContentFilters(apiKey, { filters: filters.map((f) => ({ filter_name: f.filter_name, severity: f.severity, enabled: f.enabled })) }); toast.success('Filters updated'); await loadData() } catch { toast.error('Failed to save') } finally { setSavingFilters(false) } }

  async function handleRunPlayground() {
    if (!apiKey || !playgroundText.trim()) return
    setRunningPlayground(true); setPlaygroundResponse(null)
    try { const payload = { texts: [playgroundText.trim()], model: playgroundModel.trim() || undefined }; const result = playgroundRuleId === 'all' ? await testAllGuardrails(apiKey, payload) : await testGuardrailRule(apiKey, playgroundRuleId, payload); setPlaygroundResponse(result); toast.success('Test complete') } catch { toast.error('Failed') } finally { setRunningPlayground(false) }
  }

  async function handleCreateTestCase(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !testCaseRuleId || !testCaseName.trim() || !testCaseInput.trim()) return
    setSavingTestCase(true)
    try { await createGuardrailTestCase(apiKey, { guardrail_rule_id: testCaseRuleId, name: testCaseName.trim(), input_text: testCaseInput.trim(), expected_decision: testCaseExpectedDecision }); toast.success('Test case created'); setTestCaseName(''); setTestCaseInput(''); await loadData() } catch { toast.error('Failed') } finally { setSavingTestCase(false) }
  }

  async function handleDeleteTestCase(tc: GuardrailTestCaseResponse) { if (!apiKey || !confirm(`Delete "${tc.name}"?`)) return; try { await deleteGuardrailTestCase(apiKey, tc.id); toast.success('Deleted'); await loadData() } catch { toast.error('Failed') } }

  async function handleRunRegression(ruleId?: string) {
    const tid = ruleId || selectedRegressionRuleId; if (!apiKey || !tid) return
    setRunningRegression(true); setRegressionReport(null)
    try { const report = await runGuardrailRegression(apiKey, tid); setRegressionReport(report); toast.success(`${report.passed}/${report.total_cases} passed`) } catch { toast.error('Failed') } finally { setRunningRegression(false) }
  }

  async function handleSavePartner(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey || !partnerForm.name.trim()) return
    setSavingPartner(true)
    try {
      const config = partnerForm.config_text.trim() ? JSON.parse(partnerForm.config_text) : {}
      const credentials = partnerForm.credentials_text.trim() ? JSON.parse(partnerForm.credentials_text) : {}
      const payload = { provider: partnerForm.provider, name: partnerForm.name.trim(), mode: partnerForm.mode, endpoint_url: partnerForm.endpoint_url.trim() || undefined, timeout_ms: partnerForm.timeout_ms, fallback_action: partnerForm.fallback_action, priority: partnerForm.priority, status: partnerForm.status, config, credentials }
      if (partnerForm.id) { await updatePartnerGuardrail(apiKey, partnerForm.id, payload); toast.success('Updated') } else { await createPartnerGuardrail(apiKey, payload); toast.success('Created') }
      setShowPartnerModal(false); setPartnerForm(emptyPartnerForm()); await loadData()
    } catch { toast.error('Failed') } finally { setSavingPartner(false) }
  }

  async function handleDeletePartner(p: PartnerGuardrailResponse) { if (!apiKey || !confirm(`Delete "${p.name}"?`)) return; try { await deletePartnerGuardrail(apiKey, p.id); toast.success('Deleted'); await loadData() } catch { toast.error('Failed') } }
  async function handleHealthCheckPartner(p: PartnerGuardrailResponse) { if (!apiKey) return; try { await healthCheckPartner(apiKey, p.id); toast.success(`Health checked ${p.name}`); await loadData() } catch { toast.error('Failed') } }
  async function handleTogglePartnerStatus(p: PartnerGuardrailResponse) { if (!apiKey) return; try { await updatePartnerGuardrail(apiKey, p.id, { status: p.status === 'active' ? 'disabled' : 'active' }); toast.success(p.status === 'active' ? 'Paused' : 'Activated'); await loadData() } catch { toast.error('Failed') } }

  async function handleMarkFalsePositive(eventId: string) { if (!apiKey) return; const reason = prompt('Why false positive? (optional)') || ''; try { await submitGuardrailFeedback(apiKey, eventId, { is_false_positive: true, reason: reason.trim() || undefined }); toast.success('Marked false positive'); await loadData() } catch { toast.error('Failed') } }
  async function handleEvaluateAlerts() { if (!apiKey) return; setRefreshingAlerts(true); try { const created = await evaluateGuardrailAlerts(apiKey, 1, 24); await loadData(); toast.success(created.length > 0 ? `${created.length} alert(s) generated` : 'No new alerts') } catch { toast.error('Failed') } finally { setRefreshingAlerts(false) } }
  async function handleAcknowledgeAlert(id: string) { if (!apiKey) return; try { await acknowledgeGuardrailAlert(apiKey, id); toast.success('Acknowledged'); await loadData() } catch { toast.error('Failed') } }

  if (!apiKey) return <div className="p-8 text-xs text-slate-500">Sign in to view guardrails.</div>

  return (
    <div className="space-y-3">
      {/* ── Header ───────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-rose-500 to-red-600 shadow-lg shadow-rose-500/25">
            <ShieldCheck className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white">Guardrails & Safety</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Content filters, custom rules, partner checks, test coverage, and enforcement telemetry.</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <button onClick={() => { resetRuleForm(); setShowRuleModal(true) }} className="flex items-center gap-1 rounded-lg bg-rose-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-rose-700">
            <Plus className="h-3 w-3" /> Add Rule
          </button>
          <button onClick={() => { setPartnerForm(emptyPartnerForm()); setShowPartnerModal(true) }} className="flex items-center gap-1 rounded-lg bg-slate-100 dark:bg-slate-800 px-2.5 py-1 text-[10px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700">
            <ShieldCheck className="h-3 w-3" /> Add Partner
          </button>
        </div>
      </div>

      {/* ── KPI strip ────────────────────────────── */}
      <div className="grid grid-cols-8 gap-2">
        {[
          { label: 'Rules', value: rules.length },
          { label: 'Active', value: activeRules.length, accent: true },
          { label: 'Evaluations', value: stats?.total_evaluations ?? '—' },
          { label: 'Block Rate', value: stats?.block_rate != null ? `${(num(stats.block_rate) * 100).toFixed(1)}%` : '—' },
          { label: 'Avg Latency', value: stats?.avg_latency_ms != null ? `${num(stats.avg_latency_ms).toFixed(0)}ms` : '—' },
          { label: 'Partners', value: partners.length },
          { label: 'Templates', value: templates.length },
          { label: 'Alerts', value: alerts.length },
        ].map(({ label, value, accent }) => (
          <div key={label} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-2 py-1.5 text-center">
            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{label}</p>
            <p className={`text-sm font-bold ${accent ? 'text-rose-600 dark:text-rose-400' : 'text-slate-900 dark:text-white'}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* ── Tab bar ───────────────────────────────── */}
      <div className="flex items-center gap-1 border-b border-slate-200 dark:border-slate-700 pb-px">
        {([
          ['overview', 'Overview'],
          ['rules', 'Rules'],
          ['filters', 'Filters'],
          ['test-lab', 'Test Lab'],
          ['partners', 'Partners'],
          ['alerts', 'Alerts'],
        ] as [Tab, string][]).map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)}
            className={`px-3 py-1.5 text-xs font-semibold rounded-t-lg transition-colors ${activeTab === key ? 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300 border-b-2 border-rose-500' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'}`}
          >{label}</button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════ */}
      {/* ── OVERVIEW TAB ─────────────────────────────── */}
      {activeTab === 'overview' && (
        <div className="space-y-3">
          {/* Posture chips */}
          {observePosture && (
            <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 p-3 space-y-2">
              <h3 className="text-[10px] font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Observe Posture ({observePosture.period_days}d)</h3>
              <div className="flex flex-wrap gap-1.5">
                {[
                  `${observePosture.evaluations.total.toLocaleString()} evaluations`,
                  `${observePosture.evaluations.blocks.toLocaleString()} blocks`,
                  `${(num(observePosture.evaluations.block_rate) * 100).toFixed(1)}% block rate`,
                  `${observePosture.evaluations.modifications.toLocaleString()} modifications`,
                  `${observePosture.evaluations.distinct_rules_fired} rules fired`,
                  `${observePosture.evaluations.distinct_models} models`,
                  observePosture.performance.avg_latency_ms != null ? `${num(observePosture.performance.avg_latency_ms).toFixed(0)}ms avg` : null,
                  observePosture.performance.max_latency_ms != null ? `${num(observePosture.performance.max_latency_ms).toFixed(0)}ms max` : null,
                  `${observePosture.rules.active_rules}/${observePosture.rules.total_rules} active rules`,
                  `${observePosture.mode_breakdown.pre_call} pre · ${observePosture.mode_breakdown.post_call} post`,
                  `${observePosture.feedback.false_positive_count} false positives`,
                ].filter(Boolean).map((chip) => (
                  <span key={chip} className="rounded-full bg-sky-100 dark:bg-sky-900/30 px-2 py-0.5 text-[10px] font-medium text-sky-700 dark:text-sky-300">{chip}</span>
                ))}
              </div>
            </div>
          )}

          {finopsPosture && (
            <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 p-3 space-y-2">
              <h3 className="text-[10px] font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wider">FinOps Posture ({finopsPosture.period_days}d)</h3>
              <div className="flex flex-wrap gap-1.5">
                {[
                  `${finopsPosture.guardrail_context.evaluations_30d.toLocaleString()} evaluations`,
                  `${finopsPosture.guardrail_context.blocks_30d.toLocaleString()} blocks`,
                  `${finopsPosture.guardrail_context.active_rules} active rules`,
                  `${finopsPosture.guardrail_context.active_routes} active routes`,
                  `${finopsPosture.finops_context.budgets} budgets`,
                  `${finopsPosture.finops_context.budget_notifications} notifications`,
                  `${finopsPosture.finops_context.billing_periods} billing periods`,
                  `${finopsPosture.finops_context.chargeback_rules} chargeback rules`,
                ].map((chip) => (
                  <span key={chip} className="rounded-full bg-emerald-100 dark:bg-emerald-900/30 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">{chip}</span>
                ))}
              </div>
            </div>
          )}

          {/* Templates */}
          {templates.length > 0 && (
            <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 p-3 space-y-2">
              <div className="flex items-center gap-2">
                <Sparkles className="h-3.5 w-3.5 text-rose-500" />
                <h3 className="text-[10px] font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Templates</h3>
                <span className="text-[10px] text-slate-400">{templates.length} presets</span>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                {templates.map((t) => (
                  <div key={t.template_id} className="rounded-lg border border-slate-200/60 dark:border-slate-700/40 p-2.5 space-y-1.5 hover:shadow-sm transition">
                    <div className="flex items-center gap-1.5">
                      <span className="rounded-full bg-rose-100 dark:bg-rose-900/30 px-1.5 py-0.5 text-[9px] font-semibold text-rose-700 dark:text-rose-300 uppercase">{t.category.replaceAll('_', ' ')}</span>
                      <span className="text-[9px] text-slate-400 uppercase">{t.mode}</span>
                    </div>
                    <h4 className="text-xs font-semibold text-slate-900 dark:text-white">{t.name}</h4>
                    <p className="text-[10px] text-slate-500 line-clamp-2">{t.description}</p>
                    {t.default_logic && (
                      <pre className="rounded bg-slate-950 p-1.5 text-[9px] text-cyan-100 overflow-hidden whitespace-pre-wrap break-words max-h-16">{t.default_logic}</pre>
                    )}
                    <button onClick={() => applyTemplate(t)} className="flex items-center gap-1 rounded-lg bg-rose-100 dark:bg-rose-900/30 px-2 py-1 text-[10px] font-semibold text-rose-700 dark:text-rose-300 hover:bg-rose-200 dark:hover:bg-rose-800/40 w-full justify-center">
                      <Wand2 className="h-3 w-3" /> Use template
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick nav */}
          <div className="flex flex-wrap gap-1.5">
            {[
              { label: 'Violations Log', href: '/guardrails/violations' },
              { label: 'Gateway', href: '/gateway' },
              { label: 'Security', href: '/security' },
              { label: 'Tool Registry', href: '/tool-registry' },
              { label: 'Tool Policies', href: '/tool-policies' },
              { label: 'Approvals', href: '/approvals' },
              { label: 'Data Capture', href: '/data-capture' },
              { label: 'Audit Log', href: '/audit-log' },
              { label: 'Governance', href: '/governance' },
              { label: 'Policy Dry Run', href: '/policy-dry-run' },
              { label: 'Monitoring', href: '/monitoring' },
              { label: 'Budgets', href: '/budgets' },
            ].map(({ label, href }) => (
              <Link key={label} href={href} className="rounded-full bg-rose-100 dark:bg-rose-900/30 px-2.5 py-1 text-[10px] font-semibold text-rose-700 dark:text-rose-300 hover:bg-rose-200 dark:hover:bg-rose-800/40 transition-colors">{label}</Link>
            ))}
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════ */}
      {/* ── RULES TAB ────────────────────────────────── */}
      {activeTab === 'rules' && (
        <div className="space-y-3">
          {/* Filters + bulk */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative flex-1 min-w-40">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-slate-400" />
              <input type="text" placeholder="Search rules…" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className={`pl-7 ${inputCls}`} />
              {searchQuery && <button onClick={() => setSearchQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"><X className="h-3 w-3" /></button>}
            </div>
            <div className="flex items-center gap-0.5 rounded-lg border border-slate-200 dark:border-slate-700 p-0.5">
              {(['all', 'active', 'disabled', 'draft'] as const).map((s) => (
                <button key={s} onClick={() => setStatusFilter(s)} className={`rounded-md px-2 py-1 text-[10px] font-semibold capitalize transition-colors ${statusFilter === s ? 'bg-rose-600 text-white' : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
                  {s} ({s === 'all' ? rules.length : rules.filter((r) => r.status === s).length})
                </button>
              ))}
            </div>
          </div>

          {/* Bulk bar */}
          <div className="flex items-center justify-between rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-3 py-1.5">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <button onClick={toggleAllVisibleRules} className="flex items-center gap-1 text-[10px] font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900">
                {filteredRules.length > 0 && filteredRules.every((r) => selectedRuleIds.includes(r.id)) ? <CheckSquare className="h-3 w-3" /> : <Square className="h-3 w-3" />}
                Select all
              </button>
              <span>{selectedRuleIds.length} selected</span>
              <span>{activeRules.length} enforceable</span>
            </div>
            <div className="flex gap-1">
              <button onClick={() => void handleBulkRuleStatus('active')} disabled={bulkUpdatingRules || selectedRuleIds.length === 0} className="rounded-lg bg-emerald-100 dark:bg-emerald-900/30 px-2 py-1 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300 disabled:opacity-40">Enable</button>
              <button onClick={() => void handleBulkRuleStatus('disabled')} disabled={bulkUpdatingRules || selectedRuleIds.length === 0} className="rounded-lg bg-amber-100 dark:bg-amber-900/30 px-2 py-1 text-[10px] font-semibold text-amber-700 dark:text-amber-300 disabled:opacity-40">Disable</button>
            </div>
          </div>

          {/* Rule cards */}
          {loading ? (
            <div className="py-12 text-center text-xs text-slate-400">Loading guardrails...</div>
          ) : filteredRules.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-400">No guardrail rules found.</div>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {filteredRules.map((rule) => {
                const isEnforced = rule.status === 'active'
                return (
                  <div key={rule.id} className={`rounded-lg border p-3 transition hover:shadow-sm ${isEnforced ? 'border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40' : 'border-slate-200/40 dark:border-slate-700/30 bg-slate-50/40 dark:bg-slate-950/20 opacity-75'}`}>
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2">
                        <button onClick={() => toggleRuleSelection(rule.id)} className="mt-0.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200">
                          {selectedRuleIds.includes(rule.id) ? <CheckSquare className="h-3.5 w-3.5" /> : <Square className="h-3.5 w-3.5" />}
                        </button>
                        <div>
                          <h3 className="text-xs font-semibold text-slate-900 dark:text-white">{rule.name}</h3>
                          <p className="text-[10px] text-slate-500 line-clamp-2 mt-0.5">{rule.description || 'No description'}</p>
                        </div>
                      </div>
                      <button onClick={() => handleToggleRuleStatus(rule)} className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${isEnforced ? 'bg-emerald-600' : 'bg-slate-300 dark:bg-slate-700'}`}>
                        <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition ${isEnforced ? 'translate-x-4' : 'translate-x-0'}`} />
                      </button>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-1">
                      <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 text-[9px] font-semibold text-slate-600 dark:text-slate-300 uppercase">{rule.mode}</span>
                      <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase ${severityColors[rule.severity] || severityColors.low}`}>{rule.severity}</span>
                      <span className="rounded-full bg-blue-100 dark:bg-blue-900/30 px-1.5 py-0.5 text-[9px] font-semibold text-blue-700 dark:text-blue-300 uppercase">{rule.rule_type}</span>
                      {rule.skip_system_messages && <span className="rounded-full bg-amber-100 dark:bg-amber-900/30 px-1.5 py-0.5 text-[9px] font-semibold text-amber-700 dark:text-amber-300">skip sys</span>}
                      <span className="text-[9px] text-slate-400">{testCaseCounts.get(rule.id) || 0} tests</span>
                    </div>
                    <div className="mt-2 flex gap-1">
                      <button onClick={() => openRuleEdit(rule)} className="flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800">
                        <Edit2 className="h-2.5 w-2.5" /> Edit
                      </button>
                      <button onClick={() => { setSelectedRegressionRuleId(rule.id); void handleRunRegression(rule.id) }} className="flex items-center gap-1 rounded-lg border border-blue-200 dark:border-blue-800 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20">
                        <Play className="h-2.5 w-2.5" /> Regress
                      </button>
                      <button onClick={() => handleDeleteRule(rule)} className="flex items-center gap-1 rounded-lg border border-rose-200 dark:border-rose-800 px-2 py-0.5 text-[10px] font-medium text-rose-700 dark:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-900/20">
                        <Trash2 className="h-2.5 w-2.5" /> Del
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════ */}
      {/* ── FILTERS TAB ──────────────────────────────── */}
      {activeTab === 'filters' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xs font-bold text-slate-900 dark:text-white">Built-in Content Filters</h2>
              <p className="text-[10px] text-slate-500">Toggle baseline filters that run alongside custom rules.</p>
            </div>
            <button onClick={handleSaveFilters} disabled={savingFilters} className="rounded-lg bg-rose-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-rose-700 disabled:opacity-50">{savingFilters ? 'Saving…' : 'Save Filters'}</button>
          </div>
          <div className="space-y-2">
            {filters.map((filter, index) => (
              <div key={filter.filter_name} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <h3 className="text-xs font-semibold text-slate-900 dark:text-white capitalize">{filter.filter_name.replaceAll('_', ' ')}</h3>
                      <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 text-[9px] font-semibold text-slate-500 uppercase">{filter.category}</span>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1">{filter.description}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <select value={filter.severity} onChange={(e) => setFilters((c) => c.map((f, i) => i === index ? { ...f, severity: e.target.value } : f))} className={`w-24 ${inputCls}`}>
                      <option value="off">Off</option>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="strict">Strict</option>
                    </select>
                    <button
                      onClick={() => setFilters((c) => c.map((f, i) => i === index ? { ...f, enabled: !f.enabled } : f))}
                      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${filter.enabled ? 'bg-emerald-600' : 'bg-slate-300 dark:bg-slate-700'}`}
                    >
                      <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition ${filter.enabled ? 'translate-x-4' : 'translate-x-0'}`} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════ */}
      {/* ── TEST LAB TAB ─────────────────────────────── */}
      {activeTab === 'test-lab' && (
        <div className="space-y-3">
          <div className="grid gap-3 xl:grid-cols-2">
            {/* Playground */}
            <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 p-3 space-y-2">
              <div className="flex items-center gap-2">
                <TestTube2 className="h-3.5 w-3.5 text-blue-500" />
                <h3 className="text-xs font-bold text-slate-900 dark:text-white">Test Playground</h3>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <select value={playgroundRuleId} onChange={(e) => setPlaygroundRuleId(e.target.value)} className={inputCls}>
                  <option value="all">All active guardrails</option>
                  {activeRules.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                </select>
                <input value={playgroundModel} onChange={(e) => setPlaygroundModel(e.target.value)} className={inputCls} placeholder="Model hint" />
              </div>
              <textarea value={playgroundText} onChange={(e) => setPlaygroundText(e.target.value)} placeholder="Paste a prompt or response sample…" className={`${inputCls} min-h-24`} />
              <div className="flex gap-1.5">
                <button onClick={handleRunPlayground} disabled={runningPlayground || !playgroundText.trim()} className="flex items-center gap-1 rounded-lg bg-blue-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
                  <Play className="h-3 w-3" /> {runningPlayground ? 'Running…' : 'Run Test'}
                </button>
                <button onClick={() => { if (!playgroundText.trim()) return; setTestCaseInput(playgroundText); if (playgroundRuleId !== 'all') setTestCaseRuleId(playgroundRuleId); toast.success('Copied to test case form') }} className="flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-2.5 py-1 text-[10px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800">
                  <Plus className="h-3 w-3" /> Save as test case
                </button>
              </div>
              {playgroundResponse && (
                <div className="rounded-lg border border-slate-200/60 dark:border-slate-700/40 p-2 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-900 dark:text-white">Decision:</span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${decisionColors[playgroundResponse.overall_decision] || decisionColors.allow}`}>{playgroundResponse.overall_decision}</span>
                    <span className="text-[10px] text-slate-400">{num(playgroundResponse.total_latency_ms).toFixed(1)}ms</span>
                  </div>
                  {playgroundResponse.results.map((r) => (
                    <div key={r.guardrail_id} className="rounded border border-slate-100 dark:border-slate-700/30 p-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-medium text-slate-900 dark:text-white">{r.guardrail_name}</span>
                        <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase ${decisionColors[r.decision] || decisionColors.allow}`}>{r.decision}</span>
                      </div>
                      <p className="text-[10px] text-slate-500 mt-0.5">{r.reason || 'No reason'}</p>
                      {r.modified_texts && r.modified_texts.length > 0 && (
                        <pre className="mt-1 rounded bg-amber-50 dark:bg-amber-900/20 p-1.5 text-[9px] text-amber-800 dark:text-amber-200 whitespace-pre-wrap break-words">{r.modified_texts.join('\n\n')}</pre>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Test cases + regression */}
            <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 p-3 space-y-2">
              <div className="flex items-center gap-2">
                <Activity className="h-3.5 w-3.5 text-emerald-500" />
                <h3 className="text-xs font-bold text-slate-900 dark:text-white">Test Cases & Regression</h3>
              </div>
              <form onSubmit={handleCreateTestCase} className="space-y-2">
                <div className="grid gap-2 sm:grid-cols-2">
                  <select value={testCaseRuleId} onChange={(e) => setTestCaseRuleId(e.target.value)} className={inputCls}>
                    <option value="">Select rule</option>
                    {rules.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                  <select value={testCaseExpectedDecision} onChange={(e) => setTestCaseExpectedDecision(e.target.value)} className={inputCls}>
                    <option value="allow">allow</option>
                    <option value="block">block</option>
                    <option value="modify">modify</option>
                  </select>
                </div>
                <input value={testCaseName} onChange={(e) => setTestCaseName(e.target.value)} placeholder="Test case name" className={inputCls} />
                <textarea value={testCaseInput} onChange={(e) => setTestCaseInput(e.target.value)} placeholder="Input text…" className={`${inputCls} min-h-16`} />
                <div className="flex gap-1.5">
                  <button type="submit" disabled={savingTestCase || !testCaseRuleId || !testCaseName.trim() || !testCaseInput.trim()} className="rounded-lg bg-slate-900 dark:bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-white dark:text-slate-900 hover:bg-slate-700 dark:hover:bg-white disabled:opacity-50">{savingTestCase ? 'Saving…' : 'Add test case'}</button>
                  <select value={selectedRegressionRuleId} onChange={(e) => setSelectedRegressionRuleId(e.target.value)} className={`w-auto ${inputCls}`}>
                    <option value="">Run regression for…</option>
                    {rules.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                  <button type="button" onClick={() => void handleRunRegression()} disabled={runningRegression || !selectedRegressionRuleId} className="flex items-center gap-1 rounded-lg bg-blue-100 dark:bg-blue-900/30 px-2.5 py-1 text-[10px] font-semibold text-blue-700 dark:text-blue-300 disabled:opacity-50">
                    <Play className="h-3 w-3" /> {runningRegression ? 'Running…' : 'Run'}
                  </button>
                </div>
              </form>
              <div className="space-y-1.5 max-h-64 overflow-y-auto">
                {testCases.length === 0 ? (
                  <div className="py-6 text-center text-[10px] text-slate-400">No test cases yet.</div>
                ) : testCases.slice(0, 10).map((tc) => (
                  <div key={tc.id} className="flex items-start justify-between gap-2 rounded border border-slate-100 dark:border-slate-700/30 p-2">
                    <div>
                      <span className="text-[10px] font-medium text-slate-900 dark:text-white">{tc.name}</span>
                      <span className="ml-1 text-[9px] text-slate-400">expects: {tc.expected_decision}</span>
                      <p className="text-[10px] text-slate-500 line-clamp-1 mt-0.5">{tc.input_text}</p>
                    </div>
                    <button onClick={() => handleDeleteTestCase(tc)} className="text-slate-400 hover:text-rose-500"><Trash2 className="h-3 w-3" /></button>
                  </div>
                ))}
              </div>
              {regressionReport && (
                <div className="rounded-lg border border-slate-200/60 dark:border-slate-700/40 p-2 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-900 dark:text-white">{regressionReport.guardrail_name}</span>
                    <span className="text-[10px] text-slate-400">{regressionReport.passed}/{regressionReport.total_cases} passed</span>
                  </div>
                  {regressionReport.results.map((r) => (
                    <div key={r.test_case_id} className="flex items-center justify-between rounded border border-slate-100 dark:border-slate-700/30 p-1.5">
                      <div>
                        <span className="text-[10px] font-medium text-slate-900 dark:text-white">{r.test_case_name}</span>
                        <span className="ml-1 text-[9px] text-slate-400">expected {r.expected_decision} / actual {r.actual_decision} / {num(r.latency_ms).toFixed(1)}ms</span>
                      </div>
                      <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${r.passed ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300'}`}>{r.passed ? 'Pass' : 'Fail'}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════ */}
      {/* ── PARTNERS TAB ─────────────────────────────── */}
      {activeTab === 'partners' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xs font-bold text-slate-900 dark:text-white">Partner Guardrails</h2>
              <p className="text-[10px] text-slate-500">{partners.length} external vendor(s) running alongside custom rules.</p>
            </div>
          </div>
          {partners.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-400">No partner guardrails configured.</div>
          ) : (
            <div className="grid gap-2 lg:grid-cols-2">
              {partners.map((p) => (
                <div key={p.id} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <h3 className="text-xs font-semibold text-slate-900 dark:text-white">{p.name}</h3>
                        <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 text-[9px] font-semibold text-slate-500 uppercase">{p.provider}</span>
                        <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${p.health_status === 'healthy' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>{p.health_status || 'unchecked'}</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5 mt-1.5">
                        {[`${p.mode} mode`, `${p.timeout_ms}ms timeout`, `fallback: ${p.fallback_action}`, `${p.total_calls} calls`, `$${num(p.total_cost_usd || 0).toFixed(2)} cost`].map((chip) => (
                          <span key={chip} className="rounded-full bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 text-[9px] text-slate-500">{chip}</span>
                        ))}
                      </div>
                    </div>
                    <button onClick={() => handleTogglePartnerStatus(p)} className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${p.status === 'active' ? 'bg-emerald-600' : 'bg-slate-300 dark:bg-slate-700'}`}>
                      <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition ${p.status === 'active' ? 'translate-x-4' : 'translate-x-0'}`} />
                    </button>
                  </div>
                  <div className="mt-2 flex gap-1">
                    <button onClick={() => openPartnerEdit(p)} className="flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"><Edit2 className="h-2.5 w-2.5" /> Edit</button>
                    <button onClick={() => handleHealthCheckPartner(p)} className="flex items-center gap-1 rounded-lg border border-blue-200 dark:border-blue-800 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20"><Activity className="h-2.5 w-2.5" /> Health</button>
                    <button onClick={() => handleDeletePartner(p)} className="flex items-center gap-1 rounded-lg border border-rose-200 dark:border-rose-800 px-2 py-0.5 text-[10px] font-medium text-rose-700 dark:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-900/20"><Trash2 className="h-2.5 w-2.5" /> Del</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════ */}
      {/* ── ALERTS TAB ───────────────────────────────── */}
      {activeTab === 'alerts' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xs font-bold text-slate-900 dark:text-white">Alerts & Live Events</h2>
              <p className="text-[10px] text-slate-500">Production alerts, false-positive tracking, and recent enforcement events.</p>
            </div>
            <div className="flex items-center gap-1.5">
              <button onClick={handleEvaluateAlerts} disabled={refreshingAlerts} className="flex items-center gap-1 rounded-lg bg-amber-500 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-amber-600 disabled:opacity-50">
                <TriangleAlert className="h-3 w-3" /> {refreshingAlerts ? 'Evaluating…' : 'Evaluate'}
              </button>
              <Link href="/guardrails/violations" className="flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-2.5 py-1 text-[10px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800">
                <Activity className="h-3 w-3" /> Violations Log
              </Link>
            </div>
          </div>

          {/* Alerts */}
          <div className="space-y-1.5">
            {alerts.length === 0 ? (
              <div className="py-8 text-center text-[10px] text-slate-400">No alerts recorded yet.</div>
            ) : alerts.map((alert) => (
              <div key={alert.id} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 p-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-1.5">
                      <h4 className="text-xs font-semibold text-slate-900 dark:text-white">{alert.title}</h4>
                      <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase ${severityColors[alert.severity] || severityColors.medium}`}>{alert.severity}</span>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-0.5">{alert.description || 'No description'}</p>
                    <span className="text-[9px] text-slate-400">{alert.alert_type} {alert.guardrail_name ? `— ${alert.guardrail_name}` : ''}</span>
                  </div>
                  {alert.status !== 'acknowledged' && (
                    <button onClick={() => handleAcknowledgeAlert(alert.id)} className="flex items-center gap-1 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300 hover:bg-emerald-200 dark:hover:bg-emerald-800/40">
                      <CheckCircle2 className="h-3 w-3" /> Ack
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Recent events */}
          <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 overflow-hidden">
            <div className="border-b border-slate-200/60 dark:border-slate-700/40 px-3 py-2">
              <h3 className="text-xs font-bold text-slate-900 dark:text-white">Recent Enforcement Events</h3>
            </div>
            <div className="max-h-80 overflow-y-auto divide-y divide-slate-100/60 dark:divide-slate-700/30">
              {events?.items?.length ? events.items.map((event) => (
                <div key={event.id} className="px-3 py-2">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-xs font-medium text-slate-900 dark:text-white truncate max-w-[200px]">{event.guardrail_name}</span>
                        <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase ${decisionColors[event.decision] || decisionColors.allow}`}>{event.decision}</span>
                        {event.is_false_positive && <span className="shrink-0 rounded-full bg-violet-100 dark:bg-violet-900/30 px-1.5 py-0.5 text-[9px] font-semibold text-violet-700 dark:text-violet-300">FP</span>}
                      </div>
                      <p className="text-[10px] text-slate-500 mt-0.5 line-clamp-1">{event.reason || 'No reason'}</p>
                      <span className="text-[9px] text-slate-400">{event.model || '—'} · {num(event.latency_ms).toFixed(1)}ms · {new Date(event.created_at).toLocaleString()}</span>
                    </div>
                    {!event.is_false_positive && event.decision !== 'allow' && (
                      <button onClick={() => handleMarkFalsePositive(event.id)} className="shrink-0 rounded-lg border border-violet-200 dark:border-violet-800 px-2 py-0.5 text-[10px] font-medium text-violet-700 dark:text-violet-300 hover:bg-violet-50 dark:hover:bg-violet-900/20 whitespace-nowrap">Mark FP</button>
                    )}
                  </div>
                </div>
              )) : (
                <div className="py-8 text-center text-[10px] text-slate-400">No recent events.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════ */}
      {/* ── RULE MODAL ───────────────────────────────── */}
      {showRuleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 px-4 py-3">
              <h2 className="text-sm font-bold text-slate-900 dark:text-white">{editingRule ? 'Edit Rule' : 'Create Rule'}</h2>
              <button onClick={() => setShowRuleModal(false)} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"><X className="h-4 w-4" /></button>
            </div>
            <form onSubmit={handleSaveRule} className="p-4 space-y-3">
              <input required value={ruleName} onChange={(e) => setRuleName(e.target.value)} className={inputCls} placeholder="Rule name" />
              <textarea value={ruleDescription} onChange={(e) => setRuleDescription(e.target.value)} className={`${inputCls} min-h-16`} placeholder="Description" />
              <div className="grid gap-2 sm:grid-cols-3">
                <select value={ruleMode} onChange={(e) => setRuleMode(e.target.value)} className={inputCls}>
                  <option value="pre_call">pre_call</option>
                  <option value="post_call">post_call</option>
                  <option value="during_call">during_call</option>
                  <option value="both">both</option>
                </select>
                <select value={ruleType} onChange={(e) => setRuleType(e.target.value)} disabled={Boolean(editingRule)} className={inputCls}>
                  <option value="custom">custom</option>
                  <option value="template">template</option>
                </select>
                <select value={ruleSeverity} onChange={(e) => setRuleSeverity(e.target.value)} className={inputCls}>
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                  <option value="strict">strict</option>
                </select>
              </div>
              <textarea value={ruleLogic} onChange={(e) => setRuleLogic(e.target.value)} className={`${inputCls} min-h-28 font-mono`} placeholder="Logic (e.g. result = block('Detected secret'))" />
              <textarea value={ruleConfigText} onChange={(e) => setRuleConfigText(e.target.value)} className={`${inputCls} min-h-16 font-mono`} placeholder='Config JSON (e.g. {"threshold": 0.8})' />
              <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                <input type="checkbox" checked={ruleSkipSystemMessages} onChange={(e) => setRuleSkipSystemMessages(e.target.checked)} />
                Skip system messages
              </label>
              <div className="flex justify-end gap-1.5 border-t border-slate-100 dark:border-slate-800 pt-3">
                <button type="button" onClick={() => setShowRuleModal(false)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800">Cancel</button>
                <button type="submit" disabled={savingRule || !ruleName.trim()} className="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-50">{savingRule ? 'Saving…' : editingRule ? 'Update' : 'Create'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── PARTNER MODAL ────────────────────────────── */}
      {showPartnerModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 px-4 py-3">
              <h2 className="text-sm font-bold text-slate-900 dark:text-white">{partnerForm.id ? 'Edit Partner' : 'Add Partner'}</h2>
              <button onClick={() => setShowPartnerModal(false)} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"><X className="h-4 w-4" /></button>
            </div>
            <form onSubmit={handleSavePartner} className="p-4 space-y-3">
              <div className="grid gap-2 sm:grid-cols-2">
                <select value={partnerForm.provider} onChange={(e) => setPartnerForm((c) => ({ ...c, provider: e.target.value }))} disabled={Boolean(partnerForm.id)} className={inputCls}>
                  {['presidio', 'bedrock', 'lakera', 'openai_moderation', 'google_model_armor', 'guardrails_ai', 'prompt_security', 'lasso'].map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
                <input value={partnerForm.name} onChange={(e) => setPartnerForm((c) => ({ ...c, name: e.target.value }))} className={inputCls} placeholder="Name" />
              </div>
              <div className="grid gap-2 sm:grid-cols-3">
                <select value={partnerForm.mode} onChange={(e) => setPartnerForm((c) => ({ ...c, mode: e.target.value }))} className={inputCls}>
                  <option value="pre_call">pre_call</option>
                  <option value="post_call">post_call</option>
                  <option value="during_call">during_call</option>
                  <option value="both">both</option>
                </select>
                <input type="number" min={100} max={30000} value={partnerForm.timeout_ms} onChange={(e) => setPartnerForm((c) => ({ ...c, timeout_ms: Number(e.target.value) || 2000 }))} className={inputCls} placeholder="Timeout (ms)" />
                <input type="number" min={0} value={partnerForm.priority} onChange={(e) => setPartnerForm((c) => ({ ...c, priority: Number(e.target.value) || 200 }))} className={inputCls} placeholder="Priority" />
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <input value={partnerForm.endpoint_url} onChange={(e) => setPartnerForm((c) => ({ ...c, endpoint_url: e.target.value }))} className={inputCls} placeholder="Endpoint URL" />
                <select value={partnerForm.fallback_action} onChange={(e) => setPartnerForm((c) => ({ ...c, fallback_action: e.target.value }))} className={inputCls}>
                  <option value="allow">allow</option>
                  <option value="block">block</option>
                </select>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <textarea value={partnerForm.config_text} onChange={(e) => setPartnerForm((c) => ({ ...c, config_text: e.target.value }))} className={`${inputCls} min-h-24 font-mono`} placeholder="Config JSON" />
                <textarea value={partnerForm.credentials_text} onChange={(e) => setPartnerForm((c) => ({ ...c, credentials_text: e.target.value }))} className={`${inputCls} min-h-24 font-mono`} placeholder="Credentials JSON" />
              </div>
              <div className="flex justify-end gap-1.5 border-t border-slate-100 dark:border-slate-800 pt-3">
                <button type="button" onClick={() => setShowPartnerModal(false)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800">Cancel</button>
                <button type="submit" disabled={savingPartner || !partnerForm.name.trim()} className="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-50">{savingPartner ? 'Saving…' : partnerForm.id ? 'Update' : 'Create'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
