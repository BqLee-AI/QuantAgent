import type { ApiError } from "@/shared/api";

import type {
  PluginErrorSummary,
  SectionAvailability,
  SectionAvailabilityState,
} from "../api/plugin-detail.contracts";

const availabilityLabels: Record<SectionAvailabilityState, string> = {
  degraded: "已降级",
  forbidden: "权限不足",
  not_collected: "尚未采集",
  not_configured: "未配置",
  ready: "可用",
  unavailable: "暂不可用",
};

export function formatAvailability(availability?: SectionAvailability | null): string {
  if (!availability) {
    return "未知";
  }
  const label = availabilityLabels[availability.state] ?? availability.state;
  return availability.message ? `${label}：${availability.message}` : label;
}

export function formatOptional(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }
  return JSON.stringify(value);
}

export function formatErrorSummary(error?: PluginErrorSummary | null): string {
  if (!error) {
    return "无";
  }
  return `${error.code} / ${error.stage}：${error.message}`;
}

export function formatApiError(error: unknown): string {
  const candidate = error as Partial<ApiError> | null;
  const requestId = candidate?.requestId ? ` request_id=${candidate.requestId}` : "";
  const status = candidate?.status ? `HTTP ${candidate.status}` : "请求失败";
  const message = candidate?.msg ?? (error instanceof Error ? error.message : "未知错误");
  return `${status}：${message}${requestId}`;
}

export function formatDateTime(value?: string | null): string {
  if (!value) {
    return "-";
  }
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return value;
  }
  return new Date(timestamp).toLocaleString();
}

export function formatRecordSummary(value: Record<string, unknown>): string {
  const entries = Object.entries(value);
  if (entries.length === 0) {
    return "-";
  }
  return entries.map(([key, item]) => `${key}: ${formatOptional(item)}`).join(" · ");
}

const pluginTypeLabels: Record<string, string> = {
  broker: "交易通道",
  industry: "行业包",
  notification: "通知",
  source: "数据源",
  strategy: "策略",
};

const pluginStatusLabels: Record<string, string> = {
  configured: "已配置",
  disabled: "已禁用",
  discovered: "已发现",
  enabled: "已启用",
  failed: "失败",
  invalid: "无效",
  loaded: "已加载",
  planned_only: "仅规划",
  started: "已启动",
  stopped: "已停止",
  valid: "有效",
};

const configStateLabels: Record<string, string> = {
  invalid: "配置无效",
  missing_required: "缺少必填项",
  not_configured: "未配置",
  unavailable: "暂不可用",
  valid: "配置有效",
};

const healthStatusLabels: Record<string, string> = {
  degraded: "已降级",
  failed: "失败",
  healthy: "健康",
  not_collected: "尚未采集",
  unavailable: "暂不可用",
};

const riskLevelLabels: Record<string, string> = {
  high: "高",
  low: "低",
  medium: "中",
};

const actionLabels: Record<string, string> = {
  disable: "停用",
  enable: "启用",
  reload: "重载",
  rescan: "重新扫描",
  uninstall: "卸载",
};

const keyLabels: Record<string, string> = {
  active_version: "运行版本",
  audit: "审计",
  blocked_reason: "阻塞原因",
  config: "配置",
  config_schema: "配置 Schema",
  config_state: "配置状态",
  dependencies: "依赖",
  dependency_blocker: "依赖阻塞",
  health: "健康",
  health_error: "健康错误",
  installed_version: "安装版本",
  last_actor: "最近操作者",
  last_changed_at: "最近变更时间",
  last_check_at: "最近检查时间",
  last_error: "最近错误",
  masked_sensitive: "敏感字段掩码",
  missing_dependencies: "缺失依赖",
  missing_required: "缺失必填项",
  operable_state: "可操作状态",
  ops_state: "操作状态",
  plugin_id: "插件 ID",
  reverse_dependencies: "反向依赖",
  runtime_errors: "运行错误",
};

const schemaSourceLabels: Record<string, string> = {
  "debug-mock": "调试样例",
  "registry-api": "插件注册表",
};

const pluginDescriptionLabels: Record<string, string> = {
  "quantagent.official.industry.example":
    "官方示例行业包，用于演示 source binding 的资源组织方式。",
  "quantagent.official.industry.semiconductor":
    "官方半导体行业包，内置 RSS 基线与行业观察样例。",
  "quantagent.official.notification.discord":
    "官方 Discord 通知插件试验版，提供低风险发送与接收能力。",
  "quantagent.official.source.placeholder":
    "最小可运行的数据源插件，用于验证插件基础链路。",
  "quantagent.official.source.readability":
    "读取单个网页链接并提取可读文章正文。",
  "quantagent.official.source.rss":
    "轮询 RSS/Atom 订阅源，并将条目标准化为 source item。",
  "quantagent.official.source.tavily":
    "基于 Tavily API 的证据型搜索与摘要提取工具。",
};

export function formatPluginType(value?: string | null): string {
  return value ? (pluginTypeLabels[value] ?? value) : "-";
}

export function formatPluginStatus(value?: string | null): string {
  return value ? (pluginStatusLabels[value] ?? value) : "-";
}

export function formatConfigState(value?: string | null): string {
  return value ? (configStateLabels[value] ?? value) : "-";
}

export function formatHealthStatus(value?: string | null): string {
  return value ? (healthStatusLabels[value] ?? value) : "-";
}

export function formatRiskLevel(value?: string | null): string {
  return value ? (riskLevelLabels[value] ?? value) : "-";
}

export function formatAction(value?: string | null): string {
  return value ? (actionLabels[value] ?? value) : "-";
}

export function formatYesNo(value: boolean): string {
  return value ? "是" : "否";
}

export function formatKeyLabel(value: string): string {
  return keyLabels[value] ?? value;
}

export function formatSchemaSource(value?: string | null): string {
  return value ? (schemaSourceLabels[value] ?? value) : "-";
}

export function formatPluginDescription(
  pluginId: string,
  description?: string | null,
): string {
  return (
    pluginDescriptionLabels[pluginId] ??
    description ??
    "manifest 暂不可用，详情页会展示受控失败态。"
  );
}
