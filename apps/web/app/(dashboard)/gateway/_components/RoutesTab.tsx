'use client'

import { Network, Plus, Trash2, Pencil, ChevronUp } from 'lucide-react'
import type { GatewayRoutingGroupStrategy } from '@/types/api'
import { inputCls } from './shared'
import { useSearchParams, usePathname, useRouter } from 'next/navigation'
import { RouteTestPanel } from './RouteTestPanel'
import { useGateway } from './useGatewayState'

export function RoutesTab() {
  const {
    canManage,
    gatewayRoutes,
    newRouteAlias,
    setNewRouteAlias,
    newRouteProvider,
    setNewRouteProvider,
    newRouteTargetModel,
    setNewRouteTargetModel,
    newRouteBaseUrl,
    setNewRouteBaseUrl,
    newRouteApiKeyEnvVar,
    setNewRouteApiKeyEnvVar,
    newRoutePriority,
    setNewRoutePriority,
    newRouteRoutingGroupId,
    setNewRouteRoutingGroupId,
    newRouteRequiredTags,
    setNewRouteRequiredTags,
    newRouteExcludedTags,
    setNewRouteExcludedTags,
    newRouteRegion,
    setNewRouteRegion,
    newRouteConfigStr,
    setNewRouteConfigStr,
    newRouteConfigError,
    setNewRouteConfigError,
    newRouteDailyCap,
    setNewRouteDailyCap,
    newRouteMonthlyCap,
    setNewRouteMonthlyCap,
    newRoutePiiRedaction,
    setNewRoutePiiRedaction,
    newRouteSemanticCache,
    setNewRouteSemanticCache,
    newRouteContextCompiler,
    setNewRouteContextCompiler,
    newRouteCompilerModel,
    setNewRouteCompilerModel,
    newRouteRerankerModel,
    setNewRouteRerankerModel,
    newRouteCompilerThreshold,
    setNewRouteCompilerThreshold,
    newRouteCompress,
    setNewRouteCompress,
    newRouteCompressModel,
    setNewRouteCompressModel,
    newRouteCompressRate,
    setNewRouteCompressRate,
    newRouteCompressWhen,
    setNewRouteCompressWhen,
    newRouteCompressPct,
    setNewRouteCompressPct,
    newRouteToolFilter,
    setNewRouteToolFilter,
    newRouteToolK,
    setNewRouteToolK,
    newRouteSkills,
    setNewRouteSkills,
    newRouteSkillK,
    setNewRouteSkillK,
    newRouteIntelligent,
    setNewRouteIntelligent,
    newRouteRoutingConfigStr,
    setNewRouteRoutingConfigStr,
    newRouteRoutingError,
    setNewRouteRoutingError,
    newRoutePerUserRpm,
    setNewRoutePerUserRpm,
    newRouteFallbackAliases,
    setNewRouteFallbackAliases,
    newRouteContextFallback,
    setNewRouteContextFallback,
    newRoutePolicyFallback,
    setNewRoutePolicyFallback,
    newRouteMirrorAlias,
    setNewRouteMirrorAlias,
    newRouteMirrorPct,
    setNewRouteMirrorPct,
    creatingRoute,
    showRouteForm,
    setShowRouteForm,
    routeEditState,
    setRouteEditState,
    savingRouteEdit,
    routeEditError,
    setRouteEditError,
    routingGroups,
    strategyComparison,
    showGroupForm,
    setShowGroupForm,
    creatingGroup,
    newGroupAlias,
    setNewGroupAlias,
    newGroupName,
    setNewGroupName,
    newGroupDescription,
    setNewGroupDescription,
    newGroupMatchTags,
    setNewGroupMatchTags,
    newGroupDefaultTags,
    setNewGroupDefaultTags,
    newGroupStrategyType,
    setNewGroupStrategyType,
    newGroupStrategyConfig,
    setNewGroupStrategyConfig,
    newGroupStrategyError,
    setNewGroupStrategyError,
    groupEditState,
    setGroupEditState,
    savingGroupEdit,
    groupEditError,
    setGroupEditError,
    pricing,
    getRouteFallbackAliases,
    fallbackRules,
    getMirror,
    beginRouteEdit,
    handleSaveRouteEdit,
    beginGroupEdit,
    handleSaveGroupEdit,
    getDeploymentStatusTone,
    handleCreateRoute,
    handleToggleRoute,
    handleToggleSemanticCache,
    handleToggleContextCompiler,
    handleToggleIntelligentRouting,
    handleDeleteRoute,
    handleCreateRoutingGroup,
    handleToggleRoutingGroup,
    handleDeleteRoutingGroup,
  } = useGateway()
  // Route search lives in the URL (?routeq=) so a filtered view can be shared.
  const params = useSearchParams()
  const pathname = usePathname()
  const router = useRouter()
  const routeQuery = params.get('routeq') ?? ''
  const setRouteQuery = (value: string) => {
    const next = new URLSearchParams(params.toString())
    if (value) next.set('routeq', value)
    else next.delete('routeq')
    router.replace(`${pathname}?${next.toString()}`, { scroll: false })
  }
  const needle = routeQuery.trim().toLowerCase()
  const visibleRoutes = needle
    ? gatewayRoutes.filter((r) =>
        [r.alias, r.provider, r.target_model, r.region ?? '', r.routing_group_name ?? ''].some((v) => v.toLowerCase().includes(needle)),
      )
    : gatewayRoutes
  return (
  <div className="space-y-3">
  <RouteTestPanel />

  <section className="space-y-4">
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-base font-semibold dark:text-white">Routing Groups</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
          Independent group state for tagged traffic, default tags for untagged requests, and per-group routing strategy.
        </p>
      </div>
      <button
        onClick={() => setShowGroupForm((value) => !value)}
        className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
      >
        {showGroupForm ? <ChevronUp className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
        {showGroupForm ? 'Cancel' : 'Add Group'}
      </button>
    </div>

    {showGroupForm && (
      <form onSubmit={handleCreateRoutingGroup} className="grid gap-3 rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-900/10 p-4 sm:grid-cols-2 lg:grid-cols-3">
        <input value={newGroupAlias} onChange={(e) => setNewGroupAlias(e.target.value)} className={inputCls} placeholder="Alias (e.g. gpt-4o)" required />
        <input value={newGroupName} onChange={(e) => setNewGroupName(e.target.value)} className={inputCls} placeholder="Group name" required />
        <select value={newGroupStrategyType} onChange={(e) => setNewGroupStrategyType(e.target.value as GatewayRoutingGroupStrategy)} className={inputCls}>
          <option value="manual">manual</option>
          <option value="latency_optimized">latency_optimized</option>
          <option value="round_robin">round_robin</option>
        </select>
        <input value={newGroupMatchTags} onChange={(e) => setNewGroupMatchTags(e.target.value)} className={inputCls} placeholder="Match tags (csv)" />
        <input value={newGroupDefaultTags} onChange={(e) => setNewGroupDefaultTags(e.target.value)} className={inputCls} placeholder="Default tags (csv)" />
        <input value={newGroupDescription} onChange={(e) => setNewGroupDescription(e.target.value)} className={inputCls} placeholder="Description" />
        <textarea value={newGroupStrategyConfig} onChange={(e) => { setNewGroupStrategyConfig(e.target.value); setNewGroupStrategyError('') }} className={`${inputCls} min-h-[96px] font-mono text-xs sm:col-span-2 lg:col-span-3`} placeholder='{"notes":"optional"}' />
        {newGroupStrategyError && <p className="text-xs text-red-500 sm:col-span-2 lg:col-span-3">{newGroupStrategyError}</p>}
        <div className="sm:col-span-2 lg:col-span-3">
          <button type="submit" disabled={creatingGroup} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
            {creatingGroup ? 'Creating…' : 'Create routing group'}
          </button>
        </div>
      </form>
    )}

    <div className="grid gap-3 lg:grid-cols-2">
      {routingGroups.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400 lg:col-span-2">
          No routing groups configured yet.
        </div>
      ) : routingGroups.map((group) => (
        <div key={group.id} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm dark:text-slate-100">{group.alias}</span>
                <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">{group.name}</span>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">{group.strategy_type}</span>
                <button onClick={() => void handleToggleRoutingGroup(group)} className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${group.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'}`}>
                  {group.is_active ? 'active' : 'inactive'}
                </button>
              </div>
              {group.description && <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{group.description}</p>}
              <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                <span className="rounded-full bg-sky-100 px-2 py-0.5 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300">match: {group.match_tags.length ? group.match_tags.join(', ') : 'none'}</span>
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">default: {group.default_tags.length ? group.default_tags.join(', ') : 'none'}</span>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600 dark:bg-slate-700 dark:text-slate-300">routes: {group.route_count}</span>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button aria-label="Edit" onClick={() => beginGroupEdit(group)} className="rounded-lg p-1.5 text-slate-400 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors">
                <Pencil className="h-3.5 w-3.5" />
              </button>
              <button aria-label="Delete" onClick={() => void handleDeleteRoutingGroup(group.id)} className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
          {groupEditState?.id === group.id && (
            <div className="mt-4 grid gap-3 rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/40 dark:bg-indigo-900/10 p-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <p className="text-sm font-semibold text-indigo-800 dark:text-indigo-300">Edit routing group</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Update the alias mapping, tag defaults, and strategy config without leaving the gateway page.</p>
              </div>
              <input value={groupEditState.alias} onChange={(e) => setGroupEditState({ ...groupEditState, alias: e.target.value })} className={inputCls} placeholder="Alias" />
              <input value={groupEditState.name} onChange={(e) => setGroupEditState({ ...groupEditState, name: e.target.value })} className={inputCls} placeholder="Group name" />
              <input value={groupEditState.matchTags} onChange={(e) => setGroupEditState({ ...groupEditState, matchTags: e.target.value })} className={inputCls} placeholder="Match tags (csv)" />
              <input value={groupEditState.defaultTags} onChange={(e) => setGroupEditState({ ...groupEditState, defaultTags: e.target.value })} className={inputCls} placeholder="Default tags (csv)" />
              <input value={groupEditState.description} onChange={(e) => setGroupEditState({ ...groupEditState, description: e.target.value })} className={`${inputCls} sm:col-span-2`} placeholder="Description" />
              <select value={groupEditState.strategyType} onChange={(e) => setGroupEditState({ ...groupEditState, strategyType: e.target.value as GatewayRoutingGroupStrategy })} className={inputCls}>
                <option value="manual">manual</option>
                <option value="latency_optimized">latency_optimized</option>
                <option value="round_robin">round_robin</option>
              </select>
              <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                <input type="checkbox" checked={groupEditState.isActive} onChange={(e) => setGroupEditState({ ...groupEditState, isActive: e.target.checked })} className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                Group active
              </label>
              <textarea value={groupEditState.strategyConfigStr} onChange={(e) => { setGroupEditState({ ...groupEditState, strategyConfigStr: e.target.value }); setGroupEditError('') }} className={`${inputCls} min-h-[96px] font-mono text-xs sm:col-span-2`} placeholder='{"notes":"optional"}' />
              {groupEditError && <p className="text-xs text-red-500 sm:col-span-2">{groupEditError}</p>}
              <div className="sm:col-span-2 flex items-center gap-2">
                <button onClick={() => void handleSaveGroupEdit()} disabled={savingGroupEdit} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                  {savingGroupEdit ? 'Saving...' : 'Save changes'}
                </button>
                <button onClick={() => setGroupEditState(null)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  </section>

  <section className="space-y-4">
    <div>
      <h2 className="text-base font-semibold dark:text-white">Routing Strategy Comparison</h2>
      <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
        Compare routing groups by throughput, cache performance, latency, and errors.
      </p>
    </div>
    {strategyComparison.length === 0 ? (
      <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400">
        Comparison data will appear after requests hit grouped routes.
      </div>
    ) : (
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {strategyComparison.map((item) => (
          <div key={`${item.alias}-${item.group_name}`} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="font-mono text-sm dark:text-slate-100">{item.alias}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{item.group_name}</p>
              </div>
              <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[11px] font-semibold text-violet-700 dark:bg-violet-900/30 dark:text-violet-300">{item.strategy_type}</span>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg bg-white px-3 py-2 dark:bg-slate-900/40">
                <p className="text-slate-400">Requests</p>
                <p className="font-semibold dark:text-white">{item.total_requests.toLocaleString()}</p>
              </div>
              <div className="rounded-lg bg-white px-3 py-2 dark:bg-slate-900/40">
                <p className="text-slate-400">Active routes</p>
                <p className="font-semibold dark:text-white">{item.active_routes}</p>
              </div>
              <div className="rounded-lg bg-white px-3 py-2 dark:bg-slate-900/40">
                <p className="text-slate-400">Cache hit</p>
                <p className="font-semibold dark:text-white">{(parseFloat(item.cache_hit_rate) * 100).toFixed(1)}%</p>
              </div>
              <div className="rounded-lg bg-white px-3 py-2 dark:bg-slate-900/40">
                <p className="text-slate-400">Errors</p>
                <p className="font-semibold dark:text-white">{(parseFloat(item.error_rate) * 100).toFixed(1)}%</p>
              </div>
            </div>
            <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
              Avg latency: {item.avg_latency_ms ? `${parseFloat(item.avg_latency_ms).toFixed(0)}ms` : '—'}
            </p>
          </div>
        ))}
      </div>
    )}
  </section>

  <section className="space-y-4">
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-base font-semibold dark:text-white">Provider Routes</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Each route maps an alias to a provider model with priority and fallback.</p>
      </div>
      {canManage && (
        <button
          onClick={() => setShowRouteForm((v) => !v)}
          className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
        >
          {showRouteForm ? <ChevronUp className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
          {showRouteForm ? 'Cancel' : 'Add Route'}
        </button>
      )}
    </div>

    {showRouteForm && canManage && (
      <div className="rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-900/10 p-4">
        <form onSubmit={handleCreateRoute} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-500 dark:text-slate-400">Alias (route name) *</label>
            <input type="text" placeholder="e.g. gpt-4o" value={newRouteAlias} onChange={(e) => setNewRouteAlias(e.target.value)} className={inputCls} required />
          </div>
          <div className="flex flex-col gap-1 sm:col-span-2">
            <label className="text-xs text-slate-500 dark:text-slate-400">Provider &amp; Model *</label>
            <select
              className={inputCls}
              value={`${newRouteProvider}::${newRouteTargetModel}`}
              onChange={(e) => {
                const [prov, model] = e.target.value.split('::')
                setNewRouteProvider(prov)
                setNewRouteTargetModel(model ?? '')
              }}
              required
            >
              <option value="::">— select model —</option>
              {pricing.length > 0 ? (
                (() => {
                  const grouped: Record<string, typeof pricing> = {}
                  pricing.forEach((p) => { ;(grouped[p.provider] ??= []).push(p) })
                  return Object.entries(grouped).map(([prov, models]) => (
                    <optgroup key={prov} label={prov}>
                      {models.map((m) => (
                        <option key={m.id} value={`${m.provider}::${m.model}`}>{m.model}</option>
                      ))}
                    </optgroup>
                  ))
                })()
              ) : (
                <>
                  <optgroup label="openai">
                    <option value="openai::gpt-4o">gpt-4o</option>
                    <option value="openai::gpt-4o-mini">gpt-4o-mini</option>
                  </optgroup>
                  <optgroup label="anthropic">
                    <option value="anthropic::claude-sonnet-4-6">claude-sonnet-4-6</option>
                  </optgroup>
                  <optgroup label="azure">
                    <option value="azure::gpt-4o">gpt-4o (Azure)</option>
                    <option value="azure::gpt-4o-mini">gpt-4o-mini (Azure)</option>
                  </optgroup>
                  <optgroup label="bedrock">
                    <option value="bedrock::anthropic.claude-3-5-sonnet-20241022-v2:0">claude-3-5-sonnet (Bedrock)</option>
                    <option value="bedrock::amazon.nova-pro-v1:0">nova-pro (Bedrock)</option>
                    <option value="bedrock::meta.llama3-2-90b-instruct-v1:0">llama3-2-90b (Bedrock)</option>
                  </optgroup>
                  <optgroup label="vertex">
                    <option value="vertex::gemini-2.0-flash">gemini-2.0-flash (Vertex)</option>
                    <option value="vertex::gemini-1.5-pro">gemini-1.5-pro (Vertex)</option>
                  </optgroup>
                </>
              )}
            </select>
          </div>
          <input type="text" placeholder="Base URL (optional)" value={newRouteBaseUrl} onChange={(e) => setNewRouteBaseUrl(e.target.value)} className={inputCls} />
          <input type="text" placeholder="API key env var (e.g. OPENAI_API_KEY)" value={newRouteApiKeyEnvVar} onChange={(e) => setNewRouteApiKeyEnvVar(e.target.value)} className={inputCls} />
          <select value={newRouteRoutingGroupId} onChange={(e) => setNewRouteRoutingGroupId(e.target.value)} className={inputCls}>
            <option value="">No routing group</option>
            {routingGroups
              .filter((group) => group.alias === newRouteAlias.trim() || newRouteAlias.trim().length === 0)
              .map((group) => (
                <option key={group.id} value={group.id}>
                  {group.alias} / {group.name}
                </option>
              ))}
          </select>
          <div className="flex flex-col gap-1 sm:col-span-2 lg:col-span-3">
            <label className="text-xs text-slate-500 dark:text-slate-400">
              Provider Config JSON <span className="text-slate-400">(optional — Azure: deployment_name/api_version; Bedrock: region; Vertex: project/location)</span>
            </label>
            <textarea
              placeholder='e.g. {"deployment_name": "my-gpt4o", "api_version": "2024-02-01"}'
              value={newRouteConfigStr}
              onChange={(e) => { setNewRouteConfigStr(e.target.value); setNewRouteConfigError('') }}
              className={`${inputCls} min-h-[60px] resize-y font-mono text-xs`}
              rows={2}
            />
            {newRouteConfigError && <p className="text-xs text-red-500">{newRouteConfigError}</p>}
          </div>
          <div className="flex items-center gap-2">
            <input type="number" placeholder="Priority" value={newRoutePriority} onChange={(e) => setNewRoutePriority(e.target.value)} className={`w-24 ${inputCls}`} min={1} max={100} />
          </div>
          <input type="text" placeholder="Region (e.g. us-east-1)" value={newRouteRegion} onChange={(e) => setNewRouteRegion(e.target.value)} className={inputCls} />
          <input type="text" placeholder="Required tags (csv)" value={newRouteRequiredTags} onChange={(e) => setNewRouteRequiredTags(e.target.value)} className={inputCls} />
          <input type="text" placeholder="Excluded tags (csv)" value={newRouteExcludedTags} onChange={(e) => setNewRouteExcludedTags(e.target.value)} className={inputCls} />
          {/* Runtime controls row */}
          <div className="sm:col-span-2 lg:col-span-3 border-t border-indigo-100 dark:border-indigo-900 pt-3 mt-1">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">Runtime Controls</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-500 dark:text-slate-400">Daily Cost Cap (USD)</label>
                <input type="number" placeholder="e.g. 10.00" step="0.01" min="0" value={newRouteDailyCap} onChange={(e) => setNewRouteDailyCap(e.target.value)} className={inputCls} />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-500 dark:text-slate-400">Monthly Cost Cap (USD)</label>
                <input type="number" placeholder="e.g. 100.00" step="0.01" min="0" value={newRouteMonthlyCap} onChange={(e) => setNewRouteMonthlyCap(e.target.value)} className={inputCls} />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-500 dark:text-slate-400">Per-User RPM Limit</label>
                <input type="number" placeholder="e.g. 60" min="1" value={newRoutePerUserRpm} onChange={(e) => setNewRoutePerUserRpm(e.target.value)} className={inputCls} />
              </div>
              <div className="flex flex-col gap-1 sm:col-span-2">
                <label className="text-xs text-slate-500 dark:text-slate-400">Fallback Chain Aliases</label>
                <input
                  type="text"
                  placeholder="e.g. gpt-4o-mini, gpt-4.1-mini"
                  value={newRouteFallbackAliases}
                  onChange={(e) => setNewRouteFallbackAliases(e.target.value)}
                  className={inputCls}
                />
                <p className="text-[11px] text-slate-400 dark:text-slate-500">
                  Comma-separated route aliases to try if this endpoint is unhealthy or fails (timeouts, 429, 5xx).
                </p>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-500 dark:text-slate-400">On context-length error</label>
                <input
                  type="text"
                  placeholder="e.g. long-context alias"
                  value={newRouteContextFallback}
                  onChange={(e) => setNewRouteContextFallback(e.target.value)}
                  className={inputCls}
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-500 dark:text-slate-400">On content-policy error</label>
                <input
                  type="text"
                  placeholder="e.g. alternate-provider alias"
                  value={newRoutePolicyFallback}
                  onChange={(e) => setNewRoutePolicyFallback(e.target.value)}
                  className={inputCls}
                />
                <p className="text-[11px] text-slate-400 dark:text-slate-500">
                  Other 400-class errors aren&apos;t retried or sent to fallbacks; the client gets the provider&apos;s status.
                </p>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-500 dark:text-slate-400">Mirror (shadow) alias</label>
                <input
                  type="text"
                  placeholder="e.g. candidate-model alias"
                  value={newRouteMirrorAlias}
                  onChange={(e) => setNewRouteMirrorAlias(e.target.value)}
                  className={inputCls}
                />
              </div>
              <div className="flex flex-col gap-1 lg:col-span-3">
                <label className="text-xs text-slate-500 dark:text-slate-400">Mirror sample %</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  placeholder="e.g. 10"
                  value={newRouteMirrorPct}
                  onChange={(e) => setNewRouteMirrorPct(e.target.value)}
                  className={inputCls}
                />
                <p className="text-[11px] text-slate-400 dark:text-slate-500">
                  Sampled requests are re-sent to the mirror alias in the background and recorded as shadow spend.
                </p>
              </div>
              <div className="flex items-center gap-2 mt-4">
                <input
                  id="pii-redact"
                  type="checkbox"
                  checked={newRoutePiiRedaction}
                  onChange={(e) => setNewRoutePiiRedaction(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="pii-redact" className="text-xs text-slate-600 dark:text-slate-300 cursor-pointer">PII Redaction</label>
              </div>
              <div className="flex items-center gap-2 mt-4">
                <input
                  id="semantic-cache"
                  type="checkbox"
                  checked={newRouteSemanticCache}
                  onChange={(e) => setNewRouteSemanticCache(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="semantic-cache" className="text-xs text-slate-600 dark:text-slate-300 cursor-pointer" title="Also serve near-duplicate prompts from the semantic cache">Semantic Cache</label>
              </div>
              <div className="flex items-center gap-2 mt-4">
                <input
                  id="context-compiler"
                  type="checkbox"
                  checked={newRouteContextCompiler}
                  onChange={(e) => setNewRouteContextCompiler(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="context-compiler" className="text-xs text-slate-600 dark:text-slate-300 cursor-pointer" title="Shrink oversized requests before routing: dedup, tool-output compression, rerank, compaction">Context Compiler</label>
              </div>
              {newRouteContextCompiler && (
                <div className="mt-2 flex flex-col gap-2 rounded-lg border border-indigo-200 dark:border-indigo-800 p-2">
                  <div className="flex flex-col gap-1">
                    <label className="text-[11px] text-slate-500 dark:text-slate-400">Compaction model (local)</label>
                    <select className={inputCls} value={newRouteCompilerModel} onChange={(e) => setNewRouteCompilerModel(e.target.value)}>
                      <option value="">— default —</option>
                      {pricing.filter((p) => ['ollama', 'vllm', 'local'].includes(p.provider)).map((m) => (
                        <option key={m.id} value={m.model}>{m.model}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[11px] text-slate-500 dark:text-slate-400">Reranker model</label>
                    <select className={inputCls} value={newRouteRerankerModel} onChange={(e) => setNewRouteRerankerModel(e.target.value)}>
                      <option value="flashrank">flashrank (fast, default)</option>
                      <option value="bge-reranker-base">BGE reranker (quality)</option>
                      <option value="jina-tiny">jina tiny</option>
                    </select>
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[11px] text-slate-500 dark:text-slate-400">Engage threshold (tokens · 0 = always)</label>
                    <input type="number" min="0" value={newRouteCompilerThreshold} onChange={(e) => setNewRouteCompilerThreshold(e.target.value)} className={inputCls} />
                  </div>
                  <div className="flex items-center gap-2 border-t border-indigo-200 dark:border-indigo-800 pt-2">
                    <input id="tool-filter" type="checkbox" checked={newRouteToolFilter} onChange={(e) => setNewRouteToolFilter(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                    <label htmlFor="tool-filter" className="text-[11px] text-slate-600 dark:text-slate-300 cursor-pointer" title="Keep only the tools relevant to the request">Tool filtering</label>
                    {newRouteToolFilter && (
                      <input type="number" min="1" value={newRouteToolK} onChange={(e) => setNewRouteToolK(e.target.value)} className={`w-16 ${inputCls}`} title="Keep top-k tools" />
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <input id="skills" type="checkbox" checked={newRouteSkills} onChange={(e) => setNewRouteSkills(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                    <label htmlFor="skills" className="text-[11px] text-slate-600 dark:text-slate-300 cursor-pointer" title="Inject matched skill bodies from the registry">Skill injection</label>
                    {newRouteSkills && (
                      <input type="number" min="1" value={newRouteSkillK} onChange={(e) => setNewRouteSkillK(e.target.value)} className={`w-16 ${inputCls}`} title="Max skills injected" />
                    )}
                  </div>
                  <div className="flex items-center gap-2 border-t border-indigo-200 dark:border-indigo-800 pt-2">
                    <input
                      id="compress"
                      type="checkbox"
                      checked={newRouteCompress}
                      onChange={(e) => setNewRouteCompress(e.target.checked)}
                      className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <label htmlFor="compress" className="text-[11px] text-slate-600 dark:text-slate-300 cursor-pointer" title="LLMLingua-2 prompt compression — lossy, opt-in">Prompt compression (LLMLingua-2)</label>
                  </div>
                  {newRouteCompress && (
                    <>
                      <div className="flex flex-col gap-1">
                        <label className="text-[11px] text-slate-500 dark:text-slate-400">Compression model</label>
                        <select className={inputCls} value={newRouteCompressModel} onChange={(e) => setNewRouteCompressModel(e.target.value)}>
                          <option value="bert-base-multilingual">bert-base-multilingual (fast, default)</option>
                          <option value="xlm-roberta-large">xlm-roberta-large (quality)</option>
                        </select>
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-[11px] text-slate-500 dark:text-slate-400">Keep rate (0.1–1.0 · lower = more aggressive)</label>
                        <input type="number" min="0.1" max="1" step="0.05" value={newRouteCompressRate} onChange={(e) => setNewRouteCompressRate(e.target.value)} className={inputCls} />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-[11px] text-slate-500 dark:text-slate-400">Compress when</label>
                        <select className={inputCls} value={newRouteCompressWhen} onChange={(e) => setNewRouteCompressWhen(e.target.value)}>
                          <option value="over_budget">only over token budget</option>
                          <option value="over_pct">over a % of the budget</option>
                          <option value="always">always</option>
                        </select>
                      </div>
                      {newRouteCompressWhen === 'over_pct' && (
                        <div className="flex flex-col gap-1">
                          <label className="text-[11px] text-slate-500 dark:text-slate-400">Budget fraction to trigger (e.g. 0.8)</label>
                          <input type="number" min="0.1" max="1" step="0.05" value={newRouteCompressPct} onChange={(e) => setNewRouteCompressPct(e.target.value)} className={inputCls} />
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="sm:col-span-2 lg:col-span-3 border-t border-indigo-100 dark:border-indigo-900 pt-3 mt-1">
            <div className="flex items-center gap-2">
              <input
                id="intelligent-routing"
                type="checkbox"
                checked={newRouteIntelligent}
                onChange={(e) => setNewRouteIntelligent(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              <label htmlFor="intelligent-routing" className="text-xs text-slate-600 dark:text-slate-300 cursor-pointer" title="Classify complexity × risk and route to a model tier; also sets reasoning effort">Intelligent Routing</label>
            </div>
            {newRouteIntelligent && (
              <div className="mt-2 flex flex-col gap-1">
                <label className="text-[11px] text-slate-500 dark:text-slate-400">Routing config (JSON) — tiers, matrix, classifier_mode, llm_model, reasoning_effort, on_failure</label>
                <textarea
                  rows={12}
                  value={newRouteRoutingConfigStr}
                  onChange={(e) => { setNewRouteRoutingConfigStr(e.target.value); setNewRouteRoutingError('') }}
                  className={`${inputCls} font-mono text-[11px]`}
                />
                {newRouteRoutingError && <p className="text-xs text-red-500">{newRouteRoutingError}</p>}
              </div>
            )}
          </div>
          <div className="sm:col-span-2 lg:col-span-3">
            <button type="submit" disabled={creatingRoute || !newRouteAlias || !newRouteTargetModel} className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors">
              {creatingRoute ? 'Adding…' : 'Add Route'}
            </button>
          </div>
        </form>
      </div>
    )}

    <div className="flex items-center gap-2">
      <input
        type="search"
        aria-label="Search routes by alias, provider, model, region or group"
        placeholder="Search routes…"
        value={routeQuery}
        onChange={(e) => setRouteQuery(e.target.value)}
        className={`${inputCls} max-w-xs`}
      />
      <span className="text-xs text-slate-500">{visibleRoutes.length} of {gatewayRoutes.length}</span>
    </div>
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      {visibleRoutes.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2">
          <Network className="h-8 w-8 text-slate-300 dark:text-slate-600" />
          <p className="text-sm text-slate-500 dark:text-slate-400">{gatewayRoutes.length === 0 ? 'No routes configured yet.' : 'No routes match this search.'}</p>
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Alias</th>
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Provider</th>
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Model</th>
              <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Priority</th>
              <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
              {canManage && <th className="px-4 py-2.5" />}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
            {visibleRoutes.map((route) => (
              <>
              <tr key={route.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                {(() => {
                  const fallbackAliases = getRouteFallbackAliases(route)
                  return (
                    <>
                <td className="px-4 py-2.5">
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-sm font-semibold dark:text-slate-200">{route.alias}</span>
                    <div className="flex flex-wrap gap-1">
                      {route.routing_group_name && (
                        <span className="rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
                          {route.routing_group_name}
                        </span>
                      )}
                      {route.region && (
                        <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                          {route.region}
                        </span>
                      )}
                      {route.required_tags.length > 0 && (
                        <span className="rounded-full bg-sky-100 px-1.5 py-0.5 text-[10px] font-medium text-sky-700 dark:bg-sky-900/30 dark:text-sky-300">
                          needs {route.required_tags.join(', ')}
                        </span>
                      )}
                      {route.excluded_tags.length > 0 && (
                        <span className="rounded-full bg-rose-100 px-1.5 py-0.5 text-[10px] font-medium text-rose-700 dark:bg-rose-900/30 dark:text-rose-300">
                          avoids {route.excluded_tags.join(', ')}
                        </span>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-4 py-2.5 text-xs capitalize text-slate-600 dark:text-slate-300">{route.provider}</td>
                <td className="px-4 py-2.5 font-mono text-xs text-slate-500 dark:text-slate-400">{route.target_model}</td>
                <td className="px-4 py-2.5 text-center text-xs text-slate-500 dark:text-slate-400">{route.priority}</td>
                <td className="px-4 py-2.5 text-center">
                  <div className="flex flex-col items-center gap-1">
                    <button
                      onClick={() => canManage && handleToggleRoute(route)}
                      disabled={!canManage}
                      className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize transition-colors ${getDeploymentStatusTone(route.deployment_status)} ${canManage ? 'cursor-pointer hover:opacity-80' : 'cursor-default'}`}
                      title={route.disabled_reason ?? undefined}
                    >
                      {route.deployment_status}
                    </button>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400">
                      {route.is_active ? 'Route enabled' : 'Route disabled'}
                    </span>
                    {route.health_summary && (
                      <span className="max-w-[160px] text-[11px] text-center text-slate-400 dark:text-slate-500" title={route.health_summary}>
                        {route.health_summary}
                      </span>
                    )}
                    {route.disabled_reason && (
                      <span className="text-xs text-red-500 dark:text-red-400 max-w-[120px] truncate" title={route.disabled_reason}>
                        {route.disabled_reason}
                      </span>
                    )}
                    {fallbackAliases.length > 0 && (
                      <span
                        className="rounded-full bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-300 px-1.5 py-0.5 text-[10px] font-medium"
                        title={`Fallback chain: ${fallbackAliases.join(', ')}`}
                      >
                        Fallback {fallbackAliases.length}
                      </span>
                    )}
                    {fallbackRules(route.fallback_config).length > 0 && (
                      <span
                        className="rounded-full bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 px-1.5 py-0.5 text-[10px] font-medium"
                        title={`Error-triggered fallbacks: ${fallbackRules(route.fallback_config)
                          .map((r) => `${Array.isArray(r.on) ? r.on.join('/') : '?'} → ${String(r.alias)}`)
                          .join(', ')}`}
                      >
                        On error {fallbackRules(route.fallback_config).length}
                      </span>
                    )}
                    {getMirror(route.mirror_config).alias && (
                      <span
                        className="rounded-full bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 px-1.5 py-0.5 text-[10px] font-medium"
                        title={`Shadow traffic to ${getMirror(route.mirror_config).alias}`}
                      >
                        Mirror {getMirror(route.mirror_config).pct || 0}%
                      </span>
                    )}
                    {route.pii_redaction_enabled && (
                      <span className="rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 px-1.5 py-0.5 text-[10px] font-medium">PII</span>
                    )}
                    {canManage ? (
                      <button
                        onClick={() => handleToggleSemanticCache(route)}
                        title={route.semantic_cache_enabled ? 'Semantic cache ON — click to turn off' : 'Semantic cache OFF — click to turn on'}
                        className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium transition-colors cursor-pointer hover:opacity-80 ${route.semantic_cache_enabled ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300' : 'bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500'}`}
                      >
                        Cache {route.semantic_cache_enabled ? 'ON' : 'OFF'}
                      </button>
                    ) : route.semantic_cache_enabled && (
                      <span className="rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 px-1.5 py-0.5 text-[10px] font-medium">Cache</span>
                    )}
                    {canManage ? (
                      <button
                        onClick={() => handleToggleContextCompiler(route)}
                        title={route.context_compiler_enabled ? 'Context compiler ON — click to turn off' : 'Context compiler OFF — click to turn on'}
                        className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium transition-colors cursor-pointer hover:opacity-80 ${route.context_compiler_enabled ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300' : 'bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500'}`}
                      >
                        Compiler {route.context_compiler_enabled ? 'ON' : 'OFF'}
                      </button>
                    ) : route.context_compiler_enabled && (
                      <span className="rounded-full bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 px-1.5 py-0.5 text-[10px] font-medium">Compiler</span>
                    )}
                    {canManage ? (
                      <button
                        onClick={() => handleToggleIntelligentRouting(route)}
                        title={route.intelligent_routing_enabled ? 'Intelligent routing ON — click to turn off' : 'Intelligent routing OFF — click to turn on'}
                        className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium transition-colors cursor-pointer hover:opacity-80 ${route.intelligent_routing_enabled ? 'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300' : 'bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500'}`}
                      >
                        Routing {route.intelligent_routing_enabled ? 'ON' : 'OFF'}
                      </button>
                    ) : route.intelligent_routing_enabled && (
                      <span className="rounded-full bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 px-1.5 py-0.5 text-[10px] font-medium">Routing</span>
                    )}
                  </div>
                </td>
                {canManage && (
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button aria-label="Edit" onClick={() => beginRouteEdit(route)} className="rounded-lg p-1.5 text-slate-400 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors">
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button aria-label="Delete" onClick={() => handleDeleteRoute(route.id)} className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                )}
                    </>
                  )
                })()}
              </tr>
              {routeEditState?.id === route.id && (
                <tr>
                  <td colSpan={canManage ? 6 : 5} className="bg-indigo-50/40 dark:bg-indigo-900/10 px-4 py-4">
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      <div className="sm:col-span-2 lg:col-span-3">
                        <p className="text-sm font-semibold text-indigo-800 dark:text-indigo-300">Edit route configuration</p>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Adjust provider target, routing group assignment, runtime caps, fallback aliases, and JSON config in place.</p>
                      </div>
                      <input value={routeEditState.alias} onChange={(e) => setRouteEditState({ ...routeEditState, alias: e.target.value })} className={inputCls} placeholder="Alias" />
                      <input value={routeEditState.targetModel} onChange={(e) => setRouteEditState({ ...routeEditState, targetModel: e.target.value })} className={inputCls} placeholder="Target model" />
                      <select value={routeEditState.routingGroupId} onChange={(e) => setRouteEditState({ ...routeEditState, routingGroupId: e.target.value })} className={inputCls}>
                        <option value="">No routing group</option>
                        {routingGroups
                          .filter((group) => group.alias === routeEditState.alias.trim() || routeEditState.alias.trim().length === 0)
                          .map((group) => (
                            <option key={group.id} value={group.id}>
                              {group.alias} / {group.name}
                            </option>
                          ))}
                      </select>
                      <input value={routeEditState.baseUrl} onChange={(e) => setRouteEditState({ ...routeEditState, baseUrl: e.target.value })} className={inputCls} placeholder="Base URL" />
                      <input value={routeEditState.apiKeyEnvVar} onChange={(e) => setRouteEditState({ ...routeEditState, apiKeyEnvVar: e.target.value })} className={inputCls} placeholder="API key env var" />
                      <input value={routeEditState.priority} onChange={(e) => setRouteEditState({ ...routeEditState, priority: e.target.value })} className={inputCls} placeholder="Priority" />
                      <input value={routeEditState.region} onChange={(e) => setRouteEditState({ ...routeEditState, region: e.target.value })} className={inputCls} placeholder="Region" />
                      <input value={routeEditState.requiredTags} onChange={(e) => setRouteEditState({ ...routeEditState, requiredTags: e.target.value })} className={inputCls} placeholder="Required tags (csv)" />
                      <input value={routeEditState.excludedTags} onChange={(e) => setRouteEditState({ ...routeEditState, excludedTags: e.target.value })} className={inputCls} placeholder="Excluded tags (csv)" />
                      <input value={routeEditState.dailyCostLimitUsd} onChange={(e) => setRouteEditState({ ...routeEditState, dailyCostLimitUsd: e.target.value })} className={inputCls} placeholder="Daily cap USD" />
                      <input value={routeEditState.monthlyCostLimitUsd} onChange={(e) => setRouteEditState({ ...routeEditState, monthlyCostLimitUsd: e.target.value })} className={inputCls} placeholder="Monthly cap USD" />
                      <input value={routeEditState.perUserRpmLimit} onChange={(e) => setRouteEditState({ ...routeEditState, perUserRpmLimit: e.target.value })} className={inputCls} placeholder="Per-user RPM" />
                      <input value={routeEditState.fallbackAliases} onChange={(e) => setRouteEditState({ ...routeEditState, fallbackAliases: e.target.value })} className={inputCls} placeholder="Fallback aliases (csv)" />
                      <input value={routeEditState.contextWindowFallback} onChange={(e) => setRouteEditState({ ...routeEditState, contextWindowFallback: e.target.value })} className={inputCls} placeholder="On context-length error → alias" />
                      <input value={routeEditState.contentPolicyFallback} onChange={(e) => setRouteEditState({ ...routeEditState, contentPolicyFallback: e.target.value })} className={inputCls} placeholder="On content-policy error → alias" />
                      <input value={routeEditState.mirrorAlias} onChange={(e) => setRouteEditState({ ...routeEditState, mirrorAlias: e.target.value })} className={inputCls} placeholder="Mirror (shadow) alias" />
                      <input type="number" min="0" max="100" step="0.1" value={routeEditState.mirrorSamplePct} onChange={(e) => setRouteEditState({ ...routeEditState, mirrorSamplePct: e.target.value })} className={inputCls} placeholder="Mirror sample %" />
                      <textarea value={routeEditState.routeConfigStr} onChange={(e) => { setRouteEditState({ ...routeEditState, routeConfigStr: e.target.value }); setRouteEditError('') }} className={`${inputCls} min-h-[96px] font-mono text-xs sm:col-span-2 lg:col-span-3`} placeholder="Provider config JSON" />
                      <textarea value={routeEditState.routingConfigStr} onChange={(e) => { setRouteEditState({ ...routeEditState, routingConfigStr: e.target.value }); setRouteEditError('') }} className={`${inputCls} min-h-[120px] font-mono text-xs sm:col-span-2 lg:col-span-3`} placeholder="Routing config JSON" />
                      <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                        <input type="checkbox" checked={routeEditState.piiRedactionEnabled} onChange={(e) => setRouteEditState({ ...routeEditState, piiRedactionEnabled: e.target.checked })} className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                        PII redaction
                      </label>
                      <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                        <input type="checkbox" checked={routeEditState.semanticCacheEnabled} onChange={(e) => setRouteEditState({ ...routeEditState, semanticCacheEnabled: e.target.checked })} className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                        Semantic cache
                      </label>
                      <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                        <input type="checkbox" checked={routeEditState.contextCompilerEnabled} onChange={(e) => setRouteEditState({ ...routeEditState, contextCompilerEnabled: e.target.checked })} className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                        Context compiler
                      </label>
                      <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                        <input type="checkbox" checked={routeEditState.intelligentRoutingEnabled} onChange={(e) => setRouteEditState({ ...routeEditState, intelligentRoutingEnabled: e.target.checked })} className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                        Intelligent routing
                      </label>
                      {routeEditError && <p className="text-xs text-red-500 sm:col-span-2 lg:col-span-3">{routeEditError}</p>}
                      <div className="sm:col-span-2 lg:col-span-3 flex items-center gap-2">
                        <button onClick={() => void handleSaveRouteEdit()} disabled={savingRouteEdit} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                          {savingRouteEdit ? 'Saving...' : 'Save changes'}
                        </button>
                        <button onClick={() => setRouteEditState(null)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                          Cancel
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
              )}
              </>
            ))}
          </tbody>
        </table>
      )}
    </div>
  </section>

  </div>
  )
}
