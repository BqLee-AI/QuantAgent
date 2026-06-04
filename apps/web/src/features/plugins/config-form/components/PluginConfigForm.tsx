import { useEffect, useMemo, useRef, useState } from "react";
import { Fieldset, Form, Tabs } from "@heroui/react";

import {
  parseConfigDraftPayload,
  PluginConfigJsonFieldParseError,
} from "../utils/plugin-config-draft";
import type {
  PluginConfigFieldDefinition,
  PluginConfigSchemaSnapshot,
} from "../types/plugin-config.types";
import { PluginConfigField } from "./PluginConfigField";
import { PluginConfigSupportMatrix } from "./PluginConfigSupportMatrix";

type PluginConfigFormProps = {
  issueLookup: Map<string, string>;
  onValueChange: (path: string, nextValue: string) => void;
  schema: PluginConfigSchemaSnapshot;
  showSupportMatrix?: boolean;
  values: Record<string, string>;
};

export function PluginConfigForm({
  issueLookup,
  onValueChange,
  schema,
  showSupportMatrix = true,
  values,
}: PluginConfigFormProps) {
  const formViewportRef = useRef<HTMLDivElement | null>(null);
  const fieldGroups = useMemo(
    () => groupFields(schema.fields),
    [schema.fields],
  );
  const defaultSelectedGroupKey = fieldGroups[0]?.key ?? null;
  const [selectedGroupKey, setSelectedGroupKey] = useState<string | null>(
    defaultSelectedGroupKey,
  );
  const [isCompactLayout, setIsCompactLayout] = useState(false);
  const selectedGroup =
    fieldGroups.find((group) => group.key === selectedGroupKey) ??
    fieldGroups[0] ??
    null;

  useEffect(() => {
    setSelectedGroupKey(defaultSelectedGroupKey);
  }, [schema.pluginId, fieldGroups, defaultSelectedGroupKey]);

  useEffect(() => {
    const viewport = formViewportRef.current;

    if (!viewport || typeof ResizeObserver === "undefined") {
      return;
    }

    // 只在跨过紧凑布局阈值时触发 React 更新，避免抽屉拖拽时整棵表单逐帧重渲染。
    const updateLayoutMode = (width: number) => {
      setIsCompactLayout((current) => {
        const next = width < 860;
        return current === next ? current : next;
      });
    };

    updateLayoutMode(viewport.getBoundingClientRect().width);
    const observer = new ResizeObserver(([entry]) => {
      updateLayoutMode(entry.contentRect.width);
    });

    observer.observe(viewport);

    return () => {
      observer.disconnect();
    };
  }, []);

  return (
    <div ref={formViewportRef} className="w-full">
      <Form className="grid w-full gap-4">
        <Tabs
          className="w-full"
          orientation={isCompactLayout ? "horizontal" : "vertical"}
          selectedKey={selectedGroupKey ?? undefined}
          onSelectionChange={(key) => {
            setSelectedGroupKey(String(key));
          }}
        >
          <div
            className={
              isCompactLayout
                ? "grid gap-4"
                : "grid w-full items-start grid-cols-[184px_minmax(0,1fr)]"
            }
          >
            <div
              className={
                isCompactLayout
                  ? "w-full overflow-x-auto border-b border-hairline px-3 pt-3"
                  : "sticky top-4 self-start border-r border-hairline pr-3"
              }
            >
              <Tabs.ListContainer>
                <Tabs.List
                  aria-label="配置分类"
                  className={
                    isCompactLayout
                      ? "flex w-max min-w-full gap-1"
                      : "grid w-full gap-1.5"
                  }
                >
                  {fieldGroups.map((group) => (
                    <Tabs.Tab
                      key={group.key}
                      id={group.key}
                      className={[
                        "h-auto min-h-0 items-center rounded-md px-3 py-2.5",
                        isCompactLayout ? "min-w-[152px]" : "justify-start",
                      ].join(" ")}
                    >
                      <span className="text-left text-body-sm font-semibold leading-5">
                        {group.title}
                      </span>
                      <Tabs.Indicator />
                    </Tabs.Tab>
                  ))}
                </Tabs.List>
              </Tabs.ListContainer>
            </div>

            {/* 只挂载当前分组，避免大 schema 的隐藏字段参与滚动期重渲染。 */}
            {selectedGroup ? (
              <Tabs.Panel
                id={selectedGroup.key}
                className={isCompactLayout ? "min-w-0 p-3 pt-0" : "min-w-0 p-1 pl-4"}
              >
                <SelectedGroupPanel
                  group={selectedGroup}
                  isCompactLayout={isCompactLayout}
                  issueLookup={issueLookup}
                  onValueChange={onValueChange}
                  values={values}
                />
              </Tabs.Panel>
            ) : null}
          </div>
        </Tabs>

        {showSupportMatrix ? (
          <PluginConfigSupportMatrix supportMatrix={schema.supportMatrix} />
        ) : null}
      </Form>
    </div>
  );
}

type SelectedGroupPanelProps = {
  group: ReturnType<typeof groupFields>[number];
  isCompactLayout: boolean;
  issueLookup: Map<string, string>;
  onValueChange: (path: string, nextValue: string) => void;
  values: Record<string, string>;
};

function SelectedGroupPanel({
  group,
  isCompactLayout,
  issueLookup,
  onValueChange,
  values,
}: SelectedGroupPanelProps) {
  return (
    <section
      id={`plugin-group-${group.key}`}
      className="grid w-full gap-3"
    >
      <Fieldset>
        <div className="grid gap-0 rounded-lg border border-hairline bg-surface">
          <Fieldset.Group className="grid gap-0 px-4">
            {group.fields.map((definition) => (
              <PluginConfigField
                key={definition.path}
                definition={definition}
                isCompactLayout={isCompactLayout}
                isInlineRow
                issue={issueLookup.get(definition.path)}
                onChange={onValueChange}
                value={values[definition.path] ?? ""}
              />
            ))}
          </Fieldset.Group>
        </div>
      </Fieldset>
    </section>
  );
}

export function buildPluginConfigPreviewPayload(
  schema: PluginConfigSchemaSnapshot,
  values: Record<string, string>,
) {
  try {
    return JSON.stringify(parseConfigDraftPayload(schema, values), null, 2);
  } catch (error) {
    if (error instanceof PluginConfigJsonFieldParseError) {
      return JSON.stringify(
        {
          error: `字段 ${error.path} 无法解析`,
        },
        null,
        2,
      );
    }

    return '{\n  "error": "存在无法解析的 JSON 字段"\n}';
  }
}

function groupFields(fields: PluginConfigFieldDefinition[]) {
  const groups = new Map<string, PluginConfigFieldDefinition[]>();

  for (const field of fields) {
    const groupKey = inferFieldGroupKey(field);
    const current = groups.get(groupKey) ?? [];
    current.push(field);
    groups.set(groupKey, current);
  }

  return Array.from(groups.entries()).map(([key, groupFields]) => ({
    key,
    title: groupTitle(key),
    fields: groupFields,
  }));
}

function inferFieldGroupKey(field: PluginConfigFieldDefinition) {
  const path = field.path.toLowerCase();
  const key = field.key.toLowerCase();

  if (
    field.sensitive ||
    key.includes("secret") ||
    key.includes("token") ||
    key.includes("api_key") ||
    key.includes("public_key") ||
    path.includes("auth.")
  ) {
    return "credentials";
  }

  if (
    key === "url" ||
    key === "feeds" ||
    key === "query" ||
    key.includes("watchlist") ||
    key.includes("source")
  ) {
    return "input";
  }

  if (
    key.includes("timeout") ||
    key.includes("headers") ||
    key.includes("user_agent") ||
    key.includes("response_bytes")
  ) {
    return "network";
  }

  if (
    key.includes("max_items") ||
    key.includes("max_results") ||
    key.includes("content") ||
    key.includes("text_length") ||
    key.includes("search_depth") ||
    key.includes("favicon")
  ) {
    return "processing";
  }

  if (key.includes("allowlist") || key.includes("include_") || key.includes("exclude_")) {
    return "scope";
  }

  if (key.includes("response_text") || key.includes("webhook") || key.includes("channel")) {
    return "notification";
  }

  if (field.path.includes(".")) {
    return field.path.split(".")[0];
  }

  return "base";
}

function groupTitle(groupKey: string) {
  if (groupKey === "base") {
    return "基础信息";
  }

  const titleMap: Record<string, string> = {
    advancedMetrics: "高级监控",
    auth: "认证配置",
    credentials: "凭证与密钥",
    deploymentZone: "部署配置",
    input: "采集输入",
    network: "请求与网络",
    notification: "通知输出",
    processing: "内容处理",
    scope: "过滤范围",
    topology: "部署拓扑",
  };

  if (titleMap[groupKey]) {
    return titleMap[groupKey];
  }

  return groupKey
    .replace(/([A-Z])/g, " $1")
    .replace(/^./, (value) => value.toUpperCase());
}
