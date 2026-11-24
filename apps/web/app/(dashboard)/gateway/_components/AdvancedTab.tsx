'use client'

import { BenchmarkPanel } from './BenchmarkPanel'
import { PassThroughPanel } from './PassThroughPanel'
import { BudgetTierPanel } from './BudgetTierPanel'
import { ModelQuotaPanel } from './ModelQuotaPanel'
import { FlywheelPanel } from './FlywheelPanel'
import { useGateway } from './useGatewayState'

export function AdvancedTab() {
  const {
    apiKey,
    canManage,
    can,
  } = useGateway()
  return (
  <div className="space-y-3">
  {apiKey && <BenchmarkPanel apiKey={apiKey} />}
  {apiKey && <PassThroughPanel apiKey={apiKey} canManage={canManage} />}
  {apiKey && <BudgetTierPanel apiKey={apiKey} canManage={can('budget_tiers', 'write')} />}
  {apiKey && <ModelQuotaPanel apiKey={apiKey} canManage={canManage} />}
  {apiKey && <FlywheelPanel apiKey={apiKey} canApply={can('flywheel', 'apply')} canWrite={can('flywheel', 'write')} />}
  </div>
  )
}
