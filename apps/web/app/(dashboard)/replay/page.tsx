import { redirect } from 'next/navigation'

/** Replay Lab was merged into experiments (mode = "replay", review B-07). */
export default function ReplayRedirect() {
  redirect('/experiments?mode=replay')
}
