import { redirect } from 'next/navigation'

export default function OptimizationSimulatorRedirect() {
  redirect('/optimization-opportunities?tab=simulator')
}
