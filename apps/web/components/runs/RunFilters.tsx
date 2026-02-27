'use client'

import { useRouter, usePathname, useSearchParams } from 'next/navigation'
import { useCallback } from 'react'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'

const TIME_PRESETS = [
  { label: 'Last 1h', value: '1h' },
  { label: 'Last 6h', value: '6h' },
  { label: 'Last 24h', value: '24h' },
  { label: 'Last 7d', value: '7d' },
]

function hoursAgoIso(hours: number) {
  return new Date(Date.now() - hours * 3_600_000).toISOString()
}

function presetToFrom(preset: string): string {
  if (preset === '1h') return hoursAgoIso(1)
  if (preset === '6h') return hoursAgoIso(6)
  if (preset === '24h') return hoursAgoIso(24)
  if (preset === '7d') return hoursAgoIso(24 * 7)
  return hoursAgoIso(24 * 7)
}

export default function RunFilters() {
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()

  const updateParam = useCallback(
    (key: string, value: string | null) => {
      const next = new URLSearchParams(params.toString())
      if (value) {
        next.set(key, value)
      } else {
        next.delete(key)
      }
      next.delete('cursor')
      router.push(`${pathname}?${next.toString()}`)
    },
    [params, pathname, router],
  )

  const status = params.get('status') ?? ''
  const search = params.get('search') ?? ''
  const preset = params.get('preset') ?? '7d'

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Input
        placeholder="Search run ID…"
        className="h-8 w-48 text-sm"
        defaultValue={search}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            updateParam('search', (e.target as HTMLInputElement).value || null)
          }
        }}
      />

      <Select
        value={status || '_all'}
        onValueChange={(v) => updateParam('status', v === '_all' ? null : v)}
      >
        <SelectTrigger className="h-8 w-36 text-sm">
          <SelectValue placeholder="All statuses" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="_all">All statuses</SelectItem>
          <SelectItem value="running">Running</SelectItem>
          <SelectItem value="succeeded">Succeeded</SelectItem>
          <SelectItem value="failed">Failed</SelectItem>
          <SelectItem value="cancelled">Cancelled</SelectItem>
        </SelectContent>
      </Select>

      <div className="flex gap-1">
        {TIME_PRESETS.map(({ label, value }) => (
          <Button
            key={value}
            variant={preset === value ? 'default' : 'outline'}
            size="sm"
            className="h-8 text-xs"
            onClick={() => {
              const next = new URLSearchParams(params.toString())
              next.set('preset', value)
              next.set('from', presetToFrom(value))
              next.delete('to')
              next.delete('cursor')
              router.push(`${pathname}?${next.toString()}`)
            }}
          >
            {label}
          </Button>
        ))}
      </div>
    </div>
  )
}
