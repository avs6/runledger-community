'use client'

import { useState } from 'react'
import { Palette, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { PageHeader } from '@/components/ui/page-header'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { AsyncCard, SectionError } from '@/components/ui/async-card'
import { EmptyState } from '@/components/ui/empty-state'
import { TimeRangePicker, rangeToWindow, type TimeRange } from '@/components/ui/time-range-picker'
import { CHART_SERIES } from '@/lib/tokens'

interface DemoRow {
  id: string
  route: string
  provider: string
  requests: number
  cost: number
}

const DEMO_ROWS: DemoRow[] = Array.from({ length: 42 }, (_, i) => ({
  id: `r${i + 1}`,
  route: ['support-bot', 'triage', 'summarize', 'extract', 'router'][i % 5] + `-${Math.floor(i / 5) + 1}`,
  provider: ['openai', 'anthropic', 'ollama'][i % 3],
  requests: (i * 137) % 1000,
  cost: Math.round(((i * 7919) % 5000) / 10) / 100,
}))

const COLUMNS: DataTableColumn<DemoRow>[] = [
  { key: 'route', header: 'Route', sortable: true },
  { key: 'provider', header: 'Provider', sortable: true },
  { key: 'requests', header: 'Requests', sortable: true, className: 'text-right' },
  { key: 'cost', header: 'Cost', sortable: true, render: (r) => `$${r.cost.toFixed(2)}`, className: 'text-right' },
  { key: 'id', header: 'ID', defaultHidden: true },
]

const TOKENS: { name: string; cls: string }[] = [
  { name: 'status-success', cls: 'bg-status-success' },
  { name: 'status-warning', cls: 'bg-status-warning' },
  { name: 'status-error', cls: 'bg-status-error' },
  { name: 'status-info', cls: 'bg-status-info' },
  { name: 'severity-high', cls: 'bg-severity-high' },
  { name: 'severity-critical', cls: 'bg-severity-critical' },
  { name: 'scope-workspace', cls: 'bg-scope-workspace' },
  { name: 'scope-api-key', cls: 'bg-scope-api-key' },
]

/** Live reference for the shared UI kit (components/ui) and design tokens. */
export default function DesignSystemPage() {
  const [range, setRange] = useState<TimeRange>('7d')
  const { confirm, dialog } = useConfirm()
  const [cardState, setCardState] = useState<'ready' | 'loading' | 'error' | 'empty'>('ready')

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8">
      {dialog}
      <PageHeader
        icon={Palette}
        title="Design System"
        description="The shared UI kit and design tokens every page should use."
        breadcrumbs={[{ label: 'Admin' }, { label: 'Design System' }]}
        actions={<TimeRangePicker value={range} onChange={setRange} />}
      />

      <AsyncCard title="Tokens" description="Tailwind classes backed by CSS variables; they follow light and dark mode.">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {TOKENS.map((t) => (
            <div key={t.name} className="flex items-center gap-2 rounded-lg border border-slate-200 p-2 text-xs dark:border-slate-700">
              <span className={`h-4 w-4 rounded ${t.cls}`} aria-hidden="true" />
              <code className="text-slate-700 dark:text-slate-200">{t.name}</code>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          Chart series (lib/tokens.ts):{' '}
          {CHART_SERIES.map((c) => <span key={c} className="mr-1 inline-block h-3 w-3 rounded-sm align-middle" style={{ backgroundColor: c }} />)}
        </p>
      </AsyncCard>

      <AsyncCard
        title="TimeRangePicker"
        description="Preset windows; rangeToWindow() gives the from/to the list endpoints take."
      >
        <code className="block break-all text-xs text-slate-700 dark:text-slate-200">{JSON.stringify(rangeToWindow(range))}</code>
      </AsyncCard>

      <AsyncCard
        title="AsyncCard"
        description="Loading, error with retry, empty and ready states for one section."
        loading={cardState === 'loading'}
        error={cardState === 'error' ? 'Couldn’t load this section.' : null}
        onRetry={() => setCardState('ready')}
        empty={cardState === 'empty'}
        emptyDescription="Nothing to show for this range."
        actions={
          <div className="flex gap-1">
            {(['ready', 'loading', 'error', 'empty'] as const).map((s) => (
              <button key={s} type="button" onClick={() => setCardState(s)}
                className={`rounded-md border px-2 py-0.5 text-[11px] ${cardState === s ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400' : 'border-slate-200 text-slate-500 dark:border-slate-700'}`}>
                {s}
              </button>
            ))}
          </div>
        }
      >
        <p className="text-sm text-slate-700 dark:text-slate-200">Section content renders here.</p>
      </AsyncCard>

      <AsyncCard title="ConfirmDialog" description="Promise-based useConfirm() replaces window.confirm.">
        <button
          type="button"
          onClick={async () => {
            const ok = await confirm({ title: 'Delete this route?', description: 'Traffic to the alias falls back to its other routes.', confirmLabel: 'Delete', destructive: true })
            toast(ok ? 'Confirmed' : 'Cancelled')
          }}
          className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 px-3 py-1.5 text-sm text-rose-600 hover:bg-rose-50 dark:border-rose-900/50 dark:hover:bg-rose-950/30"
        >
          <Trash2 className="h-4 w-4" /> Delete route…
        </button>
      </AsyncCard>

      <AsyncCard title="SectionError and EmptyState">
        <div className="space-y-3">
          <SectionError message="Couldn’t load recent requests." onRetry={() => toast('Retrying…')} />
          <EmptyState title="No routes yet" description="Add a route to send traffic through the gateway." compact />
        </div>
      </AsyncCard>

      <AsyncCard title="DataTable" description="Client mode here; pass fetchPage for server paging via X-Total-Count. Page, sort and search live in the URL.">
        <DataTable label="Demo routes" rows={DEMO_ROWS} columns={COLUMNS} rowKey={(r) => r.id} pageSize={10} urlPrefix="demo_" searchPlaceholder="Search routes…" />
      </AsyncCard>
    </div>
  )
}
