import { useContext } from "react";

import { AuthContext } from "./context";
import type { AuthContextValue } from "./models";

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);

  if (!value) {
    throw new Error("useAuth must be used within AuthProvider.");
  }

  return value;
}
