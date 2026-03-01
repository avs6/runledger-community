'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useCallback } from 'react'

const PRESETS = [
  { label: '24h', hours: 24 },
  { label: '7d', hours: 24 * 7 },
  { label: '30d', hours: 24 * 30 },
] as const

interface Props {
  currentPreset?: string
}

export default function TimeWindowPicker({ currentPreset }: Props) {
  const router = useRouter()
  const searchParams = useSearchParams()

  const setWindow = useCallback(
    (hours: number, label: string) => {
      const now = new Date()
      const from = new Date(now.getTime() - hours * 3_600_000)
      const params = new URLSearchParams(searchParams.toString())
      params.set('from', from.toISOString())
      params.set('to', now.toISOString())
      params.set('preset', label)
      router.push(`?${params.toString()}`)
    },
    [router, searchParams]
  )

  const active = currentPreset ?? '7d'

  return (
    <div className="flex gap-1 rounded-lg border border-gray-200 bg-gray-50 p-1 dark:border-gray-700 dark:bg-gray-800">
      {PRESETS.map(({ label, hours }) => (
        <button
          key={label}
          onClick={() => setWindow(hours, label)}
          className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
            active === label
              ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-gray-100'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
