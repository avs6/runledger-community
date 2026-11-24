import { redirect } from 'next/navigation'
import { routes } from '@/lib/routes'

/** Workflow runs are ordinary runs now (a view over agent_runs); keep old links working. */
export default function WorkflowRunRedirect({ params }: { params: { run_id: string } }) {
  redirect(routes.runsRunId(params.run_id))
}
