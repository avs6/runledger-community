import type { AnalyticsSummary } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingDown, TrendingUp } from 'lucide-react'

function fmt$$(value: string): string {
  const n = parseFloat(value)
  if (n >= 1) return `$${n.toFixed(2)}`
  if (n >= 0.001) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

function DeltaBadge({ pct }: { pct: string | null }) {
  if (pct === null) return null
  const n = parseFloat(pct)
  const up = n >= 0
  return (
    <span
      className={`flex items-center gap-0.5 text-xs font-medium ${
        up ? 'text-red-600' : 'text-green-600'
      }`}
    >
      {up ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
      {up ? '+' : ''}
      {n.toFixed(1)}% vs prior period
    </span>
  )
}

interface Props {
  summary: AnalyticsSummary
}

export default function SummaryCards({ summary }: Props) {
  const totalTokens = summary.total_input_tokens + summary.total_output_tokens
  const avgCostPerRun =
    summary.run_count > 0
      ? fmt$$(String(parseFloat(summary.total_cost_usd) / summary.run_count))
      : '$0.000000'

  const cards = [
    {
      title: 'Total Spend',
      value: fmt$$(summary.total_cost_usd),
      delta: summary.cost_delta_pct,
    },
    {
      title: 'Agent Runs',
      value: summary.run_count.toLocaleString(),
      delta: null,
    },
    {
      title: 'Avg Cost / Run',
      value: avgCostPerRun,
      delta: null,
    },
    {
      title: 'Total Tokens',
      value: fmtTokens(totalTokens),
      delta: null,
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {card.title}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tracking-tight">{card.value}</p>
            <DeltaBadge pct={card.delta} />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
