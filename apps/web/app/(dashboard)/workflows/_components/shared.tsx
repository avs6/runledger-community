'use client'

import { useState, type ReactNode } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Check, Copy } from 'lucide-react'
import { num } from '@/lib/utils'
import { createWorkflow, updateWorkflow } from '@/lib/api'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import type { WorkflowDefinitionResponse, WorkflowHealth, WorkflowInput } from '@/types/api'

export function useApiKey(): string | undefined {
  const { data: session } = useSession()
  return (session as Record<string, unknown> | null)?.apiKey as string | undefined
}

export function money(v: number | string | null | undefined): string {
  if (v === null || v === undefined) return '—'
  const n = num(v)
  if (n === 0) return '$0.00'
  if (n >= 1) return `$${n.toFixed(2)}`
  if (n >= 0.01) return `$${n.toFixed(3)}`
  return n < 0.0001 ? '<$0.0001' : `$${n.toFixed(4)}`
}

export function pct(v: number | null | undefined): string {
  return v === null || v === undefined ? '—' : `${(v * 100).toFixed(1)}%`
}

export function ms(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  return v < 1000 ? `${Math.round(v)} ms` : `${(v / 1000).toFixed(1)} s`
}

export function relTime(iso: string | null | undefined): string {
  if (!iso) return 'never'
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.round(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.round(m / 60)
  if (h < 48) return `${h}h ago`
  return `${Math.round(h / 24)}d ago`
}

const STATUS_CLS: Record<string, string> = {
  active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  succeeded: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  running: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  failed: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
  cancelled: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  paused: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  archived: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
  retired: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${STATUS_CLS[status] ?? STATUS_CLS.archived}`}>
      {status}
    </span>
  )
}

export const inputCls =
  'w-full rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100'

export const TAG_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,254}$/

export function slugify(name: string): string {
  return name.trim().toLowerCase().replace(/[^a-z0-9._:/-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 64)
}

function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="text-xs font-medium text-slate-700 dark:text-slate-200">{label}</label>
      {children}
      {hint && <p className="text-[11px] text-slate-500 dark:text-slate-400">{hint}</p>}
    </div>
  )
}

/** Name, tag, alias, owner and description for a workflow. Controlled. */
export function WorkflowFields({
  value,
  onChange,
  autoTag = false,
}: {
  value: WorkflowInput
  onChange: (next: WorkflowInput) => void
  autoTag?: boolean
}) {
  const tagInvalid = !!value.feature_tag && !TAG_PATTERN.test(value.feature_tag)
  return (
    <div className="space-y-3">
      <Field id="wf-name" label="Name">
        <input
          id="wf-name"
          required
          className={inputCls}
          value={value.name ?? ''}
          placeholder="Support triage"
          onChange={(e) => {
            const name = e.target.value
            const next: WorkflowInput = { ...value, name }
            if (autoTag && (!value.feature_tag || value.feature_tag === slugify(value.name ?? ''))) next.feature_tag = slugify(name)
            onChange(next)
          }}
        />
      </Field>
      <Field
        id="wf-tag"
        label="Feature tag"
        hint="Runs tagged with this (SDK, header, OTLP or gateway) belong to the workflow. Budgets on this tag are the workflow's budgets."
      >
        <input
          id="wf-tag"
          className={`${inputCls} font-mono ${tagInvalid ? 'border-rose-400 focus:ring-rose-500' : ''}`}
          value={value.feature_tag ?? ''}
          placeholder="support-triage"
          aria-invalid={tagInvalid}
          onChange={(e) => onChange({ ...value, feature_tag: e.target.value || null })}
        />
        {tagInvalid && <p role="alert" className="text-[11px] text-rose-600">Letters, digits and . _ : / - only; no spaces.</p>}
      </Field>
      <Field id="wf-alias" label="Gateway alias (optional)" hint="Requests to this route alias are attributed to the workflow. Must be an existing route.">
        <input
          id="wf-alias"
          className={`${inputCls} font-mono`}
          value={value.gateway_alias ?? ''}
          placeholder="smart"
          onChange={(e) => onChange({ ...value, gateway_alias: e.target.value || null })}
        />
      </Field>
      <Field id="wf-owner" label="Owner (optional)">
        <input id="wf-owner" className={inputCls} value={value.owner ?? ''} placeholder="support-eng" onChange={(e) => onChange({ ...value, owner: e.target.value || null })} />
      </Field>
      <Field id="wf-desc" label="Description (optional)">
        <textarea id="wf-desc" rows={2} className={inputCls} value={value.description ?? ''} onChange={(e) => onChange({ ...value, description: e.target.value || null })} />
      </Field>
    </div>
  )
}

export function isValidWorkflowInput(v: WorkflowInput): boolean {
  return !!v.name?.trim() && (!v.feature_tag || TAG_PATTERN.test(v.feature_tag))
}

/** Create (no `workflow`) or edit a workflow in a side sheet. */
export function WorkflowSheet({
  open,
  onOpenChange,
  workflow,
  onSaved,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  workflow?: WorkflowDefinitionResponse | null
  onSaved: (wf: WorkflowDefinitionResponse) => void
}) {
  const apiKey = useApiKey()
  const [value, setValue] = useState<WorkflowInput>(() => toInput(workflow))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastId, setLastId] = useState(workflow?.id)
  if (workflow?.id !== lastId) {
    setLastId(workflow?.id)
    setValue(toInput(workflow))
  }

  const save = async () => {
    if (!apiKey || !isValidWorkflowInput(value)) return
    setSaving(true)
    setError(null)
    try {
      const body = { ...value, name: value.name!.trim() }
      const saved = workflow ? await updateWorkflow(apiKey, workflow.id, body) : await createWorkflow(apiKey, body)
      toast.success(workflow ? 'Workflow saved' : 'Workflow created', {
        description: saved.linked_runs ? `${saved.linked_runs} existing runs linked` : undefined,
      })
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
          <SheetTitle>{workflow ? `Edit ${workflow.name}` : 'New workflow'}</SheetTitle>
          <SheetDescription>Link the workflow to the traffic it owns.</SheetDescription>
        </SheetHeader>
        <form
          className="mt-4 space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            void save()
          }}
        >
          <WorkflowFields value={value} onChange={setValue} autoTag={!workflow} />
          {error && <p role="alert" className="text-xs text-rose-600">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => onOpenChange(false)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm dark:border-slate-700">Cancel</button>
            <button type="submit" disabled={saving || !isValidWorkflowInput(value)} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
              {saving ? 'Saving…' : workflow ? 'Save' : 'Create'}
            </button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  )
}

function toInput(wf?: WorkflowDefinitionResponse | null): WorkflowInput {
  return {
    name: wf?.name ?? '',
    description: wf?.description ?? null,
    feature_tag: wf?.feature_tag ?? null,
    gateway_alias: wf?.gateway_alias ?? null,
    owner: wf?.owner ?? null,
  }
}

/** Pull the API's `detail` out of an apiFetch error ("API 409: {...}"). */
export function apiErrorMessage(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e)
  const m = msg.match(/^API \d+: ([\s\S]*)$/)
  if (m) {
    try {
      const detail = JSON.parse(m[1]).detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg).join('; ')
    } catch {
      return m[1]
    }
  }
  return msg
}

function Stat({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: 'good' | 'bad' }) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3 dark:border-slate-800 dark:bg-slate-800/40">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-lg font-bold text-slate-900 dark:text-white">{value}</p>
      {sub && <p className={`text-[11px] ${tone === 'good' ? 'text-status-success' : tone === 'bad' ? 'text-status-error' : 'text-slate-500 dark:text-slate-400'}`}>{sub}</p>}
    </div>
  )
}

/** Inline sparkline of one numeric series (no axis; the numbers sit next to it). */
function Spark({ values, label }: { values: Array<number | null>; label: string }) {
  const pts = values.map((v, i) => [i, v] as const).filter(([, v]) => v !== null) as Array<readonly [number, number]>
  if (pts.length < 2) return <p className="text-[11px] text-slate-400">Not enough data for a trend</p>
  const max = Math.max(...pts.map(([, v]) => v))
  const min = Math.min(...pts.map(([, v]) => v))
  const w = 160
  const h = 32
  const x = (i: number) => (i / Math.max(values.length - 1, 1)) * w
  const y = (v: number) => (max === min ? h / 2 : h - ((v - min) / (max - min)) * h)
  const d = pts.map(([i, v], k) => `${k ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  return (
    <svg role="img" aria-label={label} viewBox={`0 0 ${w} ${h}`} className="h-8 w-40 text-indigo-500">
      <path d={d} fill="none" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  )
}

/** The workflow health card: cost per success, p95 latency and eval score trend. */
export function HealthCard({ health }: { health: WorkflowHealth }) {
  const delta = health.eval_score_delta
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Stat label="Cost per success" value={money(health.cost_per_success)} sub={`${money(health.total_cost_usd)} total`} />
        <Stat label="p95 latency" value={ms(health.p95_latency_ms)} sub={`p50 ${ms(health.p50_latency_ms)}`} />
        <Stat
          label="Success rate"
          value={pct(health.success_rate)}
          sub={`${health.succeeded} ok · ${health.failed} failed of ${health.runs}`}
          tone={health.success_rate !== null && health.success_rate < 0.9 ? 'bad' : undefined}
        />
        <Stat
          label="Eval score"
          value={health.avg_eval_score === null ? '—' : health.avg_eval_score.toFixed(2)}
          sub={delta === null ? 'no scores yet' : `${delta >= 0 ? '▲' : '▼'} ${Math.abs(delta).toFixed(2)} vs first half`}
          tone={delta === null ? undefined : delta >= 0 ? 'good' : 'bad'}
        />
      </div>
      <div className="flex flex-wrap gap-6">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Daily cost</p>
          <Spark values={health.trend.map((p) => num(p.cost_usd))} label="Daily cost trend" />
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Eval score</p>
          <Spark values={health.trend.map((p) => p.avg_score)} label="Daily eval score trend" />
        </div>
      </div>
    </div>
  )
}

function CopyBlock({ code, label }: { code: string; label: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="relative">
      <button
        type="button"
        aria-label={`Copy ${label}`}
        onClick={() => {
          void navigator.clipboard?.writeText(code)
          setCopied(true)
          setTimeout(() => setCopied(false), 1500)
        }}
        className="absolute right-2 top-2 rounded-md bg-slate-800 p-1 text-slate-300 hover:text-white"
      >
        {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
      </button>
      <pre className="overflow-x-auto rounded-lg bg-slate-950 p-3 pr-9 font-mono text-[11px] leading-relaxed text-emerald-300">{code}</pre>
    </div>
  )
}

/** How to send traffic for a workflow: SDK decorator, header, OTLP attribute, gateway alias. */
export function ConnectSnippets({ workflow }: { workflow: Pick<WorkflowDefinitionResponse, 'name' | 'feature_tag' | 'gateway_alias'> }) {
  const ref = workflow.feature_tag || workflow.name
  const [tab, setTab] = useState<'python' | 'ts' | 'http' | 'otlp' | 'gateway'>('python')
  const snippets: Record<typeof tab, { label: string; code: string }> = {
    python: {
      label: 'Python SDK',
      code: `from runledger_sdk import RunLedger\n\nrl = RunLedger.from_env()\n\n@rl.workflow("${ref}")\ndef handle(ticket):\n    ...  # model calls in here are attributed to the workflow`,
    },
    ts: {
      label: 'TypeScript SDK',
      code: `import { RunLedger } from '@runledger/sdk'\n\nconst rl = RunLedger.fromEnv()\nawait rl.withWorkflow('${ref}', async (task) => {\n  // model calls in here are attributed to the workflow\n})`,
    },
    http: {
      label: 'Ingest header',
      code: `curl -X POST $RUNLEDGER_URL/ingest/v1/batch \\\n  -H "Authorization: Bearer $RUNLEDGER_API_KEY" \\\n  -H "X-RunLedger-Workflow: ${ref}" \\\n  -d @events.json`,
    },
    otlp: {
      label: 'OpenTelemetry',
      code: `# span or resource attribute\nrunledger.workflow = "${ref}"\n# or, per service, on the exporter:\nOTEL_EXPORTER_OTLP_HEADERS="X-RunLedger-Workflow=${ref}"`,
    },
    gateway: {
      label: 'Gateway',
      code: workflow.gateway_alias
        ? `# every request to the "${workflow.gateway_alias}" alias belongs to this workflow\nclient.chat.completions.create(model="${workflow.gateway_alias}", ...)`
        : `# tag gateway requests with the workflow's feature tag\nclient.chat.completions.create(\n    model="smart",\n    extra_body={"metadata": {"feature_tag": "${ref}"}},\n)`,
    },
  }
  return (
    <div className="space-y-2">
      <div role="tablist" aria-label="Connection method" className="flex flex-wrap gap-1">
        {(Object.keys(snippets) as Array<typeof tab>).map((k) => (
          <button
            key={k}
            role="tab"
            type="button"
            aria-selected={tab === k}
            onClick={() => setTab(k)}
            className={`rounded-md px-2.5 py-1 text-xs font-medium ${tab === k ? 'bg-indigo-600 text-white' : 'border border-slate-200 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800'}`}
          >
            {snippets[k].label}
          </button>
        ))}
      </div>
      <CopyBlock code={snippets[tab].code} label={`${snippets[tab].label} snippet`} />
    </div>
  )
}
