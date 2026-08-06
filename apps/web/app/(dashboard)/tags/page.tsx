import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { getAutoTagRules, getTagTree, simulateAutoTagging } from '@/lib/api'

function TagNode({ node, depth = 0 }: { node: import('@/types/api').TagTreeNode; depth?: number }) {
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

export default async function TagsPage() {
  const session = await getServerSession(authOptions)
  const apiKey = (session as Record<string, string> | null)?.apiKey
  if (!apiKey) return <p className="p-8 text-slate-500">Sign in to view tag management.</p>

  try {
    const [tree, rules, simulation] = await Promise.all([
      getTagTree(apiKey),
      getAutoTagRules(apiKey),
      simulateAutoTagging(apiKey, {
        fields: {
          feature: 'support-search',
          prompt: 'search the docs for billing exports',
          provider: 'openai',
        },
      }),
    ])

    return (
      <div className="mx-auto max-w-7xl space-y-8 p-6 md:p-10">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Tag Management
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Hierarchical tags and auto-tagging coverage for workspace metadata.
            </p>
          </div>
          <span className="text-sm text-slate-500">
            {tree.total} tags • {rules.total} rules
          </span>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Hierarchy</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{tree.total}</p>
            <p className="mt-1 text-sm text-slate-500">Active tags available for routing, governance, and reporting.</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Rule Coverage</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{rules.items.filter((r) => r.is_active).length}</p>
            <p className="mt-1 text-sm text-slate-500">Active rules ready to auto-apply tags during ingest and workflows.</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 dark:border-slate-700 dark:bg-slate-900/80">
            <p className="text-xs uppercase tracking-wide text-slate-500">Simulation</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-50">{simulation.matched.length}</p>
            <p className="mt-1 text-sm text-slate-500">Rules matched against a sample prompt payload.</p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.3fr_0.9fr]">
          <section className="space-y-4">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Hierarchy</h2>
            {tree.items.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-sm text-slate-500 dark:border-slate-700">
                No tags created yet.
              </div>
            ) : (
              tree.items.map((node) => <TagNode key={node.id} node={node} />)
            )}
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Auto-Tagging Rules</h2>
            <div className="space-y-3">
              {rules.items.map((rule) => (
                <div key={rule.id} className="rounded-2xl border border-slate-200 bg-white/90 p-4 dark:border-slate-700 dark:bg-slate-900/80">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-semibold text-slate-900 dark:text-slate-50">{rule.name}</p>
                    <span className="text-xs text-slate-500">P{rule.priority}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-500">
                    {rule.match_field} {rule.match_type} <span className="font-mono">{rule.match_pattern}</span>
                  </p>
                  <p className="mt-2 text-xs text-slate-500">
                    Applies <span className="font-mono">{rule.tag_key}={rule.tag_value}</span>
                  </p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    )
  } catch {
    return <p className="p-8 text-slate-500">Failed to load tag management.</p>
  }
}
