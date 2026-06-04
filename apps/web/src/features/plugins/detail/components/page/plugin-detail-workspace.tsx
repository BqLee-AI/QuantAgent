import { Tabs } from "@heroui/react";

import { SourceBindingsPanel } from "../../../source-bindings/components/source-bindings-panel";
import { PluginConfigEditorPanel } from "../config/plugin-config-editor-panel";
import type {
  PluginAuditViewResponse,
  PluginDependenciesViewResponse,
  PluginDetailResponse,
  PluginHealthViewResponse,
} from "../../api/plugin-detail.contracts";
import { PluginOverviewSection } from "../sections/plugin-overview-section";
import {
  PluginConfigDependencySection,
  PluginHealthAuditOpsSection,
} from "../sections/plugin-summary-sections";

type PluginDetailWorkspaceProps = {
  auditError?: unknown;
  auditView?: PluginAuditViewResponse;
  dependenciesError?: unknown;
  dependenciesView?: PluginDependenciesViewResponse;
  detail: PluginDetailResponse;
  healthError?: unknown;
  healthView?: PluginHealthViewResponse;
};

export function PluginDetailWorkspace({
  auditError,
  auditView,
  dependenciesError,
  dependenciesView,
  detail,
  healthError,
  healthView,
}: PluginDetailWorkspaceProps) {
  return (
    <section className="grid gap-4">
      <Tabs defaultSelectedKey="overview" className="w-full">
        <Tabs.ListContainer className="bg-transparent p-0">
          <Tabs.List aria-label="插件详情视图" className="grid w-full grid-cols-5 gap-2">
            <Tabs.Tab id="overview" className="h-9 min-w-0 justify-center rounded-xl bg-transparent py-0">
              概览
              <Tabs.Indicator />
            </Tabs.Tab>
            <Tabs.Tab id="config" className="h-9 min-w-0 justify-center rounded-xl bg-transparent py-0">
              配置
              <Tabs.Indicator />
            </Tabs.Tab>
            <Tabs.Tab id="bindings" className="h-9 min-w-0 justify-center rounded-xl bg-transparent py-0">
              绑定
              <Tabs.Indicator />
            </Tabs.Tab>
            <Tabs.Tab id="capabilities" className="h-9 min-w-0 justify-center rounded-xl bg-transparent py-0">
              依赖
              <Tabs.Indicator />
            </Tabs.Tab>
            <Tabs.Tab id="health" className="h-9 min-w-0 justify-center rounded-xl bg-transparent py-0">
              健康
              <Tabs.Indicator />
            </Tabs.Tab>
          </Tabs.List>
        </Tabs.ListContainer>

        <div className="grid gap-4">
          <Tabs.Panel id="overview" className="min-w-0">
            <PluginOverviewSection detail={detail} />
          </Tabs.Panel>

          <Tabs.Panel id="config" className="min-w-0">
            <PluginConfigEditorPanel pluginId={detail.overview.plugin_id} />
          </Tabs.Panel>

          <Tabs.Panel id="bindings" className="min-w-0">
            <SourceBindingsPanel overview={detail.overview} />
          </Tabs.Panel>

          <Tabs.Panel id="capabilities" className="min-w-0">
            <PluginConfigDependencySection
              dependenciesError={dependenciesError}
              dependenciesView={dependenciesView}
              detail={detail}
            />
          </Tabs.Panel>

          <Tabs.Panel id="health" className="min-w-0">
            <PluginHealthAuditOpsSection
              auditError={auditError}
              auditView={auditView}
              detail={detail}
              healthError={healthError}
              healthView={healthView}
            />
          </Tabs.Panel>
        </div>
      </Tabs>
    </section>
  );
}
