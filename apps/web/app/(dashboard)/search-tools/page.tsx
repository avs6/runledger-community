import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { getSearchToolPolicies, getSearchTools } from '@/lib/api'

function money(value: number) {
  if (value >= 1) return `$${value.toFixed(2)}`
  if (value >= 0.001) return `$${value.toFixed(4)}`
  return `$${value.toFixed(6)}`
}

export default async function SearchToolsPage() {
  const session = await getServerSession(authOptions)
  const apiKey = (session as Record<string, string> | null)?.apiKey
  if (!apiKey) return <p className="p-8 text-slate-500">Sign in to view search tools.</p>

  try {
    const tools = await getSearchTools(apiKey)
    const firstToolPolicySummary = tools.items[0]
      ? await getSearchToolPolicies(apiKey, tools.items[0].id)
      : null

    return (
      <div className="mx-auto max-w-7xl space-y-8 p-6 md:p-10">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Search Tools Integration
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Registry coverage, endpoint metadata, and policy attachments for search providers.
            </p>
          </div>
          <span className="text-sm text-slate-500">{tools.total} registered tools</span>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Active Providers</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
              {tools.items.filter((tool) => tool.is_active).length}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Queries Routed</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
              {tools.items.reduce((sum, tool) => sum + tool.total_queries, 0).toLocaleString()}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Attached Policies</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">
              {tools.items.reduce((sum, tool) => sum + tool.policy_count, 0)}
            </p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white/90 dark:border-slate-700 dark:bg-slate-900/80">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800/60">
                <tr>
                  <th className="px-4 py-3">Tool</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Queries</th>
                  <th className="px-4 py-3">Cost</th>
                  <th className="px-4 py-3">Policies</th>
                </tr>
              </thead>
              <tbody>
                {tools.items.map((tool) => (
                  <tr key={tool.id} className="border-t border-slate-200 dark:border-slate-700">
                    <td className="px-4 py-3">
                      <p className="font-semibold text-slate-900 dark:text-slate-50">{tool.name}</p>
                      <p className="text-xs text-slate-500">{tool.endpoint_url || 'managed internally'}</p>
                    </td>
                    <td className="px-4 py-3 text-slate-500">{tool.tool_type}</td>
                    <td className="px-4 py-3 text-slate-500">{tool.total_queries.toLocaleString()}</td>
                    <td className="px-4 py-3 text-slate-500">{money(tool.total_cost_usd || 0)}</td>
                    <td className="px-4 py-3 text-slate-500">{tool.policy_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Policy Preview</h2>
            {firstToolPolicySummary ? (
              <div className="mt-4 space-y-3">
                <p className="text-sm text-slate-500">
                  Policies currently attached to <span className="font-semibold">{firstToolPolicySummary.tool_name}</span>.
                </p>
                {firstToolPolicySummary.policies.length === 0 ? (
                  <p className="text-sm text-slate-500">No policies attached yet.</p>
                ) : (
                  firstToolPolicySummary.policies.map((policy) => (
                    <div key={policy.id} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-medium text-slate-900 dark:text-slate-50">{policy.name}</p>
                        <span className="text-xs uppercase text-slate-500">{policy.action}</span>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {policy.condition_type || 'all'} • {policy.scope_type}
                      </p>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <p className="mt-4 text-sm text-slate-500">Register a search tool to attach policies.</p>
            )}
          </section>
        </div>
      </div>
    )
  } catch {
    return <p className="p-8 text-slate-500">Failed to load search tools.</p>
  }
}
