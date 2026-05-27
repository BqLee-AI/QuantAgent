import type { InternalRequestConfig } from "./types";

export function getDedupeKey(config: InternalRequestConfig): string | undefined {
  if (config.signal || config.dedupeKey === false) {
    return undefined;
  }

  if (typeof config.dedupeKey === "string" && config.dedupeKey.length > 0) {
    return config.dedupeKey;
  }

  const method = config.method?.toLowerCase();

  if (method !== "get" && method !== "head") {
    return undefined;
  }

  const params =
    config.params && typeof config.params === "object"
      ? JSON.stringify(config.params)
      : "";
  const responseMode = config._returnEnvelope ? "envelope" : "data";

  return `${method}:${config.baseURL ?? ""}:${config.url ?? ""}:${params}:${responseMode}`;
}
