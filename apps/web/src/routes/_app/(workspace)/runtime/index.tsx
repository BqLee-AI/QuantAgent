import { createFileRoute } from '@tanstack/react-router'

import { RuntimeAuditPage } from '../../../../features/runtime'
import { toRuntimeAuditSearch } from '../../../../features/runtime'
import type { RuntimeAuditFilters } from '../../../../features/runtime'

type RuntimeSearch = Partial<RuntimeAuditFilters>

export const Route = createFileRoute('/_app/(workspace)/runtime/')({
  validateSearch: (search): RuntimeSearch => toRuntimeAuditSearch(search),
  component: RuntimePage,
})

function RuntimePage() {
  return <RuntimeAuditPage search={Route.useSearch()} />
}
