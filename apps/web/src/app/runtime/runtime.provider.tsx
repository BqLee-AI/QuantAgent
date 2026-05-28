import { useMemo, type PropsWithChildren } from "react";

import type { RuntimeConfig } from "@/shared/config";

import { AppRuntimeContext } from "./runtime.context";
import { createAppRuntime } from "./runtime.factory";
import type { AuthRuntimeBridge } from "./runtime.types";

export interface AppRuntimeProviderProps extends PropsWithChildren {
  auth: AuthRuntimeBridge;
  config: RuntimeConfig;
}

export function AppRuntimeProvider({
  auth,
  children,
  config,
}: AppRuntimeProviderProps) {
  const runtime = useMemo(
    () => createAppRuntime({ auth, config }),
    [auth, config],
  );

  return (
    <AppRuntimeContext.Provider value={runtime}>
      {children}
    </AppRuntimeContext.Provider>
  );
}
