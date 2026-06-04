import { Button, Card, Chip, Spinner, Surface } from "@heroui/react";
import { Check, RotateCcw, Save } from "lucide-react";

import { PluginConfigForm } from "@/features/plugins/config-form";

import { formatApiError } from "../../utils/plugin-detail-format";
import { usePluginConfigEditorPanel } from "../../hooks/use-plugin-config-editor-panel";

type PluginConfigEditorPanelProps = {
  pluginId: string;
};

export function PluginConfigEditorPanel({ pluginId }: PluginConfigEditorPanelProps) {
  const {
    canReset,
    config,
    draftValues,
    isDirty,
    isLoading,
    issueLookup,
    loadError,
    message,
    resetDraft,
    saveDraft,
    savePending,
    schema,
    summaryRows,
    updateDraft,
    validateDraft,
  } = usePluginConfigEditorPanel(pluginId);

  if (isLoading) {
    return (
      <div className="flex min-h-48 items-center justify-center rounded-lg border border-hairline bg-surface">
        <Spinner size="md" />
        <span className="ml-3 text-body-sm text-muted">正在准备插件配置编辑 Mock...</span>
      </div>
    );
  }

  if (loadError) {
    return (
      <Surface className="rounded-lg border border-warning/30" variant="secondary">
        <div className="p-4">
          <p className="m-0 text-title-sm font-bold text-warning">插件配置加载失败</p>
          <p className="m-0 mt-2 text-body-sm text-warning">{formatApiError(loadError)}</p>
        </div>
      </Surface>
    );
  }

  if (!schema || !config) {
    return (
      <Surface className="rounded-lg" variant="secondary">
        <div className="p-4">
          <p className="m-0 text-body-sm text-muted">当前插件没有可渲染的配置结构。</p>
        </div>
      </Surface>
    );
  }

  return (
    <div className="grid gap-4">
      <Card className="border border-hairline bg-surface shadow-sm">
        <Card.Content className="grid gap-3 p-4">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="m-0 text-title-sm font-bold text-ink">配置表单</p>
                <Chip color="warning" size="sm" variant="soft">
                  Mock
                </Chip>
                <Chip color={isDirty ? "warning" : "success"} size="sm" variant="soft">
                  {isDirty ? "有未保存改动" : "无改动"}
                </Chip>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button isDisabled={savePending} size="sm" type="button" variant="secondary" onPress={() => void validateDraft()}>
                <Check className="size-4" />
                校验
              </Button>
              <Button isDisabled={savePending || !canReset} size="sm" type="button" variant="secondary" onPress={resetDraft}>
                <RotateCcw className="size-4" />
                重置
              </Button>
              <Button isDisabled={savePending || !isDirty} size="sm" type="button" variant="primary" onPress={() => void saveDraft()}>
                <Save className="size-4" />
                {savePending ? "保存中" : "模拟保存"}
              </Button>
            </div>
          </div>

          {message ? (
            <div className="rounded-md border border-hairline bg-surface-soft px-3 py-2 text-body-sm text-muted">
              {message}
            </div>
          ) : null}

          <div className="grid gap-2 text-body-sm md:grid-cols-4">
            {summaryRows.map((row) => (
              <p key={row.label} className="m-0 rounded-md border border-hairline bg-surface-soft px-3 py-2">
                <span className="block text-[11px] font-semibold text-muted">{row.label}</span>
                <span className="mt-1 block truncate font-bold text-ink">{row.value}</span>
              </p>
            ))}
          </div>
        </Card.Content>
      </Card>

      <PluginConfigForm
        issueLookup={issueLookup}
        onValueChange={updateDraft}
        schema={schema}
        showSupportMatrix={false}
        values={draftValues}
      />
    </div>
  );
}
