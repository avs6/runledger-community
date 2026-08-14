import { redirect } from 'next/navigation'

export default function PolicyDryRunPage() {
  redirect('/tool-policies?tab=dry-run')
}
