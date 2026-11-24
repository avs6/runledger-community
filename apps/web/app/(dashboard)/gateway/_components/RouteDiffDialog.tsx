'use client'

import * as DialogPrimitive from '@radix-ui/react-dialog'
import { AlertTriangle } from 'lucide-react'
import { useGateway } from './useGatewayState'

function show(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

/** Review a route change before it is saved (ENH): the server-computed field diff. */
export function RouteDiffDialog() {
  const { routeDiff, confirmRouteDiff, cancelRouteDiff, savingRouteEdit } = useGateway()
  return (
    <DialogPrimitive.Root open={routeDiff !== null} onOpenChange={(open) => { if (!open) cancelRouteDiff() }}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40" />
        <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-slate-200 bg-white p-5 shadow-xl focus:outline-none dark:border-slate-700 dark:bg-slate-900">
          <DialogPrimitive.Title className="text-base font-semibold text-slate-900 dark:text-white">Review route change</DialogPrimitive.Title>
          <DialogPrimitive.Description className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            These fields change on the next request after you save. Config keys you didn&apos;t edit are kept.
          </DialogPrimitive.Description>
          {routeDiff && routeDiff.warnings.length > 0 && (
            <ul className="mt-3 space-y-1 rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
              {routeDiff.warnings.map((w) => (
                <li key={w} className="flex gap-1.5"><AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />{w}</li>
              ))}
            </ul>
          )}
          <table className="mt-3 w-full text-left text-xs" aria-label="Changed route fields">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-700">
                <th scope="col" className="py-1.5 pr-2 font-medium">Field</th>
                <th scope="col" className="py-1.5 pr-2 font-medium">Before</th>
                <th scope="col" className="py-1.5 font-medium">After</th>
              </tr>
            </thead>
            <tbody>
              {routeDiff?.changes.map((c) => (
                <tr key={c.field} className="border-b border-slate-100 align-top dark:border-slate-800">
                  <td className="py-1.5 pr-2 font-mono text-slate-700 dark:text-slate-200">{c.field}</td>
                  <td className="py-1.5 pr-2"><pre className="whitespace-pre-wrap break-all font-mono text-status-error line-through decoration-1">{show(c.before)}</pre></td>
                  <td className="py-1.5"><pre className="whitespace-pre-wrap break-all font-mono text-status-success">{show(c.after)}</pre></td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-5 flex justify-end gap-2">
            <button type="button" onClick={cancelRouteDiff} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800">
              Back to edit
            </button>
            <button type="button" autoFocus disabled={savingRouteEdit} onClick={() => void confirmRouteDiff()} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
              {savingRouteEdit ? 'Saving…' : 'Save change'}
            </button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}
