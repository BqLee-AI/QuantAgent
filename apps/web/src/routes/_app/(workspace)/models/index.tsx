import { createFileRoute } from '@tanstack/react-router'

import { ModelsPage } from '../../../../features/models/components/ModelsPage'

export const Route = createFileRoute('/_app/(workspace)/models/')({
  component: ModelsPage,
})
