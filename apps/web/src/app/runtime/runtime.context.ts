import { createContext } from "react";

import type { AppRuntime } from "./runtime.types";

export const AppRuntimeContext = createContext<AppRuntime | null>(null);
