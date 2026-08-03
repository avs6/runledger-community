'use client';

import { useSession } from 'next-auth/react';
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Receipt, Trash2, Plus } from 'lucide-react';
import { listChargebackRules, createChargebackRule, deleteChargebackRule } from '@/lib/api';
import type { ChargebackRuleResponse } from '@/types/api';

const ALLOCATION_TYPES = ['proportional', 'fixed', 'per_user', 'per_feature'] as const;

export default function ChargebackPage() {
  const { data: session } = useSession();
  const apiKey = (session as { apiKey?: string })?.apiKey ?? '';

  const [rules, setRules] = useState<ChargebackRuleResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [allocationType, setAllocationType] = useState<string>(ALLOCATION_TYPES[0]);
  const [dimension, setDimension] = useState('');
  const [weight, setWeight] = useState<number>(50);

  const fetchRules = useCallback(async () => {
    if (!apiKey) return;
    try {
      setLoading(true);
      const data = await listChargebackRules(apiKey);
      setRules(data.items);
    } catch {
      toast.error('Failed to load chargeback rules');
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

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
      setDimension('');
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

      <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        {loading ? (
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
              <input
                type="text"
                placeholder="e.g. team, department"
                value={dimension}
                onChange={(e) => setDimension(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
              />
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
    </div>
  );
}
