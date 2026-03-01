'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { getRegressions, getAnnotations, getTopWorkflows } from '@/lib/api'
import type { WorkflowTopList, RegressionList, Annotation } from '@/types/api'
import ChangeImpactPanel from '@/components/economics/ChangeImpactPanel'
import RegressionTable from '@/components/economics/RegressionTable'
import AnnotationForm from '@/components/economics/AnnotationForm'

function Section({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <h2 className="mb-4 text-base font-semibold text-gray-800 dark:text-gray-100">{title}</h2>
      {children}
    </div>
  )
}

function Skeleton() {
  return <div className="h-40 w-full animate-pulse rounded-lg bg-gray-100 dark:bg-gray-700" />
}

export default function EconomicsPage() {
  const { data: session } = useSession()
  const apiKey = session?.apiKey ?? ''

  const [workflows, setWorkflows] = useState<WorkflowTopList | null>(null)
  const [regressions, setRegressions] = useState<RegressionList | null>(null)
  const [annotations, setAnnotations] = useState<Annotation[]>([])
  const [loadingWorkflows, setLoadingWorkflows] = useState(true)
  const [loadingRegressions, setLoadingRegressions] = useState(true)
  const [loadingAnnotations, setLoadingAnnotations] = useState(true)

  useEffect(() => {
    if (!apiKey) return

    getTopWorkflows(apiKey, { metric: 'cost', limit: 10 })
      .then(setWorkflows)
      .finally(() => setLoadingWorkflows(false))

    getRegressions(apiKey)
      .then(setRegressions)
      .finally(() => setLoadingRegressions(false))

    getAnnotations(apiKey)
      .then((data) => setAnnotations(data.items))
      .finally(() => setLoadingAnnotations(false))
  }, [apiKey])

  function handleAnnotationCreated(annotation: Annotation) {
    setAnnotations((prev) => [annotation, ...prev])
  }

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Economics</h1>

      {/* ── Top Workflows ────────────────────────────────────────────────── */}
      <Section title="Top Workflows by Cost">
        {loadingWorkflows ? (
          <Skeleton />
        ) : workflows && workflows.items.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
                <th className="pb-1 font-medium">Feature tag</th>
                <th className="pb-1 text-right font-medium">Runs</th>
                <th className="pb-1 text-right font-medium">Avg cost</th>
                <th className="pb-1 text-right font-medium">p95 cost</th>
                <th className="pb-1 text-right font-medium">Total cost</th>
                <th className="pb-1 text-right font-medium">Calls</th>
              </tr>
            </thead>
            <tbody>
              {workflows.items.map((w, i) => (
                <tr key={i} className="border-b border-gray-100 last:border-0 dark:border-gray-700">
                  <td className="py-2 font-mono text-xs dark:text-gray-300">{w.feature_tag ?? '—'}</td>
                  <td className="py-2 text-right tabular-nums dark:text-gray-300">{w.run_count}</td>
                  <td className="py-2 text-right tabular-nums dark:text-gray-300">
                    ${parseFloat(w.avg_cost_usd).toFixed(6)}
                  </td>
                  <td className="py-2 text-right tabular-nums dark:text-gray-300">
                    ${parseFloat(w.p95_cost_usd).toFixed(6)}
                  </td>
                  <td className="py-2 text-right tabular-nums font-medium dark:text-gray-200">
                    ${parseFloat(w.total_cost_usd).toFixed(4)}
                  </td>
                  <td className="py-2 text-right tabular-nums dark:text-gray-300">{w.call_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">No workflow data yet.</p>
        )}
      </Section>

      {/* ── Version Compare ───────────────────────────────────────────────── */}
      <Section title="Version Compare">
        {apiKey ? (
          <ChangeImpactPanel apiKey={apiKey} />
        ) : (
          <Skeleton />
        )}
      </Section>

      {/* ── Cost Regressions ─────────────────────────────────────────────── */}
      <Section title="Cost Regressions (last 7 days vs prior 7 days)">
        {loadingRegressions ? (
          <Skeleton />
        ) : (
          <RegressionTable items={regressions?.items ?? []} />
        )}
      </Section>

      {/* ── Annotations ──────────────────────────────────────────────────── */}
      <Section title="Annotations">
        {apiKey && (
          <div className="mb-5">
            <AnnotationForm apiKey={apiKey} onCreated={handleAnnotationCreated} />
          </div>
        )}
        {loadingAnnotations ? (
          <Skeleton />
        ) : annotations.length > 0 ? (
          <ul className="space-y-2">
            {annotations.map((a) => (
              <li
                key={a.id}
                className="flex items-start gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="min-w-[100px] text-xs text-gray-500 dark:text-gray-400">
                  <span>{a.annotation_date}</span>
                  {a.version && (
                    <span className="ml-2 rounded bg-indigo-100 px-1.5 py-0.5 font-mono text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                      {a.version}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-800 dark:text-gray-200">{a.note}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">No annotations yet.</p>
        )}
      </Section>
    </div>
  )
}
