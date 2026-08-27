'use client'

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import Link from 'next/link'
import { Building2, DollarSign, Link2, Pencil, Plus, Radio, Tags, Trash2, Wand2, X } from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'
import {
  createAutoTagRule,
  createTag,
  deleteAutoTagRule,
  deleteTag,
  getAutoTagRules,
  getTagTree,
  getTags,
  simulateAutoTagging,
  updateAutoTagRule,
  updateTag,
  getTagsFinopsBudgetPosture,
  getDataProtectionOrgPosture,
  getDataProtectionGatewayPosture,
  getGovernanceInternalPosture,
} from '@/lib/api'
import type { AutoTaggingRuleResponse, AutoTaggingSimulationResponse, TagResponse, TagTreeNode, TagsFinopsBudgetPosture, DataProtectionOrgPosture, DataProtectionGatewayPosture, GovernanceInternalPosture } from '@/types/api'

const inputCls =
  'rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:ring-indigo-400'

const MATCH_TYPES = ['equals', 'contains', 'regex', 'prefix', 'suffix'] as const

function TagNode({ node, depth = 0 }: { node: TagTreeNode; depth?: number }) {
  return (
    <div className="space-y-3">
      <div
        className="rounded-2xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-900/70"
        style={{ marginLeft: depth * 20 }}
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="font-semibold text-slate-900 dark:text-slate-50">
              {node.key}: {node.value}
            </p>
            <p className="text-xs text-slate-500">{node.category}</p>
          </div>
          <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-semibold uppercase text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {node.is_active ? 'active' : 'inactive'}
          </span>
        </div>
        {node.description && <p className="mt-2 text-sm text-slate-500">{node.description}</p>}
      </div>
      {node.children.map((child) => (
        <TagNode key={child.id} node={child} depth={depth + 1} />
      ))}
    </div>
  )
}

export default function TagsPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''
  const { canWrite } = useRole()

  const [tags, setTags] = useState<TagResponse[]>([])
  const [tree, setTree] = useState<TagTreeNode[]>([])
  const [rules, setRules] = useState<AutoTaggingRuleResponse[]>([])
  const [simulation, setSimulation] = useState<AutoTaggingSimulationResponse | null>(null)
  const [finopsPosture, setFinopsPosture] = useState<TagsFinopsBudgetPosture | null>(null)
  const [orgPosture, setOrgPosture] = useState<DataProtectionOrgPosture | null>(null)
  const [gatewayPosture, setGatewayPosture] = useState<DataProtectionGatewayPosture | null>(null)
  const [govInternal, setGovInternal] = useState<GovernanceInternalPosture | null>(null)
  const [loading, setLoading] = useState(false)

  const [editingTagId, setEditingTagId] = useState<string | null>(null)
  const [tagCategory, setTagCategory] = useState('workflow')
  const [tagKey, setTagKey] = useState('')
  const [tagValue, setTagValue] = useState('')
  const [tagDescription, setTagDescription] = useState('')
  const [parentTagId, setParentTagId] = useState('')
  const [tagIsActive, setTagIsActive] = useState(true)

  const [editingRuleId, setEditingRuleId] = useState<string | null>(null)
  const [ruleName, setRuleName] = useState('')
  const [ruleDescription, setRuleDescription] = useState('')
  const [matchType, setMatchType] = useState<(typeof MATCH_TYPES)[number]>('contains')
  const [matchField, setMatchField] = useState('prompt')
  const [matchPattern, setMatchPattern] = useState('')
  const [ruleTagKey, setRuleTagKey] = useState('')
  const [ruleTagValue, setRuleTagValue] = useState('')
  const [rulePriority, setRulePriority] = useState('100')
  const [ruleIsActive, setRuleIsActive] = useState(true)

  const [simulationFields, setSimulationFields] = useState(
    JSON.stringify(
      {
        feature: 'support-search',
        prompt: 'search the docs for billing exports',
        provider: 'openai',
      },
      null,
      2,
    ),
  )

  const resetTagForm = useCallback(() => {
    setEditingTagId(null)
    setTagCategory('workflow')
    setTagKey('')
    setTagValue('')
    setTagDescription('')
    setParentTagId('')
    setTagIsActive(true)
  }, [])

  const resetRuleForm = useCallback(() => {
    setEditingRuleId(null)
    setRuleName('')
    setRuleDescription('')
    setMatchType('contains')
    setMatchField('prompt')
    setMatchPattern('')
    setRuleTagKey('')
    setRuleTagValue('')
    setRulePriority('100')
    setRuleIsActive(true)
  }, [])

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [tagList, tagTree, autoRules, simulationResult, posture, orgP, gwP, govI] = await Promise.all([
        getTags(apiKey, { include_inactive: true }),
        getTagTree(apiKey),
        getAutoTagRules(apiKey),
        simulateAutoTagging(apiKey, {
          fields: {
            feature: 'support-search',
            prompt: 'search the docs for billing exports',
            provider: 'openai',
          },
        }),
        getTagsFinopsBudgetPosture(apiKey).catch(() => null),
        getDataProtectionOrgPosture(apiKey).catch(() => null),
        getDataProtectionGatewayPosture(apiKey).catch(() => null),
        getGovernanceInternalPosture(apiKey).catch(() => null),
      ])
      setTags(tagList.items)
      setTree(tagTree.items)
      setRules(autoRules.items)
      setSimulation(simulationResult)
      setFinopsPosture(posture)
      setOrgPosture(orgP)
      setGatewayPosture(gwP)
      setGovInternal(govI)
    } catch {
      toast.error('Failed to load tag management')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => {
    void load()
  }, [load])

  async function handleSaveTag(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    try {
      if (editingTagId) {
        await updateTag(apiKey, editingTagId, {
          category: tagCategory,
          key: tagKey,
          value: tagValue,
          description: tagDescription.trim() || null,
          parent_tag_id: parentTagId || null,
          is_active: tagIsActive,
        })
        toast.success('Tag updated')
      } else {
        await createTag(apiKey, {
          category: tagCategory,
          key: tagKey,
          value: tagValue,
          description: tagDescription.trim() || null,
          parent_tag_id: parentTagId || null,
          is_active: tagIsActive,
        })
        toast.success('Tag created')
      }
      resetTagForm()
      await load()
    } catch {
      toast.error(editingTagId ? 'Failed to update tag' : 'Failed to create tag')
    }
  }

  function startEditTag(tag: TagResponse) {
    setEditingTagId(tag.id)
    setTagCategory(tag.category)
    setTagKey(tag.key)
    setTagValue(tag.value)
    setTagDescription(tag.description ?? '')
    setParentTagId(tag.parent_tag_id ?? '')
    setTagIsActive(tag.is_active)
  }

  async function handleDeleteTag(tag: TagResponse) {
    if (!apiKey || !confirm(`Archive tag ${tag.key}=${tag.value}?`)) return
    try {
      await deleteTag(apiKey, tag.id)
      if (editingTagId === tag.id) resetTagForm()
      toast.success('Tag archived')
      await load()
    } catch {
      toast.error('Failed to archive tag')
    }
  }

  async function handleSaveRule(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    try {
      if (editingRuleId) {
        await updateAutoTagRule(apiKey, editingRuleId, {
          name: ruleName,
          description: ruleDescription.trim() || null,
          match_type: matchType,
          match_field: matchField,
          match_pattern: matchPattern,
          tag_key: ruleTagKey,
          tag_value: ruleTagValue,
          priority: parseInt(rulePriority, 10) || 100,
          is_active: ruleIsActive,
        })
        toast.success('Auto-tagging rule updated')
      } else {
        await createAutoTagRule(apiKey, {
          name: ruleName,
          description: ruleDescription.trim() || null,
          match_type: matchType,
          match_field: matchField,
          match_pattern: matchPattern,
          tag_key: ruleTagKey,
          tag_value: ruleTagValue,
          priority: parseInt(rulePriority, 10) || 100,
          is_active: ruleIsActive,
        })
        toast.success('Auto-tagging rule created')
      }
      resetRuleForm()
      await load()
    } catch {
      toast.error(editingRuleId ? 'Failed to update auto-tagging rule' : 'Failed to create auto-tagging rule')
    }
  }

  function startEditRule(rule: AutoTaggingRuleResponse) {
    setEditingRuleId(rule.id)
    setRuleName(rule.name)
    setRuleDescription(rule.description ?? '')
    setMatchType(rule.match_type as (typeof MATCH_TYPES)[number])
    setMatchField(rule.match_field)
    setMatchPattern(rule.match_pattern)
    setRuleTagKey(rule.tag_key)
    setRuleTagValue(rule.tag_value)
    setRulePriority(String(rule.priority))
    setRuleIsActive(rule.is_active)
  }

  async function handleDeleteRule(rule: AutoTaggingRuleResponse) {
    if (!apiKey || !confirm(`Delete auto-tagging rule ${rule.name}?`)) return
    try {
      await deleteAutoTagRule(apiKey, rule.id)
      if (editingRuleId === rule.id) resetRuleForm()
      toast.success('Auto-tagging rule deleted')
      await load()
    } catch {
      toast.error('Failed to delete auto-tagging rule')
    }
  }

  async function handleRunSimulation() {
    if (!apiKey) return
    try {
      const parsed = JSON.parse(simulationFields) as Record<string, string>
      const result = await simulateAutoTagging(apiKey, { fields: parsed })
      setSimulation(result)
      toast.success('Simulation updated')
    } catch {
      toast.error('Simulation fields must be valid JSON')
    }
  }

  if (!apiKey) {
    return <p className="p-8 text-slate-500">Sign in to view tag management.</p>
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6 md:p-10">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Tags className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Tag Management</h1>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Manage hierarchical tags and the auto-tagging rules that classify workflow traffic.
          </p>
        </div>
        <span className="text-sm text-slate-500">
          {tags.length} tags · {rules.length} rules
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Hierarchy</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{tree.length === 0 ? 0 : tags.filter((item) => item.is_active).length}</p>
          <p className="mt-1 text-sm text-slate-500">Active tags available for routing, governance, and reporting.</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Rule Coverage</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{rules.filter((rule) => rule.is_active).length}</p>
          <p className="mt-1 text-sm text-slate-500">Active rules ready to auto-apply tags during ingest and workflow activity.</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
          <p className="text-xs uppercase tracking-wide text-slate-500">Simulation</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{simulation?.matched.length ?? 0}</p>
          <p className="mt-1 text-sm text-slate-500">Rules matched against the current simulation payload.</p>
        </div>
      </div>

      {finopsPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 dark:border-emerald-800 dark:bg-emerald-950/40">
          <div className="mb-4 flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            <h2 className="text-lg font-semibold text-emerald-900 dark:text-emerald-100">FinOps Budget Attribution</h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl bg-white/80 p-4 dark:bg-slate-900/60">
              <p className="text-xs uppercase tracking-wide text-emerald-700 dark:text-emerald-300">Tagged Spend (30d)</p>
              <p className="mt-1 text-2xl font-bold text-emerald-900 dark:text-emerald-50">${finopsPosture.spend_context.tagged_spend_30d?.toFixed(2) ?? '0.00'}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-4 dark:bg-slate-900/60">
              <p className="text-xs uppercase tracking-wide text-emerald-700 dark:text-emerald-300">Tag-Scoped Budgets</p>
              <p className="mt-1 text-2xl font-bold text-emerald-900 dark:text-emerald-50">{finopsPosture.budget_context.tag_scoped_budgets ?? 0}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-4 dark:bg-slate-900/60">
              <p className="text-xs uppercase tracking-wide text-emerald-700 dark:text-emerald-300">Tag Dimension Rules</p>
              <p className="mt-1 text-2xl font-bold text-emerald-900 dark:text-emerald-50">{finopsPosture.chargeback_context.tag_dimension_rules ?? 0}</p>
            </div>
            <div className="rounded-xl bg-white/80 p-4 dark:bg-slate-900/60">
              <p className="text-xs uppercase tracking-wide text-emerald-700 dark:text-emerald-300">Distinct Tags w/ Spend</p>
              <p className="mt-1 text-2xl font-bold text-emerald-900 dark:text-emerald-50">{finopsPosture.tag_context.distinct_tags_with_spend ?? 0}</p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/budgets" className="text-emerald-700 underline underline-offset-2 hover:text-emerald-900 dark:text-emerald-300 dark:hover:text-emerald-100">Budgets</Link>
            <Link href="/budgets/detail" className="text-emerald-700 underline underline-offset-2 hover:text-emerald-900 dark:text-emerald-300 dark:hover:text-emerald-100">Budget Detail</Link>
            <Link href="/chargeback" className="text-emerald-700 underline underline-offset-2 hover:text-emerald-900 dark:text-emerald-300 dark:hover:text-emerald-100">Chargeback</Link>
          </div>
        </div>
      )}

      {/* Org & Access Scope */}
      {orgPosture && (
        <div className="rounded-2xl border border-blue-200 dark:border-blue-800 bg-blue-50/60 dark:bg-blue-950/40 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <h2 className="text-lg font-semibold text-blue-900 dark:text-blue-100">Org &amp; Access Scope</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Workspace Users</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.user_context.total_users}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Active Tags</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.tag_context.active_tags}</p>
              <p className="text-xs text-slate-500">{orgPosture.tag_context.total_tags} total</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">Capture Policies</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.capture_context.active_policies}</p>
              <p className="text-xs text-slate-500">{orgPosture.capture_context.total_policies} total</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-blue-700 dark:text-blue-300">MCP Servers</p>
              <p className="mt-1 text-2xl font-bold text-blue-900 dark:text-blue-50">{orgPosture.mcp_context.active_servers}</p>
              <p className="text-xs text-slate-500">{orgPosture.mcp_context.total_servers} total</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/organization" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">Organization</Link>
            <Link href="/users" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">Users</Link>
            <Link href="/workspaces" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">Workspaces</Link>
            <Link href="/access-groups" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">Access Groups</Link>
            <Link href="/api-keys" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">API Keys</Link>
            <Link href="/mcp-registry" className="text-blue-700 underline underline-offset-2 hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100">MCP Registry</Link>
          </div>
        </div>
      )}

      {/* Gateway & Observe Runtime */}
      {gatewayPosture && (
        <div className="rounded-2xl border border-violet-200 dark:border-violet-800 bg-violet-50/60 dark:bg-violet-950/40 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Radio className="h-5 w-5 text-violet-600 dark:text-violet-400" />
            <h2 className="text-lg font-semibold text-violet-900 dark:text-violet-100">Gateway &amp; Observe Runtime</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-violet-700 dark:text-violet-300">Gateway Routes</p>
              <p className="mt-1 text-2xl font-bold text-violet-900 dark:text-violet-50">{gatewayPosture.provider_context.total_routes}</p>
              <p className="text-xs text-slate-500">{gatewayPosture.provider_context.total_providers} providers</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-violet-700 dark:text-violet-300">Guardrails</p>
              <p className="mt-1 text-2xl font-bold text-violet-900 dark:text-violet-50">{gatewayPosture.guardrail_context.total_guardrails}</p>
              <p className="text-xs text-slate-500">{gatewayPosture.guardrail_context.guardrail_events_30d} events 30d</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-violet-700 dark:text-violet-300">Tool Calls (30d)</p>
              <p className="mt-1 text-2xl font-bold text-violet-900 dark:text-violet-50">{gatewayPosture.run_context.tool_runs_30d}</p>
              <p className="text-xs text-slate-500">{gatewayPosture.run_context.total_runs_30d} agent runs</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-violet-700 dark:text-violet-300">Alert Firings (30d)</p>
              <p className="mt-1 text-2xl font-bold text-violet-900 dark:text-violet-50">{gatewayPosture.monitoring_context.alert_firings_30d}</p>
              <p className="text-xs text-slate-500">{gatewayPosture.monitoring_context.total_alert_rules} rules</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/gateway" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Gateway</Link>
            <Link href="/guardrails" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Guardrails</Link>
            <Link href="/runs" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Runs</Link>
            <Link href="/request-explorer" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Request Explorer</Link>
            <Link href="/monitoring" className="text-violet-700 underline underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100">Monitoring</Link>
          </div>
        </div>
      )}

      {govInternal && (
        <div className="rounded-2xl border border-rose-200 dark:border-rose-800 bg-rose-50/60 dark:bg-rose-950/30 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-rose-600 dark:text-rose-400" />
            <h2 className="text-lg font-semibold text-rose-900 dark:text-rose-100">Governance Cohesion</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Registered Tools</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.tool_registry_context.total_tools}</p>
              <p className="text-xs text-slate-500">{govInternal.tool_registry_context.enforced_tools} enforced</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Active Policies</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.tool_policies_context.active_policies}</p>
              <p className="text-xs text-slate-500">{govInternal.tool_policies_context.total_policies} total</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Audit Events (30d)</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.audit_context.audit_events_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/60 p-4">
              <p className="text-xs uppercase tracking-wide text-rose-700 dark:text-rose-300">Alert Firings (30d)</p>
              <p className="mt-1 text-2xl font-bold text-rose-900 dark:text-rose-50">{govInternal.alert_rules_context.alert_firings_30d}</p>
              <p className="text-xs text-slate-500">{govInternal.alert_rules_context.active_alert_rules} active rules</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/tool-registry" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tool Registry</Link>
            <Link href="/tool-policies" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Tool Policies</Link>
            <Link href="/approvals" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Approvals</Link>
            <Link href="/data-capture" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Data Capture</Link>
            <Link href="/security" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Security</Link>
            <Link href="/alert-rules" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Alert Rules</Link>
            <Link href="/audit" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Audit Log</Link>
            <Link href="/governance-pack" className="text-rose-700 underline underline-offset-2 hover:text-rose-900 dark:text-rose-300 dark:hover:text-rose-100">Governance Pack</Link>
          </div>
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.2fr_1fr]">
        <section className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Tag Catalog</h2>
                <p className="text-sm text-slate-500">Create, edit, or retire the metadata vocabulary used across the suite.</p>
              </div>
              {editingTagId && (
                <button onClick={resetTagForm} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {canWrite && (
              <form onSubmit={handleSaveTag} className="grid gap-3 md:grid-cols-2">
                <input value={tagCategory} onChange={(e) => setTagCategory(e.target.value)} className={inputCls} placeholder="Category" required />
                <input value={tagKey} onChange={(e) => setTagKey(e.target.value)} className={inputCls} placeholder="Key" required />
                <input value={tagValue} onChange={(e) => setTagValue(e.target.value)} className={inputCls} placeholder="Value" required />
                <select value={parentTagId} onChange={(e) => setParentTagId(e.target.value)} className={inputCls}>
                  <option value="">No parent tag</option>
                  {tags.filter((item) => item.id !== editingTagId).map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.category} / {item.key}={item.value}
                    </option>
                  ))}
                </select>
                <textarea value={tagDescription} onChange={(e) => setTagDescription(e.target.value)} className={`${inputCls} min-h-[90px] md:col-span-2`} placeholder="Description (optional)" />
                <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 md:col-span-2">
                  <input type="checkbox" checked={tagIsActive} onChange={(e) => setTagIsActive(e.target.checked)} />
                  Active
                </label>
                <div className="md:col-span-2">
                  <button type="submit" className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">
                    <Plus className="h-4 w-4" />
                    {editingTagId ? 'Save Tag' : 'Create Tag'}
                  </button>
                </div>
              </form>
            )}

            <div className="mt-5 space-y-2">
              {loading ? (
                <p className="text-sm text-slate-400">Loading tags...</p>
              ) : tags.length === 0 ? (
                <p className="text-sm text-slate-400">No tags created yet.</p>
              ) : (
                tags.map((tag) => (
                  <div key={tag.id} className="flex items-start justify-between gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                    <div>
                      <p className="font-medium text-slate-900 dark:text-slate-100">
                        {tag.key}={tag.value}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">{tag.category}</p>
                      {tag.description && <p className="mt-1 text-xs text-slate-500">{tag.description}</p>}
                    </div>
                    {canWrite && (
                      <div className="flex gap-2">
                        <button onClick={() => startEditTag(tag)} className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button onClick={() => void handleDeleteTag(tag)} className="rounded-lg border border-red-200 p-2 text-red-600 hover:bg-red-50 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/30">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          <section className="space-y-4">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Hierarchy</h2>
            {tree.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-sm text-slate-500 dark:border-slate-700">
                No active tags created yet.
              </div>
            ) : (
              tree.map((node) => <TagNode key={node.id} node={node} />)
            )}
          </section>
        </section>

        <section className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Auto-Tagging Rules</h2>
                <p className="text-sm text-slate-500">Define runtime classification rules that apply tags automatically.</p>
              </div>
              {editingRuleId && (
                <button onClick={resetRuleForm} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {canWrite && (
              <form onSubmit={handleSaveRule} className="grid gap-3">
                <input value={ruleName} onChange={(e) => setRuleName(e.target.value)} className={inputCls} placeholder="Rule name" required />
                <textarea value={ruleDescription} onChange={(e) => setRuleDescription(e.target.value)} className={`${inputCls} min-h-[80px]`} placeholder="Description (optional)" />
                <div className="grid gap-3 md:grid-cols-2">
                  <select value={matchType} onChange={(e) => setMatchType(e.target.value as (typeof MATCH_TYPES)[number])} className={inputCls}>
                    {MATCH_TYPES.map((item) => (
                      <option key={item} value={item}>{item}</option>
                    ))}
                  </select>
                  <input value={matchField} onChange={(e) => setMatchField(e.target.value)} className={inputCls} placeholder="Match field" required />
                  <input value={matchPattern} onChange={(e) => setMatchPattern(e.target.value)} className={inputCls} placeholder="Match pattern" required />
                  <input value={rulePriority} onChange={(e) => setRulePriority(e.target.value)} className={inputCls} placeholder="Priority" />
                  <input value={ruleTagKey} onChange={(e) => setRuleTagKey(e.target.value)} className={inputCls} placeholder="Tag key" required />
                  <input value={ruleTagValue} onChange={(e) => setRuleTagValue(e.target.value)} className={inputCls} placeholder="Tag value" required />
                </div>
                <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <input type="checkbox" checked={ruleIsActive} onChange={(e) => setRuleIsActive(e.target.checked)} />
                  Active
                </label>
                <div>
                  <button type="submit" className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">
                    <Plus className="h-4 w-4" />
                    {editingRuleId ? 'Save Rule' : 'Create Rule'}
                  </button>
                </div>
              </form>
            )}

            <div className="mt-5 space-y-3">
              {rules.length === 0 ? (
                <p className="text-sm text-slate-400">No auto-tagging rules configured.</p>
              ) : (
                rules.map((rule) => (
                  <div key={rule.id} className="rounded-2xl border border-slate-200 bg-white/90 p-4 dark:border-slate-700 dark:bg-slate-900/80">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="font-semibold text-slate-900 dark:text-slate-50">{rule.name}</p>
                        <p className="mt-1 text-sm text-slate-500">
                          {rule.match_field} {rule.match_type} <span className="font-mono">{rule.match_pattern}</span>
                        </p>
                        <p className="mt-2 text-xs text-slate-500">
                          Applies <span className="font-mono">{rule.tag_key}={rule.tag_value}</span> · P{rule.priority} · {rule.is_active ? 'active' : 'inactive'}
                        </p>
                      </div>
                      {canWrite && (
                        <div className="flex gap-2">
                          <button onClick={() => startEditRule(rule)} className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button onClick={() => void handleDeleteRule(rule)} className="rounded-lg border border-red-200 p-2 text-red-600 hover:bg-red-50 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/30">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <div className="mb-4 flex items-center gap-2">
              <Wand2 className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Simulation</h2>
            </div>
            <textarea value={simulationFields} onChange={(e) => setSimulationFields(e.target.value)} className={`${inputCls} min-h-[170px] w-full font-mono text-xs`} />
            <button onClick={() => void handleRunSimulation()} className="mt-3 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
              Re-run simulation
            </button>
            {simulation && (
              <div className="mt-4 space-y-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Matched Rules</p>
                  <div className="mt-2 space-y-2">
                    {simulation.matched.length === 0 ? (
                      <p className="text-sm text-slate-400">No rules matched this payload.</p>
                    ) : (
                      simulation.matched.map((item) => (
                        <div key={item.rule_id} className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700">
                          <p className="font-medium text-slate-900 dark:text-slate-100">{item.rule_name}</p>
                          <p className="mt-1 text-xs text-slate-500">
                            {item.tag_key}={item.tag_value} · P{item.priority}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Applied Tags</p>
                  <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                    {JSON.stringify(simulation.applied_tags, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
