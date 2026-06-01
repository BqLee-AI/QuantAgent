export function runtimeStatusColor(value: string): "danger" | "success" | "warning" {
  const normalized = value.toLowerCase();

  if (["succeeded", "success", "healthy", "ready", "connected"].includes(normalized)) {
    return "success";
  }

  if (["failed", "timeout", "critical", "unavailable", "cancelled"].includes(normalized)) {
    return "danger";
  }

  return "warning";
}

export function runtimeSeverityColor(value: string): "danger" | "success" | "warning" {
  const normalized = value.toLowerCase();

  if (normalized === "critical") {
    return "danger";
  }

  if (normalized === "info") {
    return "success";
  }

  return "warning";
}
