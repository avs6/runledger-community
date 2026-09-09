import { redirect } from 'next/navigation'

export default function PolicyDryRunPage() {
  redirect('/tool-registry?tab=dry-run')
}
