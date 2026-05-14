import { Button } from '@heroui/react/button'
import type { ReactNode } from 'react'

type ButtonWithChildrenProps = Parameters<typeof Button>[0] & {
  children?: ReactNode
}

const ButtonWithChildren = Button as (props: ButtonWithChildrenProps) => ReactNode

export default function App() {
  return <ButtonWithChildren>QuantAgent</ButtonWithChildren>
}
