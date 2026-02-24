import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

interface HeaderActionsCtx {
  actions: ReactNode
  setActions: (node: ReactNode) => void
}

const HeaderActionsContext = createContext<HeaderActionsCtx>({
  actions: null,
  setActions: () => {},
})

export function HeaderActionsProvider({ children }: { children: ReactNode }) {
  const [actions, setActions] = useState<ReactNode>(null)
  return (
    <HeaderActionsContext.Provider value={{ actions, setActions }}>
      {children}
    </HeaderActionsContext.Provider>
  )
}

/** Used by Layout to render the slot */
export function useHeaderActionsSlot(): ReactNode {
  return useContext(HeaderActionsContext).actions
}

/** Used by pages to inject their actions into the header */
export function useHeaderActions(node: ReactNode, deps: unknown[]) {
  const { setActions } = useContext(HeaderActionsContext)
  useEffect(() => {
    setActions(node)
    return () => setActions(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}
