'use client'

import { Plus, Trash2, Activity, Pencil, ChevronUp, BarChart2, Sparkles } from 'lucide-react'
import type { RoutingPolicyType } from '@/types/api'
import { inputCls } from './shared'
import { RecommendationPanel } from './RecommendationPanel'
import { PolicyAnalysisPanel } from './PolicyAnalysisPanel'
import { useGateway } from './useGatewayState'

export function PoliciesTab() {
  const {
    canManage,
    routingPolicies,
    policyAlias,
    setPolicyAlias,
    policyType,
    setPolicyType,
    policyConfigStr,
    setPolicyConfigStr,
    creatingPolicy,
    policyConfigError,
    setPolicyConfigError,
    showPolicyForm,
    setShowPolicyForm,
    policyEditState,
    setPolicyEditState,
    savingPolicyEdit,
    policyEditError,
    setPolicyEditError,
    policyAnalysis,
    loadingPolicyAnalysis,
    routingLog,
    loadingLog,
    recommendations,
    loadingRec,
    expandedRec,
    beginPolicyEdit,
    handleSavePolicyEdit,
    handleCreatePolicy,
    handleTogglePolicy,
    handleDeletePolicy,
    handleLoadPolicyAnalysis,
    handlePromotePolicy,
    handleAdvanceCanary,
    handleRollbackPolicy,
    handleLoadRecommendation,
    handleLoadRoutingLog,
  } = useGateway()
  return (
  <div className="space-y-3">

  <section className="space-y-4">
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-base font-semibold dark:text-white">Routing Policies</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Intelligent routing strategies backed by live telemetry — cost, latency, quality.</p>
      </div>
      {canManage && (
        <button
          onClick={() => setShowPolicyForm((v) => !v)}
          className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
        >
          {showPolicyForm ? <ChevronUp className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
          {showPolicyForm ? 'Cancel' : 'Add Policy'}
        </button>
      )}
    </div>

    {showPolicyForm && canManage && (
      <div className="rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-900/10 p-4">
        <form onSubmit={handleCreatePolicy} className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <input type="text" placeholder="Alias (e.g. local)" value={policyAlias} onChange={(e) => setPolicyAlias(e.target.value)} className={inputCls} required />
          <select value={policyType} onChange={(e) => setPolicyType(e.target.value as RoutingPolicyType)} className={inputCls}>
            <option value="manual">manual — priority order</option>
            <option value="cost_optimized">cost_optimized — cheapest above quality floor</option>
            <option value="latency_optimized">latency_optimized — lowest p95</option>
            <option value="quality_optimized">quality_optimized — highest score</option>
            <option value="weighted">weighted — random split by weight</option>
            <option value="canary">canary — % to canary route</option>
            <option value="ab_test">ab_test — traffic split with winner analysis</option>
            <option value="budget_aware">budget_aware — fallback when budget % hit</option>
            <option value="complexity_based">complexity_based — branch on token count</option>
            <option value="outcome_optimized">outcome_optimized — lowest cost-per-success</option>
          </select>
          <div>
            <input
              type="text"
              placeholder='Config JSON e.g. {"quality_floor": 0.6}'
              value={policyConfigStr}
              onChange={(e) => { setPolicyConfigStr(e.target.value); setPolicyConfigError('') }}
              className={`${inputCls} font-mono text-xs`}
            />
            {policyConfigError && <p className="mt-1 text-xs text-red-500">{policyConfigError}</p>}
          </div>
          <button type="submit" disabled={creatingPolicy || !policyAlias} className="sm:col-span-3 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors">
            {creatingPolicy ? 'Creating…' : 'Add Policy'}
          </button>
        </form>
      </div>
    )}

    <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      {routingPolicies.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 gap-2">
          <Activity className="h-7 w-7 text-slate-300 dark:text-slate-600" />
          <p className="text-sm text-slate-500 dark:text-slate-400">No routing policies yet.</p>
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Alias</th>
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Strategy</th>
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Config</th>
              <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
              <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Insights</th>
              <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
              {canManage && <th className="px-4 py-2.5" />}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
            {routingPolicies.map((p) => (
              <>
                <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                  <td className="px-4 py-2.5 font-mono text-sm font-semibold dark:text-slate-200">{p.alias}</td>
                  <td className="px-4 py-2.5 text-xs text-slate-600 dark:text-slate-300">{p.policy_type}</td>
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-400 max-w-[200px] truncate" title={JSON.stringify(p.config)}>
                    {Object.keys(p.config).length ? JSON.stringify(p.config) : '—'}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <button
                      onClick={() => canManage && handleTogglePolicy(p)}
                      disabled={!canManage}
                      className={`rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors ${p.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'} ${canManage ? 'cursor-pointer hover:opacity-80' : 'cursor-default'}`}
                    >
                      {p.is_active ? 'Active' : 'Disabled'}
                    </button>
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <button
                      onClick={() => {
                        void handleLoadRecommendation(p.alias)
                        void handleLoadPolicyAnalysis(p.id)
                      }}
                      disabled={loadingRec[p.alias] || loadingPolicyAnalysis[p.id]}
                      title="View outcome-based routing recommendation"
                      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium transition-colors ${expandedRec === p.alias ? 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400 hover:bg-violet-50 hover:text-violet-600 dark:hover:bg-violet-900/20 dark:hover:text-violet-300'}`}
                    >
                      <Sparkles className="h-3 w-3" />
                      {loadingRec[p.alias] || loadingPolicyAnalysis[p.id] ? '…' : expandedRec === p.alias ? 'Hide' : 'Analyze'}
                    </button>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap items-center justify-center gap-2">
                      {(p.policy_type === 'ab_test' || p.policy_type === 'canary') && (
                        <button
                          onClick={() => void handlePromotePolicy(p.id)}
                          className="rounded-lg border border-indigo-200 px-2 py-1 text-[11px] font-medium text-indigo-700 hover:bg-indigo-50 dark:border-indigo-900/40 dark:text-indigo-300 dark:hover:bg-indigo-950/30"
                        >
                          Promote
                        </button>
                      )}
                      {p.policy_type === 'canary' && (
                        <button
                          onClick={() => void handleAdvanceCanary(p.id)}
                          className="rounded-lg border border-emerald-200 px-2 py-1 text-[11px] font-medium text-emerald-700 hover:bg-emerald-50 dark:border-emerald-900/40 dark:text-emerald-300 dark:hover:bg-emerald-950/30"
                        >
                          Advance
                        </button>
                      )}
                      {(p.policy_type === 'canary' || p.policy_type === 'ab_test') && (
                        <button
                          onClick={() => void handleRollbackPolicy(p.id)}
                          className="rounded-lg border border-amber-200 px-2 py-1 text-[11px] font-medium text-amber-700 hover:bg-amber-50 dark:border-amber-900/40 dark:text-amber-300 dark:hover:bg-amber-950/30"
                        >
                          Roll back
                        </button>
                      )}
                    </div>
                  </td>
                  {canManage && (
                    <td className="px-4 py-2.5 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => beginPolicyEdit(p)} className="rounded-lg p-1.5 text-slate-400 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors">
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button onClick={() => handleDeletePolicy(p.id)} className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
                {policyEditState?.id === p.id && (
                  <tr>
                    <td colSpan={canManage ? 7 : 6} className="px-4 py-4 bg-indigo-50/40 dark:bg-indigo-900/10">
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <div className="sm:col-span-2">
                          <p className="text-sm font-semibold text-indigo-800 dark:text-indigo-300">Edit routing policy</p>
                          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Change policy type, active state, and raw config JSON while keeping analysis and promotion tools nearby.</p>
                        </div>
                        <select value={policyEditState.policyType} onChange={(e) => setPolicyEditState({ ...policyEditState, policyType: e.target.value as RoutingPolicyType })} className={inputCls}>
                          <option value="manual">manual</option>
                          <option value="weighted">weighted</option>
                          <option value="canary">canary</option>
                          <option value="ab_test">ab_test</option>
                          <option value="cost_optimized">cost_optimized</option>
                          <option value="latency_optimized">latency_optimized</option>
                        </select>
                        <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                          <input type="checkbox" checked={policyEditState.isActive} onChange={(e) => setPolicyEditState({ ...policyEditState, isActive: e.target.checked })} className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                          Policy active
                        </label>
                        <textarea value={policyEditState.configStr} onChange={(e) => { setPolicyEditState({ ...policyEditState, configStr: e.target.value }); setPolicyEditError('') }} className={`${inputCls} min-h-[140px] font-mono text-xs sm:col-span-2`} />
                        {policyEditError && <p className="text-xs text-red-500 sm:col-span-2">{policyEditError}</p>}
                        <div className="sm:col-span-2 flex items-center gap-2">
                          <button onClick={() => void handleSavePolicyEdit()} disabled={savingPolicyEdit} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                            {savingPolicyEdit ? 'Saving...' : 'Save changes'}
                          </button>
                          <button onClick={() => setPolicyEditState(null)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                            Cancel
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
                {expandedRec === p.alias && recommendations[p.alias] && (
                  <tr key={`${p.id}-rec`}>
                    <td colSpan={canManage ? 7 : 6} className="px-4 py-0 bg-violet-50/50 dark:bg-violet-900/10">
                      <div className="py-3 space-y-4">
                        <RecommendationPanel rec={recommendations[p.alias]} />
                        {policyAnalysis[p.id] && (
                          <PolicyAnalysisPanel analysis={policyAnalysis[p.id]} />
                        )}
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

  {/* ── Routing Log ── */}
  <section className="space-y-4">
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-base font-semibold dark:text-white">Routing Log</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Which route was selected and why — including the full policy decision.</p>
      </div>
      <button
        onClick={handleLoadRoutingLog}
        disabled={loadingLog}
        className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors"
      >
        <BarChart2 className="h-3.5 w-3.5" />
        {loadingLog ? 'Loading…' : 'Load recent'}
      </button>
    </div>

    {routingLog.length > 0 && (
      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
        <table className="w-full text-xs">
          <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Time</th>
              <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Alias</th>
              <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Model Used</th>
              <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Latency</th>
              <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
              <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Decision Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
            {routingLog.map((req) => (
              <tr key={req.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                <td className="px-3 py-2 text-slate-400 whitespace-nowrap">{new Date(req.created_at).toLocaleTimeString()}</td>
                <td className="px-3 py-2 font-mono dark:text-slate-200">{req.model_requested}</td>
                <td className="px-3 py-2 font-mono text-slate-500 dark:text-slate-400">{req.model_used ?? '—'}</td>
                <td className="px-3 py-2 dark:text-slate-300">{req.latency_ms != null ? `${req.latency_ms}ms` : '—'}</td>
                <td className="px-3 py-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                    req.status === 'success' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' :
                    req.status === 'cache_hit' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' :
                    req.status === 'blocked' ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300' :
                    'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                  }`}>
                    {req.status}
                  </span>
                </td>
                <td className="px-3 py-2 font-mono text-indigo-600 dark:text-indigo-400 max-w-[280px] truncate" title={req.decision_reason ?? ''}>
                  {req.decision_reason ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
    {routingLog.length === 0 && !loadingLog && (
      <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400">
        Click &quot;Load recent&quot; to fetch the last 50 gateway requests.
      </div>
    )}
  </section>

  </div>
  )
}
