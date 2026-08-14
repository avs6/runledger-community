import { redirect } from 'next/navigation'

export default function BillingSummaryRedirect() {
  redirect('/billing?tab=summary&months=6')
}
