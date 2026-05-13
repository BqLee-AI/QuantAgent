import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/approvals/')({
  beforeLoad: () => {
    // TODO: Capability check placeholder
    // if (!hasCapability('approvals:read')) throw redirect({ to: '/' })
  },
  component: ApprovalsPage,
})

/** Approval center — lists pending human-in-the-loop decisions. */
function ApprovalsPage() {
  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900">Approvals</h1>
      <p className="mt-2 text-sm text-gray-500">Approval center placeholder</p>
    </div>
  )
}
