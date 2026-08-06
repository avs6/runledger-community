import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { getToolPolicies, getToolPolicyAnalytics, simulateToolPolicy } from '@/lib/api'

export default async function ToolPoliciesPage() {
  const session = await getServerSession(authOptions)
  const apiKey = (session as Record<string, string> | null)?.apiKey
  if (!apiKey) return <p className="p-8 text-slate-500">Sign in to view tool policies.</p>

  try {
    const [policies, analytics, simulation] = await Promise.all([
      getToolPolicies(apiKey),
      getToolPolicyAnalytics(apiKey, 250),
      simulateToolPolicy(apiKey, {
        tool_name: 'web-search',
        tool_type: 'read',
        risk_score: 25,
        context: { environment: 'prod' },
      }),
    ])

    return (
      <div className="mx-auto max-w-7xl space-y-8 p-6 md:p-10">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Tool Policies Engine
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Allow and deny rules with simulation and usage analytics across the tool surface.
            </p>
          </div>
          <span className="text-sm text-slate-500">{policies.total} active policies</span>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Total Policies</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{policies.total}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Tools Seen</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{analytics.unique_tools}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Calls Analyzed</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{analytics.total_calls}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Simulation Result</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{simulation.final_action}</p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
          <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Policy Simulation</h2>
            <p className="mt-2 text-sm text-slate-500">
              Sample request for <span className="font-mono">web-search</span> resolves to <span className="font-semibold">{simulation.final_action}</span>.
            </p>
            <div className="mt-4 space-y-3">
              {simulation.matched_policy_names.length === 0 ? (
                <p className="text-sm text-slate-500">No policies matched the sample payload.</p>
              ) : (
                simulation.matched_policy_names.map((name, index) => (
                  <div key={name} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                    <p className="font-medium text-slate-900 dark:text-slate-50">{name}</p>
                    <p className="mt-1 text-xs text-slate-500">{simulation.reasons[index] || 'matched'}</p>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white/90 dark:border-slate-700 dark:bg-slate-900/80">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800/60">
                <tr>
                  <th className="px-4 py-3">Tool</th>
                  <th className="px-4 py-3">Calls</th>
                  <th className="px-4 py-3">Allowed</th>
                  <th className="px-4 py-3">Denied</th>
                  <th className="px-4 py-3">Avg Duration</th>
                </tr>
              </thead>
              <tbody>
                {analytics.items.map((item) => (
                  <tr key={item.tool_name} className="border-t border-slate-200 dark:border-slate-700">
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-50">{item.tool_name}</td>
                    <td className="px-4 py-3 text-slate-500">{item.total_calls}</td>
                    <td className="px-4 py-3 text-slate-500">{item.allowed_calls}</td>
                    <td className="px-4 py-3 text-slate-500">{item.denied_calls}</td>
                    <td className="px-4 py-3 text-slate-500">
                      {item.avg_duration_ms != null ? `${item.avg_duration_ms.toFixed(1)} ms` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      </div>
    )
  } catch {
    return <p className="p-8 text-slate-500">Failed to load tool policies.</p>
  }
}
