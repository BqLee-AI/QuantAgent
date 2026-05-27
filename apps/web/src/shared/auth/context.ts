import { createContext } from "react";

import type { AuthContextValue } from "./models";

export const AuthContext = createContext<AuthContextValue | null>(null);
