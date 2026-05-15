import { createContext, useContext, type PropsWithChildren } from 'react';
import type { RuntimeConfig } from './runtime';

const RuntimeConfigContext = createContext<RuntimeConfig | null>(null);

export function RuntimeConfigProvider({
  children,
  value,
}: PropsWithChildren<{ value: RuntimeConfig }>) {
  return (
    <RuntimeConfigContext.Provider value={value}>
      {children}
    </RuntimeConfigContext.Provider>
  );
}

export function useRuntimeConfig(): RuntimeConfig {
  const value = useContext(RuntimeConfigContext);

  if (!value) {
    throw new Error('RuntimeConfigProvider is missing from the app bootstrap.');
  }

  return value;
}
