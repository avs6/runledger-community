/** Shared form state types and helpers for the Gateway page tabs and panels. */
import { num } from '@/lib/utils'
import type { GatewayRoutingGroupStrategy, RoutingPolicyType } from '@/types/api'

export const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500'

export function parseCsvTags(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export interface RouteEditState {
  id: string
  alias: string
  targetModel: string
  baseUrl: string
  apiKeyEnvVar: string
  routingGroupId: string
  priority: string
  region: string
  requiredTags: string
  excludedTags: string
  dailyCostLimitUsd: string
  monthlyCostLimitUsd: string
  perUserRpmLimit: string
  fallbackAliases: string
  contextWindowFallback: string
  contentPolicyFallback: string
  existingFallbackConfig: Record<string, unknown> | null
  mirrorAlias: string
  mirrorSamplePct: string
  routeConfigStr: string
  routingConfigStr: string
  piiRedactionEnabled: boolean
  semanticCacheEnabled: boolean
  contextCompilerEnabled: boolean
  intelligentRoutingEnabled: boolean
}

export interface RoutingGroupEditState {
  id: string
  alias: string
  name: string
  description: string
  matchTags: string
  defaultTags: string
  strategyType: GatewayRoutingGroupStrategy
  strategyConfigStr: string
  isActive: boolean
}

export interface RoutingPolicyEditState {
  id: string
  policyType: RoutingPolicyType
  configStr: string
  isActive: boolean
}

export interface PassThroughEditState {
  id: string
  pathPrefix: string
  upstreamBaseUrl: string
  authType: string
  authConfigStr: string
  timeoutMs: string
  rateLimitRpm: string
  costPerCallUsd: string
  headerConfigStr: string
  defaultQueryStr: string
  isActive: boolean
}

export interface CacheConfigEditState {
  id: string
  name: string
  isEnabled: boolean
  ttlSeconds: string
  maxEntries: string
  evictionPolicy: string
  similarityThreshold: string
  embeddingModel: string
  scopeModels: string
  configStr: string
}

export function pctStr(v: string | null): string {
  if (v == null) return '—'
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return `${n > 0 ? '↑' : '↓'}${Math.abs(num(n) * 100).toFixed(1)}%`
}
