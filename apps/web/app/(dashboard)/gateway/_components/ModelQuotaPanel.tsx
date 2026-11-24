'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { getBudgets } from '@/lib/api'
import { routes, type StaticRoute } from '@/lib/routes'
import type { Budget } from '@/types/api'
import { AsyncCard } from '@/components/ui/async-card'

/**
 * Per-model spend limits are budgets with scope_type=model (review G-01): enforced
 * per route in the gateway preflight and managed on the Budgets page. This panel
 * lists them so gateway operators can see which models are capped.
 */
export function ModelQuotaPanel({ apiKey }: { apiKey: string; canManage?: boolean }) {
  const [items, setItems] = useState<Budget[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      setItems((await getBudgets(apiKey, { scope_type: 'model' })).items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load model budgets')
    }
  }, [apiKey])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <section id="gateway-model-quotas">
      <AsyncCard
        title="Model budgets"
        description="Spend limits on a model or model pattern (optionally for one key). A route over its model budget is skipped; with no route left the gateway returns 429."
        loading={items === null && !error}
        error={error}
        onRetry={load}
        empty={items !== null && items.length === 0}
        emptyTitle="No model budgets yet"
        emptyDescription="Create one on the Budgets page with the scope “Model”."
        actions={
          <Link
            href={`${'/budgets' satisfies StaticRoute}?scope_type=model`}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            Manage in Budgets
          </Link>
        }
      >
        <ul className="divide-y divide-slate-100 dark:divide-slate-800">
          {(items ?? []).map((b) => (
            <li key={b.id} className="flex items-center justify-between py-2 text-sm">
              <Link href={routes.budgetsId(b.id)} className="font-mono text-slate-800 hover:underline dark:text-slate-100">
                {b.scope_id}
              </Link>
              <span className="text-xs text-slate-500 dark:text-slate-400">
                ${Number(b.current_spend_usd).toFixed(2)} / ${Number(b.limit_usd).toFixed(2)} {b.period_type} · {b.action}
                {b.api_key_id ? ' · one key' : ''}
              </span>
            </li>
          ))}
        </ul>
      </AsyncCard>
    </section>
  )
}
