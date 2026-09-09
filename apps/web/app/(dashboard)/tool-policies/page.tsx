import { redirect } from 'next/navigation'

export default function ToolPoliciesPage() {
  redirect('/tool-registry?tab=policies')
}
