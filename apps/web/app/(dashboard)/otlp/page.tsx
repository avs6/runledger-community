import { redirect } from 'next/navigation'

export default function OtlpRedirectPage() {
  redirect('/monitoring/telemetry')
}
