import { redirect } from 'next/navigation'

export default function EvaluationsRedirectPage() {
  redirect('/evaluation?tab=scores')
}
