'use client'

import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { X } from 'lucide-react'
import { createAgent, listGatewayRoutes, updateAgent } from '@/lib/api'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import type { AgentResponse } from '@/types/api'
import { apiErrorMessage, inputCls, useApiKey } from '../../workflows/_components/shared'

const TYPES = [
  ['autonomous', 'Autonomous'],
  ['semi_autonomous', 'Semi-autonomous'],
  ['workflow', 'Workflow step'],
  ['chat', 'Chat'],
] as const

interface Form {
  name: string
  description: string
  agent_type: string
  owner: string
  default_model: string
  budget_envelope: string
  status: string
  allowed_aliases: string[]
}

function toForm(a?: AgentResponse | null): Form {
  return {
    name: a?.name ?? '',
    description: a?.description ?? '',
    agent_type: a?.agent_type ?? 'autonomous',
    owner: a?.owner ?? '',
    default_model: a?.default_model ?? '',
    budget_envelope: a?.budget_envelope != null ? String(a.budget_envelope) : '',
    status: a?.status ?? 'active',
    allowed_aliases: a?.allowed_aliases ?? [],
  }
}

/** Register (no `agent`) or edit an agent. */
export function AgentSheet({
  open,
  onOpenChange,
  agent,
  onSaved,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  agent?: AgentResponse | null
  onSaved: (a: AgentResponse) => void
}) {
  const apiKey = useApiKey()
  const [form, setForm] = useState<Form>(() => toForm(agent))
  const [lastId, setLastId] = useState(agent?.id)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (agent?.id !== lastId) {
    setLastId(agent?.id)
    setForm(toForm(agent))
  }
  const [aliases, setAliases] = useState<string[]>([])
  useEffect(() => {
    if (!open || !apiKey) return
    listGatewayRoutes(apiKey)
      .then((r) => setAliases(Array.from(new Set(r.items.map((x) => x.alias))).sort()))
      .catch(() => setAliases([]))
  }, [open, apiKey])
  const addAlias = (alias: string) => {
    if (alias && !form.allowed_aliases.includes(alias)) setForm({ ...form, allowed_aliases: [...form.allowed_aliases, alias] })
  }
  const envelopeInvalid = form.budget_envelope !== '' && !(Number(form.budget_envelope) >= 0)
  const set = (k: keyof Form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })

  const save = async () => {
    if (!apiKey || !form.name.trim() || envelopeInvalid) return
    setSaving(true)
    setError(null)
    const body = {
      name: form.name.trim(),
      description: form.description || null,
      agent_type: form.agent_type,
      owner: form.owner || null,
      default_model: form.default_model || null,
      budget_envelope: form.budget_envelope === '' ? null : Number(form.budget_envelope),
      status: form.status,
      allowed_aliases: form.allowed_aliases,
    }
    try {
      const saved = agent ? await updateAgent(apiKey, agent.id, body) : await createAgent(apiKey, body)
      toast.success(agent ? 'Agent saved' : 'Agent registered')
      onSaved(saved)
      onOpenChange(false)
    } catch (e) {
      setError(apiErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{agent ? `Edit ${agent.name}` : 'Register agent'}</SheetTitle>
          <SheetDescription>Runs that name this agent (SDK agent=…, OTLP gen_ai.agent.name) are attributed to it.</SheetDescription>
        </SheetHeader>
        <form className="mt-4 space-y-3" onSubmit={(e) => { e.preventDefault(); void save() }}>
          <div className="space-y-1">
            <label htmlFor="ag-name" className="text-xs font-medium">Name</label>
            <input id="ag-name" required className={inputCls} value={form.name} onChange={set('name')} placeholder="triage-bot" />
            <p className="text-[11px] text-slate-500">Must match the agent name your code sends.</p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label htmlFor="ag-type" className="text-xs font-medium">Type</label>
              <select id="ag-type" className={inputCls} value={form.agent_type} onChange={set('agent_type')}>
                {TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label htmlFor="ag-status" className="text-xs font-medium">Status</label>
              <select id="ag-status" className={inputCls} value={form.status} onChange={set('status')}>
                <option value="active">active</option>
                <option value="paused">paused</option>
                <option value="retired">retired</option>
              </select>
            </div>
          </div>
          <div className="space-y-1">
            <label htmlFor="ag-env" className="text-xs font-medium">Monthly budget envelope (USD)</label>
            <input id="ag-env" inputMode="decimal" aria-invalid={envelopeInvalid} className={inputCls} value={form.budget_envelope} onChange={set('budget_envelope')} placeholder="no limit" />
            <p className="text-[11px] text-slate-500">When the month&apos;s attributed spend reaches this, the gateway refuses the agent&apos;s requests (429) and the SDK refuses to start its runs. Paused and retired agents are refused too (403).</p>
          </div>
          <div className="space-y-1">
            <label htmlFor="ag-aliases" className="text-xs font-medium">Allowed gateway aliases</label>
            <div className="flex flex-wrap gap-1" aria-live="polite">
              {form.allowed_aliases.length === 0 && <span className="text-[11px] text-slate-500">Any alias</span>}
              {form.allowed_aliases.map((a) => (
                <span key={a} className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2 py-0.5 font-mono text-[11px] text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
                  {a}
                  <button type="button" aria-label={`Remove alias ${a}`} onClick={() => setForm({ ...form, allowed_aliases: form.allowed_aliases.filter((x) => x !== a) })}>
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
            <select id="ag-aliases" className={inputCls} value="" onChange={(e) => addAlias(e.target.value)}>
              <option value="">Add an alias…</option>
              {aliases.filter((a) => !form.allowed_aliases.includes(a)).map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
            <p className="text-[11px] text-slate-500">The gateway refuses this agent&apos;s requests to any other alias (403). Leave empty to allow all.</p>
          </div>
          <div className="space-y-1">
            <label htmlFor="ag-model" className="text-xs font-medium">Default model</label>
            <input id="ag-model" className={inputCls} value={form.default_model} onChange={set('default_model')} placeholder="smart" />
          </div>
          <div className="space-y-1">
            <label htmlFor="ag-owner" className="text-xs font-medium">Owner</label>
            <input id="ag-owner" className={inputCls} value={form.owner} onChange={set('owner')} />
          </div>
          <div className="space-y-1">
            <label htmlFor="ag-desc" className="text-xs font-medium">Description</label>
            <textarea id="ag-desc" rows={2} className={inputCls} value={form.description} onChange={set('description')} />
          </div>
          {error && <p role="alert" className="text-xs text-rose-600">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => onOpenChange(false)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm dark:border-slate-700">Cancel</button>
            <button type="submit" disabled={saving || !form.name.trim() || envelopeInvalid} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
              {saving ? 'Saving…' : agent ? 'Save' : 'Register'}
            </button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  )
}
