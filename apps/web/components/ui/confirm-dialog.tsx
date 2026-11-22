'use client'

import { useCallback, useRef, useState, type ReactNode } from 'react'
import * as DialogPrimitive from '@radix-ui/react-dialog'

export interface ConfirmOptions {
  title: string
  description?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  /** Red confirm button for deletes and other irreversible actions. */
  destructive?: boolean
}

/** Accessible confirmation dialog (replaces window.confirm). Controlled. */
export function ConfirmDialog({
  open,
  options,
  onResolve,
}: {
  open: boolean
  options: ConfirmOptions | null
  onResolve: (confirmed: boolean) => void
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={(o) => { if (!o) onResolve(false) }}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border border-slate-200 bg-white p-5 shadow-xl focus:outline-none dark:border-slate-700 dark:bg-slate-900">
          <DialogPrimitive.Title className="text-base font-semibold text-slate-900 dark:text-white">{options?.title}</DialogPrimitive.Title>
          {options?.description ? (
            <DialogPrimitive.Description className="mt-2 text-sm text-slate-600 dark:text-slate-300">{options.description}</DialogPrimitive.Description>
          ) : (
            <DialogPrimitive.Description className="sr-only">Confirm this action</DialogPrimitive.Description>
          )}
          <div className="mt-5 flex justify-end gap-2">
            <button type="button" onClick={() => onResolve(false)}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800">
              {options?.cancelLabel ?? 'Cancel'}
            </button>
            <button type="button" autoFocus onClick={() => onResolve(true)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium text-white ${options?.destructive ? 'bg-rose-600 hover:bg-rose-700' : 'bg-indigo-600 hover:bg-indigo-700'}`}>
              {options?.confirmLabel ?? 'Confirm'}
            </button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}

/**
 * Promise-based replacement for window.confirm:
 *
 *   const { confirm, dialog } = useConfirm()
 *   if (await confirm({ title: 'Delete route?', destructive: true })) { … }
 *   return <>{dialog}…</>
 */
export function useConfirm() {
  const [options, setOptions] = useState<ConfirmOptions | null>(null)
  const resolver = useRef<((value: boolean) => void) | null>(null)
  const confirm = useCallback((opts: ConfirmOptions) => {
    setOptions(opts)
    return new Promise<boolean>((resolve) => { resolver.current = resolve })
  }, [])
  const onResolve = useCallback((value: boolean) => {
    resolver.current?.(value)
    resolver.current = null
    setOptions(null)
  }, [])
  const dialog = <ConfirmDialog open={options !== null} options={options} onResolve={onResolve} />
  return { confirm, dialog }
}
