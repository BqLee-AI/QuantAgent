import {
  Button,
  SearchFieldClearButton,
  SearchFieldGroup,
  SearchFieldInput,
  SearchFieldRoot,
  SearchFieldSearchIcon,
} from "@heroui/react";
import {
  Bell,
  Boxes,
  Database,
  Factory,
  LineChart,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";

import type { PluginRecordResponse } from "../../../api/contracts";
import { formatPluginType } from "../../utils/plugin-detail-format";

type PluginListToolbarProps = {
  activeType: string;
  onRefresh: () => void;
  onSearchChange: (value: string) => void;
  onTypeChange: (type: string) => void;
  searchValue: string;
  types: string[];
};

export function PluginListToolbar({
  activeType,
  onRefresh,
  onSearchChange,
  onTypeChange,
  searchValue,
  types,
}: PluginListToolbarProps) {
  return (
    <section className="rounded-lg border border-hairline bg-surface p-3 shadow-sm">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          {types.map((type) => (
            <Button
              key={type}
              className="shrink-0"
              size="sm"
              type="button"
              variant={activeType === type ? "primary" : "secondary"}
              onPress={() => {
                onTypeChange(type);
              }}
            >
              <PluginTypeIcon type={type} />
              {type === "all" ? "全部" : formatPluginType(type)}
            </Button>
          ))}
        </div>

        <div className="flex w-full items-center gap-2 xl:max-w-[28rem]">
          <SearchFieldRoot
            aria-label="搜索插件"
            className="w-full"
          >
            <SearchFieldGroup className="w-full">
              <SearchFieldSearchIcon />
              <SearchFieldInput
                className="w-full"
                placeholder="搜索名称、ID、描述"
                value={searchValue}
                onChange={(event) => {
                  onSearchChange(event.target.value);
                }}
              />
              <SearchFieldClearButton />
            </SearchFieldGroup>
          </SearchFieldRoot>
          <Button className="shrink-0" size="sm" type="button" variant="secondary" onPress={onRefresh}>
            <RefreshCw className="size-4" />
            刷新
          </Button>
        </div>
      </div>
    </section>
  );
}

export function collectPluginTypes(plugins: PluginRecordResponse[]) {
  const typeSet = new Set<string>();

  for (const plugin of plugins) {
    typeSet.add(plugin.manifest?.type ?? "unknown");
  }

  const preferredOrder = [
    "all",
    "source",
    "industry",
    "strategy",
    "notification",
    "broker",
    "unknown",
  ];

  const extraTypes = Array.from(typeSet).filter((type) => !preferredOrder.includes(type)).sort();

  return [...preferredOrder, ...extraTypes];
}

function PluginTypeIcon({ type }: { type: string }) {
  if (type === "all") {
    return <Boxes className="size-4" />;
  }
  if (type === "industry") {
    return <Factory className="size-4" />;
  }
  if (type === "notification") {
    return <Bell className="size-4" />;
  }
  if (type === "source") {
    return <Database className="size-4" />;
  }
  if (type === "strategy") {
    return <LineChart className="size-4" />;
  }
  if (type === "broker") {
    return <ShieldCheck className="size-4" />;
  }

  return <Boxes className="size-4" />;
}
