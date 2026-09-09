'use client'

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import Link from 'next/link'
import { BookOpen, ChevronRight, DollarSign, Pencil, Plus, Tags, Trash2, Wand2, X, Zap } from 'lucide-react'
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
  getTagsRuntimePosture,
} from '@/lib/api'
import type { AutoTaggingRuleResponse, AutoTaggingSimulationResponse, TagResponse, TagTreeNode, TagsFinopsBudgetPosture, DataProtectionOrgPosture, DataProtectionGatewayPosture, GovernanceInternalPosture, TagsRuntimePosture } from '@/types/api'

const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500'

const MATCH_TYPES = ['equals', 'contains', 'regex', 'prefix', 'suffix'] as const

type Tab = 'catalog' | 'rules' | 'simulation' | 'hierarchy'

function TagNode({ node, depth = 0 }: { node: TagTreeNode; depth?: number }) {
  return (
    <div className="space-y-1.5">
      <div
        className="rounded-lg border border-slate-200 bg-white p-2.5 dark:border-slate-700 dark:bg-slate-900/70"
        style={{ marginLeft: depth * 16 }}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="text-xs font-semibold text-slate-900 dark:text-slate-50">
              {node.key}: <span className="text-amber-600 dark:text-amber-400">{node.value}</span>
            </p>
            <p className="text-[10px] text-slate-500">{node.category}</p>
          </div>
          <span className={`shrink-0 rounded-full px-2 py-0.5 text-[9px] font-bold uppercase ${node.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>
            {node.is_active ? 'active' : 'inactive'}
          </span>
        </div>
        {node.description && <p className="mt-1 text-[10px] text-slate-500">{node.description}</p>}
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

  const [tab, setTab] = useState<Tab>('catalog')
  const [tags, setTags] = useState<TagResponse[]>([])
  const [tree, setTree] = useState<TagTreeNode[]>([])
  const [rules, setRules] = useState<AutoTaggingRuleResponse[]>([])
  const [simulation, setSimulation] = useState<AutoTaggingSimulationResponse | null>(null)
  const [finopsPosture, setFinopsPosture] = useState<TagsFinopsBudgetPosture | null>(null)
  const [orgPosture, setOrgPosture] = useState<DataProtectionOrgPosture | null>(null)
  const [gatewayPosture, setGatewayPosture] = useState<DataProtectionGatewayPosture | null>(null)
  const [govInternal, setGovInternal] = useState<GovernanceInternalPosture | null>(null)
  const [runtimePosture, setRuntimePosture] = useState<TagsRuntimePosture | null>(null)
  const [loading, setLoading] = useState(false)

  const [editingTagId, setEditingTagId] = useState<string | null>(null)
  const [tagCategory, setTagCategory] = useState('workflow')
  const [tagKey, setTagKey] = useState('')
  const [tagValue, setTagValue] = useState('')
  const [tagDescription, setTagDescription] = useState('')
  const [parentTagId, setParentTagId] = useState('')
  const [tagIsActive, setTagIsActive] = useState(true)
  const [showTagForm, setShowTagForm] = useState(false)

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
  const [showRuleForm, setShowRuleForm] = useState(false)

  const [simulationFields, setSimulationFields] = useState(
    JSON.stringify({ feature: 'support-search', prompt: 'search the docs for billing exports', provider: 'openai' }, null, 2),
  )

  const resetTagForm = useCallback(() => {
    setEditingTagId(null)
    setTagCategory('workflow')
    setTagKey('')
    setTagValue('')
    setTagDescription('')
    setParentTagId('')
    setTagIsActive(true)
    setShowTagForm(false)
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
    setShowRuleForm(false)
  }, [])

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const [tagList, tagTree, autoRules, simulationResult, posture, orgP, gwP, govI, rtP] = await Promise.all([
        getTags(apiKey, { include_inactive: true }),
        getTagTree(apiKey),
        getAutoTagRules(apiKey),
        simulateAutoTagging(apiKey, { fields: { feature: 'support-search', prompt: 'search the docs for billing exports', provider: 'openai' } }),
        getTagsFinopsBudgetPosture(apiKey).catch(() => null),
        getDataProtectionOrgPosture(apiKey).catch(() => null),
        getDataProtectionGatewayPosture(apiKey).catch(() => null),
        getGovernanceInternalPosture(apiKey).catch(() => null),
        getTagsRuntimePosture(apiKey).catch(() => null),
      ])
      setTags(tagList.items)
      setTree(tagTree.items)
      setRules(autoRules.items)
      setSimulation(simulationResult)
      setFinopsPosture(posture)
      setOrgPosture(orgP)
      setGatewayPosture(gwP)
      setGovInternal(govI)
      setRuntimePosture(rtP)
    } catch {
      toast.error('Failed to load tag management')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { void load() }, [load])

  async function handleSaveTag(e: React.FormEvent) {
    e.preventDefault()
    if (!apiKey) return
    try {
      if (editingTagId) {
        await updateTag(apiKey, editingTagId, { category: tagCategory, key: tagKey, value: tagValue, description: tagDescription.trim() || null, parent_tag_id: parentTagId || null, is_active: tagIsActive })
        toast.success('Tag updated')
      } else {
        await createTag(apiKey, { category: tagCategory, key: tagKey, value: tagValue, description: tagDescription.trim() || null, parent_tag_id: parentTagId || null, is_active: tagIsActive })
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
    setShowTagForm(true)
    setTab('catalog')
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
        await updateAutoTagRule(apiKey, editingRuleId, { name: ruleName, description: ruleDescription.trim() || null, match_type: matchType, match_field: matchField, match_pattern: matchPattern, tag_key: ruleTagKey, tag_value: ruleTagValue, priority: parseInt(rulePriority, 10) || 100, is_active: ruleIsActive })
        toast.success('Auto-tagging rule updated')
      } else {
        await createAutoTagRule(apiKey, { name: ruleName, description: ruleDescription.trim() || null, match_type: matchType, match_field: matchField, match_pattern: matchPattern, tag_key: ruleTagKey, tag_value: ruleTagValue, priority: parseInt(rulePriority, 10) || 100, is_active: ruleIsActive })
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
    setShowRuleForm(true)
    setTab('rules')
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
    return <p className="p-8 text-xs text-slate-500">Sign in to view tag management.</p>
  }

  const activeTags = tags.filter((t) => t.is_active).length
  const activeRules = rules.filter((r) => r.is_active).length

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4">
      {/* Hero header */}
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 ring-1 ring-amber-200 dark:bg-amber-500/20 dark:ring-amber-400/30">
              <BookOpen className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-950 dark:text-white">Tag Management</h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">Hierarchical tags, auto-tagging rules &amp; classification simulation</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">{tags.length} tags</span>
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">{rules.length} rules</span>
          </div>
        </div>

        {/* KPI strip */}
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
          <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
            <p className="text-lg font-bold text-slate-900 dark:text-white">{activeTags}</p>
            <p className="text-[10px] text-slate-500 dark:text-slate-400">Active Tags</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
            <p className="text-lg font-bold text-slate-900 dark:text-white">{activeRules}</p>
            <p className="text-[10px] text-slate-500 dark:text-slate-400">Active Rules</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
            <p className="text-lg font-bold text-slate-900 dark:text-white">{simulation?.matched.length ?? 0}</p>
            <p className="text-[10px] text-slate-500 dark:text-slate-400">Sim Matches</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
            <p className="text-lg font-bold text-slate-900 dark:text-white">{tree.length}</p>
            <p className="text-[10px] text-slate-500 dark:text-slate-400">Root Nodes</p>
          </div>
          {finopsPosture && (
            <>
              <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-lg font-bold text-slate-900 dark:text-white">${finopsPosture.spend_context.tagged_spend_30d?.toFixed(0) ?? '0'}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">Tagged Spend 30d</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-lg font-bold text-slate-900 dark:text-white">{finopsPosture.budget_context.tag_scoped_budgets ?? 0}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">Tag Budgets</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-lg font-bold text-slate-900 dark:text-white">{finopsPosture.chargeback_context.tag_dimension_rules ?? 0}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">Chargeback Rules</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-lg font-bold text-slate-900 dark:text-white">{finopsPosture.tag_context.distinct_tags_with_spend ?? 0}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">Tags w/ Spend</p>
              </div>
            </>
          )}
        </div>

        {/* Posture chips */}
        <div className="mt-3 flex flex-wrap gap-1.5">
          {govInternal && (
            <>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                <span className="font-semibold text-slate-900 dark:text-white">{govInternal.tool_registry_context.total_tools}</span> tools
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                <span className="font-semibold text-slate-900 dark:text-white">{govInternal.tool_policies_context.active_policies}</span> policies
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                <span className="font-semibold text-slate-900 dark:text-white">{govInternal.audit_context.audit_events_30d}</span> audit 30d
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                <span className="font-semibold text-slate-900 dark:text-white">{govInternal.alert_rules_context.alert_firings_30d}</span> alerts 30d
              </span>
            </>
          )}
          {runtimePosture && (
            <>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                <span className="font-semibold text-slate-900 dark:text-white">{runtimePosture.observe_attribution.runs_30d}</span> runs 30d
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                <span className="font-semibold text-slate-900 dark:text-white">{runtimePosture.finops_attribution.chargeback_rules}</span> chargeback
              </span>
            </>
          )}
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-lg bg-slate-100 p-1 dark:bg-slate-800/80">
        {[
          { key: 'catalog' as Tab, label: 'Tag Catalog', icon: Tags },
          { key: 'rules' as Tab, label: 'Auto-Tagging Rules', icon: Zap },
          { key: 'simulation' as Tab, label: 'Simulation', icon: Wand2 },
          { key: 'hierarchy' as Tab, label: 'Hierarchy', icon: ChevronRight },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === key
                ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Tag Catalog tab */}
      {tab === 'catalog' && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Tags className="h-4 w-4 text-amber-500" />
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Tag Catalog</p>
              </div>
              <p className="mt-1 text-[11px] text-slate-500">Create, edit, or retire the metadata vocabulary.</p>
            </div>
            {canWrite && (
              <button
                onClick={() => showTagForm ? resetTagForm() : setShowTagForm(true)}
                className="flex items-center gap-1 rounded-lg bg-gradient-to-r from-amber-600 to-orange-600 px-3 py-1.5 text-xs font-semibold text-white hover:from-amber-500 hover:to-orange-500"
              >
                {showTagForm ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
                {showTagForm ? 'Cancel' : editingTagId ? 'Editing...' : 'Add Tag'}
              </button>
            )}
          </div>

          {showTagForm && canWrite && (
            <form onSubmit={handleSaveTag} className="mb-4 grid gap-2 rounded-lg border border-amber-200 bg-amber-50/40 p-3 dark:border-amber-800 dark:bg-amber-950/20 md:grid-cols-2">
              <label className="text-xs">
                <span className="mb-1 block text-[10px] font-medium text-slate-500">Category</span>
                <input value={tagCategory} onChange={(e) => setTagCategory(e.target.value)} className={inputCls} placeholder="workflow" required />
              </label>
              <label className="text-xs">
                <span className="mb-1 block text-[10px] font-medium text-slate-500">Key</span>
                <input value={tagKey} onChange={(e) => setTagKey(e.target.value)} className={inputCls} placeholder="environment" required />
              </label>
              <label className="text-xs">
                <span className="mb-1 block text-[10px] font-medium text-slate-500">Value</span>
                <input value={tagValue} onChange={(e) => setTagValue(e.target.value)} className={inputCls} placeholder="production" required />
              </label>
              <label className="text-xs">
                <span className="mb-1 block text-[10px] font-medium text-slate-500">Parent Tag</span>
                <select value={parentTagId} onChange={(e) => setParentTagId(e.target.value)} className={inputCls}>
                  <option value="">No parent</option>
                  {tags.filter((t) => t.id !== editingTagId).map((t) => (
                    <option key={t.id} value={t.id}>{t.category}/{t.key}={t.value}</option>
                  ))}
                </select>
              </label>
              <label className="text-xs md:col-span-2">
                <span className="mb-1 block text-[10px] font-medium text-slate-500">Description</span>
                <textarea value={tagDescription} onChange={(e) => setTagDescription(e.target.value)} className={`${inputCls} min-h-[60px] resize-none`} placeholder="Optional description" />
              </label>
              <div className="flex items-center gap-3 md:col-span-2">
                <label className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                  <input type="checkbox" checked={tagIsActive} onChange={(e) => setTagIsActive(e.target.checked)} className="rounded" /> Active
                </label>
                <button type="submit" className="rounded-lg bg-gradient-to-r from-amber-600 to-orange-600 px-4 py-1.5 text-xs font-semibold text-white hover:from-amber-500 hover:to-orange-500">
                  {editingTagId ? 'Save Tag' : 'Create Tag'}
                </button>
              </div>
            </form>
          )}

          {loading ? (
            <p className="text-xs text-slate-400">Loading tags...</p>
          ) : tags.length === 0 ? (
            <p className="text-xs text-slate-400">No tags created yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th className="px-3 py-2 font-medium text-slate-500">Tag</th>
                    <th className="px-3 py-2 font-medium text-slate-500">Category</th>
                    <th className="px-3 py-2 font-medium text-slate-500">Status</th>
                    <th className="px-3 py-2 font-medium text-slate-500">Description</th>
                    {canWrite && <th className="px-3 py-2" />}
                  </tr>
                </thead>
                <tbody>
                  {tags.map((tag) => (
                    <tr key={tag.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-amber-50/30 dark:hover:bg-amber-950/10">
                      <td className="px-3 py-2">
                        <span className="font-mono text-[11px] font-semibold text-slate-900 dark:text-white">{tag.key}</span>
                        <span className="font-mono text-[11px] text-slate-500">=</span>
                        <span className="font-mono text-[11px] text-amber-600 dark:text-amber-400">{tag.value}</span>
                      </td>
                      <td className="px-3 py-2 text-[11px] text-slate-500">{tag.category}</td>
                      <td className="px-3 py-2">
                        <span className={`rounded-full px-2 py-0.5 text-[9px] font-bold uppercase ${tag.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>
                          {tag.is_active ? 'active' : 'inactive'}
                        </span>
                      </td>
                      <td className="px-3 py-2 max-w-xs truncate text-[10px] text-slate-500">{tag.description || '—'}</td>
                      {canWrite && (
                        <td className="px-3 py-2 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button onClick={() => startEditTag(tag)} className="rounded-md border border-slate-200 p-1.5 text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">
                              <Pencil className="h-3 w-3" />
                            </button>
                            <button onClick={() => void handleDeleteTag(tag)} className="rounded-md border border-red-200 p-1.5 text-red-500 hover:bg-red-50 dark:border-red-900/40 dark:hover:bg-red-950/30">
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Auto-Tagging Rules tab */}
      {tab === 'rules' && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-500" />
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Auto-Tagging Rules</p>
              </div>
              <p className="mt-1 text-[11px] text-slate-500">Runtime classification rules that apply tags automatically.</p>
            </div>
            {canWrite && (
              <button
                onClick={() => showRuleForm ? resetRuleForm() : setShowRuleForm(true)}
                className="flex items-center gap-1 rounded-lg bg-gradient-to-r from-amber-600 to-orange-600 px-3 py-1.5 text-xs font-semibold text-white hover:from-amber-500 hover:to-orange-500"
              >
                {showRuleForm ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
                {showRuleForm ? 'Cancel' : 'Add Rule'}
              </button>
            )}
          </div>

          {showRuleForm && canWrite && (
            <form onSubmit={handleSaveRule} className="mb-4 rounded-lg border border-amber-200 bg-amber-50/40 p-3 dark:border-amber-800 dark:bg-amber-950/20">
              <div className="grid gap-2 md:grid-cols-2">
                <label className="text-xs">
                  <span className="mb-1 block text-[10px] font-medium text-slate-500">Rule Name</span>
                  <input value={ruleName} onChange={(e) => setRuleName(e.target.value)} className={inputCls} placeholder="billing-classifier" required />
                </label>
                <label className="text-xs">
                  <span className="mb-1 block text-[10px] font-medium text-slate-500">Match Type</span>
                  <select value={matchType} onChange={(e) => setMatchType(e.target.value as (typeof MATCH_TYPES)[number])} className={inputCls}>
                    {MATCH_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </label>
                <label className="text-xs">
                  <span className="mb-1 block text-[10px] font-medium text-slate-500">Match Field</span>
                  <input value={matchField} onChange={(e) => setMatchField(e.target.value)} className={inputCls} placeholder="prompt" required />
                </label>
                <label className="text-xs">
                  <span className="mb-1 block text-[10px] font-medium text-slate-500">Match Pattern</span>
                  <input value={matchPattern} onChange={(e) => setMatchPattern(e.target.value)} className={inputCls} placeholder="billing" required />
                </label>
                <label className="text-xs">
                  <span className="mb-1 block text-[10px] font-medium text-slate-500">Tag Key</span>
                  <input value={ruleTagKey} onChange={(e) => setRuleTagKey(e.target.value)} className={inputCls} placeholder="domain" required />
                </label>
                <label className="text-xs">
                  <span className="mb-1 block text-[10px] font-medium text-slate-500">Tag Value</span>
                  <input value={ruleTagValue} onChange={(e) => setRuleTagValue(e.target.value)} className={inputCls} placeholder="billing" required />
                </label>
                <label className="text-xs">
                  <span className="mb-1 block text-[10px] font-medium text-slate-500">Priority</span>
                  <input value={rulePriority} onChange={(e) => setRulePriority(e.target.value)} className={inputCls} placeholder="100" />
                </label>
                <label className="text-xs md:col-span-2">
                  <span className="mb-1 block text-[10px] font-medium text-slate-500">Description</span>
                  <textarea value={ruleDescription} onChange={(e) => setRuleDescription(e.target.value)} className={`${inputCls} min-h-[50px] resize-none`} placeholder="Optional" />
                </label>
              </div>
              <div className="mt-2 flex items-center gap-3">
                <label className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                  <input type="checkbox" checked={ruleIsActive} onChange={(e) => setRuleIsActive(e.target.checked)} className="rounded" /> Active
                </label>
                <button type="submit" className="rounded-lg bg-gradient-to-r from-amber-600 to-orange-600 px-4 py-1.5 text-xs font-semibold text-white hover:from-amber-500 hover:to-orange-500">
                  {editingRuleId ? 'Save Rule' : 'Create Rule'}
                </button>
              </div>
            </form>
          )}

          {rules.length === 0 ? (
            <p className="text-xs text-slate-400">No auto-tagging rules configured.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th className="px-3 py-2 font-medium text-slate-500">Rule</th>
                    <th className="px-3 py-2 font-medium text-slate-500">Match</th>
                    <th className="px-3 py-2 font-medium text-slate-500">Applies</th>
                    <th className="px-3 py-2 font-medium text-slate-500">Priority</th>
                    <th className="px-3 py-2 font-medium text-slate-500">Status</th>
                    {canWrite && <th className="px-3 py-2" />}
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr key={rule.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-amber-50/30 dark:hover:bg-amber-950/10">
                      <td className="px-3 py-2">
                        <p className="font-semibold text-slate-900 dark:text-white">{rule.name}</p>
                        {rule.description && <p className="text-[10px] text-slate-500 truncate max-w-[180px]">{rule.description}</p>}
                      </td>
                      <td className="px-3 py-2 font-mono text-[10px] text-slate-600 dark:text-slate-400">
                        {rule.match_field} <span className="text-amber-600 dark:text-amber-400">{rule.match_type}</span> {rule.match_pattern}
                      </td>
                      <td className="px-3 py-2 font-mono text-[10px]">
                        <span className="text-slate-700 dark:text-slate-300">{rule.tag_key}</span>=<span className="text-amber-600 dark:text-amber-400">{rule.tag_value}</span>
                      </td>
                      <td className="px-3 py-2 text-[11px] text-slate-500">P{rule.priority}</td>
                      <td className="px-3 py-2">
                        <span className={`rounded-full px-2 py-0.5 text-[9px] font-bold uppercase ${rule.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>
                          {rule.is_active ? 'active' : 'off'}
                        </span>
                      </td>
                      {canWrite && (
                        <td className="px-3 py-2 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button onClick={() => startEditRule(rule)} className="rounded-md border border-slate-200 p-1.5 text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">
                              <Pencil className="h-3 w-3" />
                            </button>
                            <button onClick={() => void handleDeleteRule(rule)} className="rounded-md border border-red-200 p-1.5 text-red-500 hover:bg-red-50 dark:border-red-900/40 dark:hover:bg-red-950/30">
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Simulation tab */}
      {tab === 'simulation' && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="flex items-center gap-2 mb-3">
            <Wand2 className="h-4 w-4 text-amber-500" />
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Auto-Tag Simulation</p>
          </div>
          <p className="mb-2 text-[11px] text-slate-500">Enter JSON fields to test which rules match and what tags would be applied.</p>
          <textarea value={simulationFields} onChange={(e) => setSimulationFields(e.target.value)} className={`${inputCls} min-h-[120px] font-mono resize-none`} />
          <button onClick={() => void handleRunSimulation()} className="mt-2 rounded-lg bg-gradient-to-r from-amber-600 to-orange-600 px-4 py-1.5 text-xs font-semibold text-white hover:from-amber-500 hover:to-orange-500">
            Run Simulation
          </button>

          {simulation && (
            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">Matched Rules ({simulation.matched.length})</p>
                {simulation.matched.length === 0 ? (
                  <p className="text-xs text-slate-400">No rules matched this payload.</p>
                ) : (
                  <div className="space-y-1.5">
                    {simulation.matched.map((item) => (
                      <div key={item.rule_id} className="rounded-md bg-amber-50 px-2.5 py-2 dark:bg-amber-950/20">
                        <p className="text-xs font-semibold text-slate-900 dark:text-white">{item.rule_name}</p>
                        <p className="mt-0.5 font-mono text-[10px] text-slate-500">
                          {item.tag_key}=<span className="text-amber-600 dark:text-amber-400">{item.tag_value}</span> &middot; P{item.priority}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">Applied Tags</p>
                <pre className="overflow-x-auto rounded-md bg-slate-50 p-2.5 text-[10px] text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                  {JSON.stringify(simulation.applied_tags, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Hierarchy tab */}
      {tab === 'hierarchy' && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="flex items-center gap-2 mb-3">
            <ChevronRight className="h-4 w-4 text-amber-500" />
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Tag Hierarchy</p>
          </div>
          {tree.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 px-6 py-8 text-center text-xs text-slate-400 dark:border-slate-700">
              No active tags with hierarchy. Create tags with parent relationships to build the tree.
            </div>
          ) : (
            <div className="space-y-2">
              {tree.map((node) => <TagNode key={node.id} node={node} />)}
            </div>
          )}
        </div>
      )}

      {/* Quick nav footer */}
      <div className="flex flex-wrap gap-1.5 pt-2">
        {[
          { href: '/tool-registry', label: 'Tool Governance' },
          { href: '/data-capture', label: 'Data Capture' },
          { href: '/approvals', label: 'Approvals' },
          { href: '/audit', label: 'Audit Log' },
          { href: '/security', label: 'Security' },
          { href: '/alert-rules', label: 'Alert Rules' },
          { href: '/budgets', label: 'Budgets' },
          { href: '/chargeback', label: 'Chargeback' },
        ].map((l) => (
          <Link key={l.href} href={l.href} className="rounded-full bg-amber-50 px-2.5 py-1 text-[10px] font-medium text-amber-700 ring-1 ring-amber-200 hover:bg-amber-100 dark:bg-amber-950/30 dark:text-amber-400 dark:ring-amber-800 dark:hover:bg-amber-950/50">
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  )
}
