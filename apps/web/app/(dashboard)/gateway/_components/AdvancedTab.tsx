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
  } = useGateway()
  return (
  <div className="space-y-3">
  {apiKey && <BenchmarkPanel apiKey={apiKey} />}
  {apiKey && <PassThroughPanel apiKey={apiKey} canManage={canManage} />}
  {apiKey && <BudgetTierPanel apiKey={apiKey} canManage={canManage} />}
  {apiKey && <ModelQuotaPanel apiKey={apiKey} canManage={canManage} />}
  {apiKey && <FlywheelPanel apiKey={apiKey} canManage={canManage} />}
  </div>
  )
}
