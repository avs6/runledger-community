'use client'

import { Suspense, useCallback, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { BrainCircuit, Pencil, Plus, Trash2 } from 'lucide-react'
import { PageHeader } from '@/components/ui/page-header'
import { DataTable, type DataTableColumn, type DataTableQuery } from '@/components/ui/data-table'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { useRole } from '@/components/rbac/useRole'
import { getAgents, retireAgent } from '@/lib/api'
import { routes } from '@/lib/routes'
import type { AgentResponse } from '@/types/api'
import { StatusBadge, apiErrorMessage, money, useApiKey } from '../workflows/_components/shared'
import { AgentSheet } from './_components/AgentSheet'

function AgentsInner() {
  const apiKey = useApiKey()
  const { canWrite } = useRole()
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()
  const status = params.get('status') ?? 'active'
  const { confirm, dialog } = useConfirm()
  const [editing, setEditing] = useState<AgentResponse | null>(null)
  const [open, setOpen] = useState(false)
  const [version, setVersion] = useState(0)

  const setStatus = (s: string) => {
    const next = new URLSearchParams(params.toString())
    next.set('status', s)
    next.delete('ag_page')
    router.replace(`${pathname}?${next}`, { scroll: false })
  }

  const fetchPage = useCallback(
    async (q: DataTableQuery) => {
      if (!apiKey) return { items: [], total: 0 }
      const body = await getAgents(apiKey, { status: status === 'all' ? undefined : status, q: q.q, limit: q.limit, offset: q.offset })
      return { items: body.agents, total: body.total }
    },
    [apiKey, status],
  )

  const onRetire = async (a: AgentResponse) => {
    if (!apiKey) return
    if (!(await confirm({ title: `Retire ${a.name}?`, description: 'The gateway and SDK refuse its new requests. History is kept; you can reactivate it from Edit.', confirmLabel: 'Retire', destructive: true }))) return
    try {
      await retireAgent(apiKey, a.id)
      toast.success(`${a.name} retired`)
      setVersion((v) => v + 1)
    } catch (e) {
      toast.error(apiErrorMessage(e))
    }
  }

  const columns: DataTableColumn<AgentResponse>[] = [
    { key: 'name', header: 'Agent', render: (a) => <Link href={routes.agentsAgentId(a.id)} className="font-medium text-indigo-600 hover:underline dark:text-indigo-400">{a.name}</Link> },
    { key: 'agent_type', header: 'Type' },
    { key: 'default_model', header: 'Default model', render: (a) => a.default_model ?? '—' },
    { key: 'budget_envelope', header: 'Monthly envelope', value: (a) => (a.budget_envelope == null ? null : Number(a.budget_envelope)), render: (a) => (a.budget_envelope == null ? 'none' : money(a.budget_envelope)) },
    { key: 'allowed_aliases', header: 'Allowed aliases', value: (a) => a.allowed_aliases.join(' '), render: (a) => (a.allowed_aliases.length ? a.allowed_aliases.join(', ') : 'any') },
    { key: 'owner', header: 'Owner', render: (a) => a.owner ?? '—' },
    { key: 'status', header: 'Status', render: (a) => <StatusBadge status={a.status} /> },
    {
      key: 'actions',
      header: 'Actions',
      value: () => '',
      render: (a) =>
        canWrite ? (
          <div className="flex justify-end gap-1" onClick={(e) => e.stopPropagation()}>
            <button type="button" aria-label={`Edit ${a.name}`} onClick={() => { setEditing(a); setOpen(true) }} className="rounded-md p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"><Pencil className="h-3.5 w-3.5" /></button>
            {a.status !== 'retired' && (
              <button type="button" aria-label={`Retire ${a.name}`} onClick={() => void onRetire(a)} className="rounded-md p-1 text-slate-500 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/40"><Trash2 className="h-3.5 w-3.5" /></button>
            )}
          </div>
        ) : null,
    },
  ]

  return (
    <div className="space-y-4">
      {dialog}
      <PageHeader
        icon={BrainCircuit}
        title="Agents"
        description="Registered agents. Runs are attributed to an agent by name or id at ingest; each agent can carry a monthly budget envelope."
        actions={canWrite ? (
          <button type="button" onClick={() => { setEditing(null); setOpen(true) }} className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">
            <Plus className="h-4 w-4" aria-hidden="true" /> Register agent
          </button>
        ) : undefined}
      />
      <div role="group" aria-label="Status filter" className="flex gap-1">
        {['active', 'paused', 'retired', 'all'].map((s) => (
          <button key={s} type="button" aria-pressed={status === s} onClick={() => setStatus(s)}
            className={`rounded-md px-2.5 py-1 text-xs font-medium capitalize ${status === s ? 'bg-indigo-600 text-white' : 'border border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-300'}`}>
            {s}
          </button>
        ))}
      </div>
      <DataTable key={`${status}-${version}`} label="Agents" urlPrefix="ag_" columns={columns} rowKey={(a) => a.id} fetchPage={fetchPage}
        searchPlaceholder="Search agents…" csvFileName="agents.csv" emptyTitle="No agents" emptyDescription="Register an agent, then pass its name from the SDK (agent=…) or OTLP (gen_ai.agent.name)."
        onRowClick={(a) => router.push(routes.agentsAgentId(a.id))} />
      <AgentSheet open={open} onOpenChange={setOpen} agent={editing} onSaved={() => setVersion((v) => v + 1)} />
    </div>
  )
}

export default function AgentsPage() {
  return (
    <Suspense fallback={null}>
      <AgentsInner />
    </Suspense>
  )
}
