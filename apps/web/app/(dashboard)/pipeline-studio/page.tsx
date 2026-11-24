import { redirect } from 'next/navigation'

/** Pipeline Studio was merged into the Pipeline page (review B-26). */
export default function PipelineStudioRedirect() {
  redirect('/pipeline')
}
