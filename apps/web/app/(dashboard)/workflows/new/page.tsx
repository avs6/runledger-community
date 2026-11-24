'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { CheckCircle2, Loader2, Sparkles } from 'lucide-react'
import { PageHeader } from '@/components/ui/page-header'
import { createWorkflow, getWorkflowOverview } from '@/lib/api'
import { routes } from '@/lib/routes'
import type { WorkflowDefinitionResponse, WorkflowInput } from '@/types/api'
import {
  ConnectSnippets,
  WorkflowFields,
  apiErrorMessage,
  isValidWorkflowInput,
  money,
  useApiKey,
} from '../_components/shared'

const STEPS = ['Name it', 'Send traffic', 'See it arrive'] as const

/**
 * "First workflow" onboarding: define the workflow, copy one snippet for the way the
 * team sends traffic, then wait for the first attributed run (polled every 5 s).
 */
export default function NewWorkflowWizard() {
  const apiKey = useApiKey()
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [value, setValue] = useState<WorkflowInput>({ name: '', feature_tag: null })
  const [workflow, setWorkflow] = useState<WorkflowDefinitionResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [firstRuns, setFirstRuns] = useState<{ runs: number; cost: string | number } | null>(null)

  useEffect(() => {
    if (step !== 2 || !workflow || !apiKey) return
    let stop = false
    const poll = async () => {
      try {
        const ov = await getWorkflowOverview(apiKey, workflow.id, 1)
        if (!stop && ov.health.runs > 0) setFirstRuns({ runs: ov.health.runs, cost: ov.health.total_cost_usd })
      } catch {
        // keep polling; the API may be briefly unavailable
      }
    }
    void poll()
    const t = setInterval(() => void poll(), 5000)
    return () => {
      stop = true
      clearInterval(t)
    }
  }, [step, workflow, apiKey])

  const create = async () => {
    if (!apiKey || !isValidWorkflowInput(value)) return
    setSaving(true)
    setError(null)
    try {
      const wf = await createWorkflow(apiKey, { ...value, name: value.name!.trim() })
      setWorkflow(wf)
      if (wf.linked_runs) setFirstRuns({ runs: wf.linked_runs, cost: 0 })
      setStep(1)
    } catch (e) {
      setError(apiErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <PageHeader
        icon={Sparkles}
        title="Set up a workflow"
        description="Three steps: name the work, send its traffic, watch the first run land."
        breadcrumbs={[{ label: 'Workflows', href: '/workflows' }, { label: 'New' }]}
      />

      <ol aria-label="Setup progress" className="flex gap-2">
        {STEPS.map((label, i) => (
          <li key={label} aria-current={i === step ? 'step' : undefined}
            className={`flex flex-1 items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium ${
              i === step ? 'border-indigo-500 text-indigo-700 dark:text-indigo-300' : i < step ? 'border-emerald-300 text-emerald-700 dark:text-emerald-300' : 'border-slate-200 text-slate-400 dark:border-slate-700'
            }`}>
            {i < step ? <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> : <span aria-hidden="true">{i + 1}</span>}
            {label}
          </li>
        ))}
      </ol>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        {step === 0 && (
          <form onSubmit={(e) => { e.preventDefault(); void create() }} className="space-y-4">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              A workflow is one piece of AI work, like a support bot or a nightly summarizer. Its feature tag is how traffic finds it,
              and how budgets, chargeback and analytics group it.
            </p>
            <WorkflowFields value={value} onChange={setValue} autoTag />
            {error && <p role="alert" className="text-xs text-rose-600">{error}</p>}
            <div className="flex justify-end">
              <button type="submit" disabled={saving || !isValidWorkflowInput(value)} className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                {saving ? 'Creating…' : 'Create workflow'}
              </button>
            </div>
          </form>
        )}

        {step === 1 && workflow && (
          <div className="space-y-4">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              <strong>{workflow.name}</strong> is ready. Pick how this work reaches RunLedger and add one line; runs are attributed
              as they arrive.
            </p>
            <ConnectSnippets workflow={workflow} />
            {firstRuns && <p className="text-xs text-status-success">{firstRuns.runs} existing runs with this tag were already linked.</p>}
            <div className="flex justify-between">
              <Link href={routes.workflowsWorkflowId(workflow.id)} className="text-sm text-slate-500 hover:underline">Skip to the workflow</Link>
              <button type="button" onClick={() => setStep(2)} className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">I&apos;ve sent traffic</button>
            </div>
          </div>
        )}

        {step === 2 && workflow && (
          <div className="space-y-4 text-center" aria-live="polite">
            {firstRuns ? (
              <>
                <CheckCircle2 className="mx-auto h-10 w-10 text-status-success" aria-hidden="true" />
                <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                  {firstRuns.runs} run{firstRuns.runs === 1 ? '' : 's'} attributed{Number(firstRuns.cost) ? `, ${money(firstRuns.cost)} so far` : ''}.
                </p>
                <p className="text-xs text-slate-500">Next: add a budget on the tag and an evaluator, and the health card fills in.</p>
                <button type="button" onClick={() => router.push(routes.workflowsWorkflowId(workflow.id))} className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">
                  Open {workflow.name}
                </button>
              </>
            ) : (
              <>
                <Loader2 className="mx-auto h-8 w-8 animate-spin text-indigo-500" aria-hidden="true" />
                <p className="text-sm text-slate-700 dark:text-slate-200">Waiting for the first run tagged <code>{workflow.feature_tag || workflow.name}</code>…</p>
                <p className="text-xs text-slate-500">Runs show up a few seconds after the pipeline processes them. This checks every 5 seconds.</p>
                <button type="button" onClick={() => setStep(1)} className="text-xs text-indigo-600 hover:underline">Back to the snippets</button>
              </>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
