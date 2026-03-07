'use client'

import { useCallback } from 'react'
import { useRouter, usePathname, useSearchParams } from 'next/navigation'
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
  { label: '5m', value: '5m', minutes: 5 },
  { label: '15m', value: '15m', minutes: 15 },
  { label: '30m', value: '30m', minutes: 30 },
  { label: '1h', value: '1h', minutes: 60 },
  { label: '3h', value: '3h', minutes: 180 },
  { label: '6h', value: '6h', minutes: 360 },
  { label: '12h', value: '12h', minutes: 720 },
  { label: '24h', value: '24h', minutes: 1440 },
  { label: '7d', value: '7d', minutes: 60 * 24 * 7 },
  { label: '30d', value: '30d', minutes: 60 * 24 * 30 },
]

function minutesAgoIso(minutes: number): string {
  return new Date(Date.now() - minutes * 60_000).toISOString()
}

/** ISO string → datetime-local input value (YYYY-MM-DDTHH:MM:SS) in local tz */
function isoToLocal(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  )
}

export default function RunFilters() {
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()

  const updateParam = useCallback(
    (key: string, value: string | null) => {
      const next = new URLSearchParams(params.toString())
      if (value) next.set(key, value)
      else next.delete(key)
      next.delete('cursor')
      router.push(`${pathname}?${next.toString()}`)
    },
    [params, pathname, router],
  )

  const applyPreset = useCallback(
    (value: string, minutes: number) => {
      const next = new URLSearchParams(params.toString())
      next.set('preset', value)
      next.set('from', minutesAgoIso(minutes))
      next.delete('to')
      next.delete('cursor')
      router.push(`${pathname}?${next.toString()}`)
    },
    [params, pathname, router],
  )

  const switchToCustom = useCallback(() => {
    const next = new URLSearchParams(params.toString())
    next.set('preset', 'custom')
    if (!next.has('from')) next.set('from', minutesAgoIso(60 * 24 * 7))
    if (!next.has('to')) next.set('to', new Date().toISOString())
    next.delete('cursor')
    router.push(`${pathname}?${next.toString()}`)
  }, [params, pathname, router])

  const status = params.get('status') ?? ''
  const search = params.get('search') ?? ''
  const featureTag = params.get('feature_tag') ?? ''
  const endUser = params.get('end_user_id') ?? ''
  const model = params.get('model') ?? ''
  const minCost = params.get('min_cost') ?? ''
  const maxCost = params.get('max_cost') ?? ''
  const preset = params.get('preset') ?? '7d'
  const fromParam = params.get('from') ?? ''
  const toParam = params.get('to') ?? ''
  const isCustom = preset === 'custom'

  return (
    <div className="space-y-2">
      {/* Row 1: text + status filters */}
      <div className="flex flex-wrap items-center gap-2">
        <Input
          placeholder="Search run ID…"
          className="h-8 w-44 text-sm"
          defaultValue={search}
          onKeyDown={(e) => {
            if (e.key === 'Enter')
              updateParam('search', (e.target as HTMLInputElement).value || null)
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

        <Input
          placeholder="Feature tag…"
          className="h-8 w-36 text-sm"
          defaultValue={featureTag}
          onKeyDown={(e) => {
            if (e.key === 'Enter')
              updateParam('feature_tag', (e.target as HTMLInputElement).value || null)
          }}
        />

        <Input
          placeholder="End user ID…"
          className="h-8 w-36 text-sm"
          defaultValue={endUser}
          onKeyDown={(e) => {
            if (e.key === 'Enter')
              updateParam('end_user_id', (e.target as HTMLInputElement).value || null)
          }}
        />
      </div>

      {/* Row 2: model + cost range filters */}
      <div className="flex flex-wrap items-center gap-2">
        <Input
          placeholder="Model (e.g. gpt-4o)…"
          className="h-8 w-44 text-sm"
          defaultValue={model}
          onKeyDown={(e) => {
            if (e.key === 'Enter')
              updateParam('model', (e.target as HTMLInputElement).value || null)
          }}
        />

        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-400 dark:text-gray-500">Cost $</span>
          <Input
            type="number"
            placeholder="min"
            className="h-8 w-20 text-sm"
            defaultValue={minCost}
            step="0.000001"
            min="0"
            onKeyDown={(e) => {
              if (e.key === 'Enter')
                updateParam('min_cost', (e.target as HTMLInputElement).value || null)
            }}
            onBlur={(e) => updateParam('min_cost', e.target.value || null)}
          />
          <span className="text-xs text-gray-400 dark:text-gray-500">–</span>
          <Input
            type="number"
            placeholder="max"
            className="h-8 w-20 text-sm"
            defaultValue={maxCost}
            step="0.000001"
            min="0"
            onKeyDown={(e) => {
              if (e.key === 'Enter')
                updateParam('max_cost', (e.target as HTMLInputElement).value || null)
            }}
            onBlur={(e) => updateParam('max_cost', e.target.value || null)}
          />
        </div>
      </div>

      {/* Row 3: time presets + optional custom range */}
      <div className="flex flex-wrap items-center gap-1">
        {TIME_PRESETS.map(({ label, value, minutes }) => (
          <Button
            key={value}
            variant={preset === value ? 'default' : 'outline'}
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={() => applyPreset(value, minutes)}
          >
            {label}
          </Button>
        ))}

        <Button
          variant={isCustom ? 'default' : 'outline'}
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={switchToCustom}
        >
          Custom
        </Button>

        {isCustom && (
          <div className="ml-1 flex items-center gap-1">
            <span className="text-xs text-gray-400 dark:text-gray-500">from</span>
            <input
              type="datetime-local"
              step="1"
              className="h-7 rounded-md border border-gray-300 bg-white px-2 text-xs dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
              defaultValue={fromParam ? isoToLocal(fromParam) : ''}
              onBlur={(e) => {
                if (e.target.value) updateParam('from', new Date(e.target.value).toISOString())
              }}
            />
            <span className="text-xs text-gray-400 dark:text-gray-500">to</span>
            <input
              type="datetime-local"
              step="1"
              className="h-7 rounded-md border border-gray-300 bg-white px-2 text-xs dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
              defaultValue={toParam ? isoToLocal(toParam) : ''}
              onBlur={(e) => {
                if (e.target.value) updateParam('to', new Date(e.target.value).toISOString())
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}
