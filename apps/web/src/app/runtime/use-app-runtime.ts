import { useContext } from "react";

import { AppRuntimeContext } from "./runtime.context";
import type { RuntimeApis } from "./runtime.types";

export function useAppRuntime() {
  const value = useContext(AppRuntimeContext);

  if (!value) {
    throw new Error("useAppRuntime must be used within AppRuntimeProvider.");
  }

  return value;
}

export function useApis(): RuntimeApis {
  return useAppRuntime().apis;
}
