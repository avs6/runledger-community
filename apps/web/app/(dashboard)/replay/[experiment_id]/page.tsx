import { redirect } from 'next/navigation'

/** Replay Lab was merged into experiments (mode = "replay", review B-07). */
export default function ReplayExperimentRedirect({ params }: { params: { experiment_id: string } }) {
  redirect(`/experiments/${encodeURIComponent(params.experiment_id)}`)
}
