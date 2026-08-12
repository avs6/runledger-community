'use client';

import { useSession } from 'next-auth/react';
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Receipt, Trash2, Plus, Download, BarChart3 } from 'lucide-react';
import { useRole } from '@/components/rbac/useRole';
import {
  listChargebackRules,
  createChargebackRule,
  deleteChargebackRule,
  getChargebackReport,
  exportChargebackReport,
} from '@/lib/api';
import type { ChargebackRuleResponse, ChargebackReport } from '@/types/api';

const ALLOCATION_TYPES = ['proportional', 'fixed', 'per_user', 'per_feature'] as const;

const DIMENSIONS = [
  'workspace',
  'team',
  'user',
  'app',
  'model',
  'agent',
  'provider',
  'cost_center',
  'api_key',
  'feature_tag',
] as const;

function buildLast12Months(): string[] {
  const months: string[] = [];
  const now = new Date();
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
  }
  return months;
}

type Tab = 'rules' | 'reports';

export default function ChargebackPage() {
  const { data: session } = useSession();
  const apiKey = (session as { apiKey?: string })?.apiKey ?? '';
  const { canManageOrgSettings } = useRole();

  const [activeTab, setActiveTab] = useState<Tab>('rules');

  // ── Rules state ───────────────────────────────────────────────────────────
  const [rules, setRules] = useState<ChargebackRuleResponse[]>([]);
  const [loadingRules, setLoadingRules] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [allocationType, setAllocationType] = useState<string>(ALLOCATION_TYPES[0]);
  const [dimension, setDimension] = useState<string>(DIMENSIONS[0]);
  const [weight, setWeight] = useState<number>(50);

  // ── Reports state ─────────────────────────────────────────────────────────
  const last12 = buildLast12Months();
  const [selectedPeriod, setSelectedPeriod] = useState(last12[0]);
  const [reportDimension, setReportDimension] = useState<string>('');
  const [report, setReport] = useState<ChargebackReport | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [exporting, setExporting] = useState(false);

  // ── Rules CRUD ────────────────────────────────────────────────────────────
  const fetchRules = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return;
    try {
      setLoadingRules(true);
      const data = await listChargebackRules(apiKey);
      setRules(data.items);
    } catch {
      toast.error('Failed to load chargeback rules');
    } finally {
      setLoadingRules(false);
    }
  }, [apiKey, canManageOrgSettings]);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const handleCreate = async () => {
    if (!dimension.trim()) {
      toast.error('Dimension is required');
      return;
    }
    try {
      setCreating(true);
      await createChargebackRule(apiKey, {
        allocation_type: allocationType,
        dimension: dimension.trim(),
        weight: String(weight),
      });
      toast.success('Rule created');
      setShowForm(false);
      setDimension(DIMENSIONS[0]);
      setWeight(50);
      setAllocationType(ALLOCATION_TYPES[0]);
      fetchRules();
    } catch {
      toast.error('Failed to create rule');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteChargebackRule(apiKey, id);
      toast.success('Rule deleted');
      fetchRules();
    } catch {
      toast.error('Failed to delete rule');
    }
  };

  // ── Reports ───────────────────────────────────────────────────────────────
  const fetchReport = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return;
    try {
      setLoadingReport(true);
      const data = await getChargebackReport(apiKey, {
        period: selectedPeriod,
        dimension: reportDimension || undefined,
      });
      setReport(data.items.length > 0 ? data.items[0] : null);
    } catch {
      toast.error('Failed to load chargeback report');
    } finally {
      setLoadingReport(false);
    }
  }, [apiKey, canManageOrgSettings, selectedPeriod, reportDimension]);

  useEffect(() => {
    if (activeTab === 'reports') fetchReport();
  }, [activeTab, fetchReport]);

  const handleExport = async (format: 'csv' | 'json') => {
    if (!canManageOrgSettings) return;
    try {
      setExporting(true);
      const raw = await exportChargebackReport(apiKey, {
        period: selectedPeriod,
        dimension: reportDimension || undefined,
        format,
      });
      const mimeType = format === 'csv' ? 'text/csv' : 'application/json';
      const blob = new Blob([raw], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `chargeback-report-${selectedPeriod}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Report exported as ${format.toUpperCase()}`);
    } catch {
      toast.error(`Failed to export ${format.toUpperCase()}`);
    } finally {
      setExporting(false);
    }
  };

  // ── Variance color helper ─────────────────────────────────────────────────
  const varianceColor = (v: string | null) => {
    if (v == null) return 'text-slate-400';
    const n = parseFloat(v);
    if (n < 0) return 'text-emerald-600 dark:text-emerald-400';
    if (n > 0) return 'text-red-600 dark:text-red-400';
    return 'text-slate-400';
  };

  // ── Render ────────────────────────────────────────────────────────────────
  if (!canManageOrgSettings) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 p-6">
        <div className="flex items-center gap-3">
          <Receipt className="h-7 w-7 text-indigo-500" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Chargeback &amp; Showback</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Chargeback management is available to organization admins and managers.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Receipt className="h-7 w-7 text-indigo-500" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Chargeback &amp; Showback</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Allocate AI costs to teams, features, or departments
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-slate-100 p-1 dark:bg-slate-800">
        <button
          onClick={() => setActiveTab('rules')}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'rules'
              ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
              : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          Allocation Rules
        </button>
        <button
          onClick={() => setActiveTab('reports')}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'reports'
              ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
              : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          Reports
        </button>
      </div>

      {/* ── Allocation Rules Tab ───────────────────────────────────────────── */}
      {activeTab === 'rules' && (
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          {loadingRules ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : rules.length === 0 ? (
            <p className="text-sm text-slate-500">
              No chargeback rules yet. Create one to start allocating costs.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th className="pb-2 font-medium text-slate-500">Type</th>
                    <th className="pb-2 font-medium text-slate-500">Dimension</th>
                    <th className="pb-2 font-medium text-slate-500">Weight</th>
                    <th className="pb-2 font-medium text-slate-500">Created</th>
                    <th className="pb-2" />
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr
                      key={rule.id}
                      className="border-b border-slate-100 dark:border-slate-800"
                    >
                      <td className="py-3 font-mono text-xs">{rule.allocation_type}</td>
                      <td className="py-3">{rule.dimension}</td>
                      <td className="py-3">{rule.weight}%</td>
                      <td className="py-3 text-slate-500">
                        {new Date(rule.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 text-right">
                        <button
                          onClick={() => handleDelete(rule.id)}
                          className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-950"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {showForm && (
            <div className="mt-4 flex flex-wrap items-end gap-3 border-t border-slate-200 pt-4 dark:border-slate-700">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-500">Type</label>
                <select
                  value={allocationType}
                  onChange={(e) => setAllocationType(e.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
                >
                  {ALLOCATION_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-500">Dimension</label>
                <select
                  value={dimension}
                  onChange={(e) => setDimension(e.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
                >
                  {DIMENSIONS.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-500">Weight (%)</label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={weight}
                  onChange={(e) => setWeight(Number(e.target.value))}
                  className="w-20 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
                />
              </div>
              <button
                onClick={handleCreate}
                disabled={creating}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {creating ? 'Creating...' : 'Create'}
              </button>
            </div>
          )}

          <div className="mt-4">
            <button
              onClick={() => setShowForm(!showForm)}
              className="flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
            >
              <Plus className="h-4 w-4" />
              {showForm ? 'Cancel' : 'Add Rule'}
            </button>
          </div>
        </div>
      )}

      {/* ── Reports Tab ────────────────────────────────────────────────────── */}
      {activeTab === 'reports' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <div className="flex flex-wrap items-end gap-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-500">Period</label>
                <select
                  value={selectedPeriod}
                  onChange={(e) => setSelectedPeriod(e.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
                >
                  {last12.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-500">Dimension</label>
                <select
                  value={reportDimension}
                  onChange={(e) => setReportDimension(e.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
                >
                  <option value="">All</option>
                  {DIMENSIONS.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleExport('csv')}
                  disabled={exporting}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  <Download className="h-4 w-4" />
                  Export CSV
                </button>
                <button
                  onClick={() => handleExport('json')}
                  disabled={exporting}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  <Download className="h-4 w-4" />
                  Export JSON
                </button>
              </div>
            </div>
          </div>

          {/* Summary card */}
          {loadingReport ? (
            <p className="text-sm text-slate-500">Loading report...</p>
          ) : report ? (
            <>
              <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <div className="flex items-center gap-3">
                  <BarChart3 className="h-5 w-5 text-indigo-500" />
                  <div>
                    <p className="text-xs font-medium text-slate-500">
                      Total Cost &mdash; {report.period}
                    </p>
                    <p className="text-2xl font-bold tracking-tight">
                      ${parseFloat(report.total_cost_usd).toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </p>
                  </div>
                </div>
              </div>

              {/* Breakdown table */}
              <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                {report.breakdown.length === 0 ? (
                  <p className="text-sm text-slate-500">No breakdown data for this period.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-slate-200 dark:border-slate-700">
                          <th className="pb-2 font-medium text-slate-500">Dimension</th>
                          <th className="pb-2 font-medium text-slate-500">Value</th>
                          <th className="pb-2 text-right font-medium text-slate-500">Cost (USD)</th>
                          <th className="pb-2 text-right font-medium text-slate-500">% of Total</th>
                          <th className="pb-2 text-right font-medium text-slate-500">Budget (USD)</th>
                          <th className="pb-2 text-right font-medium text-slate-500">Variance (USD)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.breakdown.map((item, idx) => (
                          <tr
                            key={`${item.dimension}-${item.dimension_value}-${idx}`}
                            className="border-b border-slate-100 dark:border-slate-800"
                          >
                            <td className="py-3 font-mono text-xs">{item.dimension}</td>
                            <td className="py-3">{item.dimension_value}</td>
                            <td className="py-3 text-right font-mono">
                              ${parseFloat(item.cost_usd).toLocaleString(undefined, {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              })}
                            </td>
                            <td className="py-3 text-right">
                              {parseFloat(item.pct_of_total).toFixed(1)}%
                            </td>
                            <td className="py-3 text-right font-mono">
                              {item.budget_usd != null
                                ? `$${parseFloat(item.budget_usd).toLocaleString(undefined, {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                  })}`
                                : '—'}
                            </td>
                            <td className={`py-3 text-right font-mono ${varianceColor(item.variance_usd)}`}>
                              {item.variance_usd != null
                                ? `${parseFloat(item.variance_usd) > 0 ? '+' : ''}$${parseFloat(item.variance_usd).toLocaleString(undefined, {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                  })}`
                                : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <p className="text-sm text-slate-500">No report data for the selected period.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
