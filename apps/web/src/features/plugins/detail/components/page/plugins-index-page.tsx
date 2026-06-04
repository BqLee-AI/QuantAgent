import { useMemo, useState } from "react";
import { Spinner } from "@heroui/react";

import { usePluginListQuery } from "../../queries/use-plugin-detail";
import {
  formatApiError,
  formatPluginDescription,
} from "../../utils/plugin-detail-format";
import { PluginListCard } from "../list/plugin-list-card";
import { collectPluginTypes, PluginListToolbar } from "../list/plugin-list-toolbar";

const emptyPlugins: NonNullable<ReturnType<typeof usePluginListQuery>["data"]> = [];

export function PluginsIndexPage() {
  const pluginListQuery = usePluginListQuery();
  const plugins = pluginListQuery.data ?? emptyPlugins;
  const [activeType, setActiveType] = useState("all");
  const [searchValue, setSearchValue] = useState("");
  const pluginTypes = useMemo(() => collectPluginTypes(plugins), [plugins]);
  const filteredPlugins = useMemo(() => {
    const keyword = searchValue.trim().toLowerCase();

    return plugins.filter((plugin) => {
      const manifest = plugin.manifest;
      const matchesType = activeType === "all" || (manifest?.type ?? "unknown") === activeType;

      if (!matchesType) {
        return false;
      }

      if (!keyword) {
        return true;
      }

        return [
          plugin.id,
          plugin.status,
          plugin.source,
          manifest?.name,
          manifest?.description,
          formatPluginDescription(plugin.id, manifest?.description),
          manifest?.type,
          manifest?.version,
        ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword));
    });
  }, [activeType, plugins, searchValue]);

  return (
    <div className="grid gap-5">
      <section className="page-header">
        <h1 className="m-0 text-[30px] font-extrabold leading-[1.15] text-ink">插件治理</h1>
      </section>

      <PluginListToolbar
        activeType={activeType}
        onRefresh={() => {
          void pluginListQuery.refetch();
        }}
        onSearchChange={setSearchValue}
        onTypeChange={setActiveType}
        searchValue={searchValue}
        types={pluginTypes}
      />

      {pluginListQuery.isLoading ? (
        <div className="flex min-h-40 items-center justify-center rounded-lg border border-hairline bg-surface">
          <Spinner size="md" />
          <span className="ml-3 text-body-sm text-muted">正在加载插件列表...</span>
        </div>
      ) : null}

      {pluginListQuery.isError ? (
        <div className="rounded-lg border border-warning/30 bg-warning/10 p-4 text-body-sm text-warning">
          插件列表接口暂不可用：{formatApiError(pluginListQuery.error)}
        </div>
      ) : null}

      {!pluginListQuery.isLoading && !pluginListQuery.isError && plugins.length === 0 ? (
        <div className="rounded-lg border border-hairline bg-surface p-5">
          <p className="m-0 text-title-sm font-bold text-ink">插件注册表当前没有插件记录</p>
          <p className="m-0 mt-2 text-body-sm text-muted">
            请确认后端 Registry 已扫描官方插件目录和 runtime/plugins。
          </p>
        </div>
      ) : null}

      {!pluginListQuery.isLoading &&
      !pluginListQuery.isError &&
      plugins.length > 0 &&
      filteredPlugins.length === 0 ? (
        <div className="rounded-lg border border-hairline bg-surface p-5">
          <p className="m-0 text-title-sm font-bold text-ink">没有匹配的插件</p>
          <p className="m-0 mt-2 text-body-sm text-muted">调整类型筛选或搜索关键词后重试。</p>
        </div>
      ) : null}

      {filteredPlugins.length > 0 ? (
        <section className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3 min-[1800px]:grid-cols-4 min-[2200px]:grid-cols-5">
          {filteredPlugins.map((plugin) => (
            <PluginListCard key={plugin.id} plugin={plugin} />
          ))}
        </section>
      ) : null}
    </div>
  );
}
