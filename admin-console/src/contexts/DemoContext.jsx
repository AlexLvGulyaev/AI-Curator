import { createContext, useContext, useMemo } from 'react';

const DemoContext = createContext({ isDemo: false });

export function DemoProvider({ isDemo, children }) {
  const value = useMemo(() => ({ isDemo: Boolean(isDemo) }), [isDemo]);
  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

export function useDemo() {
  return useContext(DemoContext);
}

export default DemoContext;
