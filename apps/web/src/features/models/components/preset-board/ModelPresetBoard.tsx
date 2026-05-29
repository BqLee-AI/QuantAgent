import { Chip, ListBox, Select } from '@heroui/react';

import type {
  ModelPresetBinding,
  ModelPresetKey,
  ModelPresetStatus,
  ModelProviderDetail,
  ModelProviderModel,
} from '../../api';
import { ProviderAvatar } from '../shared/ProviderAvatar';

const presetDefinitions: Array<Pick<ModelPresetBinding, 'description' | 'preset_key' | 'title'>> = [
  {
    preset_key: 'global_default',
    title: '全局默认模型',
    description: '系统兜底使用的默认模型。',
  },
  {
    preset_key: 'economy_text',
    title: '经济型模型',
    description: '用于低成本摘要、筛选和轻量提取。',
  },
  {
    preset_key: 'general_text',
    title: '通用模型',
    description: '用于日常通用文本任务。',
  },
  {
    preset_key: 'reasoning_text',
    title: '深度推理模型',
    description: '用于复杂分析和高质量推理任务。',
  },
  {
    preset_key: 'multimodal',
    title: '多模态模型',
    description: '用于图片、图表和视觉理解任务。',
  },
];

interface ModelPresetBoardProps {
  presets: readonly ModelPresetBinding[];
  providers: readonly ModelProviderDetail[];
  updateError: string | null;
  updatingPresetKey: string | null;
  onSavePreset: (
    presetKey: ModelPresetBinding['preset_key'],
    primaryModelId: number | null,
    fallbackModelId: number | null,
  ) => void;
}

export function ModelPresetBoard({
  presets,
  providers,
  updateError,
  updatingPresetKey,
  onSavePreset,
}: ModelPresetBoardProps) {
  const candidateModels = providers.flatMap((provider) =>
    provider.enabled
      ? provider.models
          .filter((model) => model.enabled)
          .map((model) => ({ ...model, providerName: provider.name }))
      : [],
  );
  const presetByKey = new Map(presets.map((preset) => [preset.preset_key, preset]));
  const presetItems: ModelPresetCardItem[] = presetDefinitions.map((definition) => {
    const binding = presetByKey.get(definition.preset_key);
    return {
      ...definition,
      primary_model: binding?.primary_model ?? null,
      fallback_model: binding?.fallback_model ?? null,
      status: binding?.status ?? (definition.preset_key === 'global_default' ? 'configured' : 'missing_primary'),
      validation_message: binding?.validation_message ?? null,
    };
  });

  return (
    <section className="rounded-xl border border-hairline bg-canvas">
      {/* Header */}
      <div className="border-b border-hairline px-5 py-3.5">
        <h2 className="text-[15px] font-semibold text-ink">任务模型预设</h2>
        <p className="mt-1 text-xs text-muted">
          这些类别由系统固定定义。你只需要为它们选择主模型。
        </p>
      </div>

      {/* Error */}
      {updateError ? (
        <div className="mx-5 mt-4 rounded-lg bg-trading-down/10 px-3 py-2 text-[13px] text-trading-down">
          {updateError}
        </div>
      ) : null}

      {/* Preset cards grid */}
      <div className="grid gap-4 p-5 lg:grid-cols-2">
        {presetItems.map((preset) => (
          <ModelPresetCard
            key={preset.preset_key}
            candidateModels={candidateModels}
            isSaving={updatingPresetKey === preset.preset_key}
            preset={preset}
            onSave={onSavePreset}
          />
        ))}
      </div>
    </section>
  );
}

function ModelPresetCard({
  candidateModels,
  isSaving,
  preset,
  onSave,
}: {
  candidateModels: Array<ModelProviderModel & { providerName: string }>;
  isSaving: boolean;
  preset: ModelPresetCardItem;
  onSave: (presetKey: ModelPresetKey, primaryModelId: number | null, fallbackModelId: number | null) => void;
}) {
  const visionOnly = preset.preset_key === 'multimodal';
  const available = visionOnly ? candidateModels.filter((m) => m.supports_vision) : candidateModels;

  return (
    <div className="rounded-lg border border-hairline bg-surface-soft p-4">
      {/* Preset header */}
      <div className="mb-4 flex items-center gap-2">
        <h3 className="text-[13px] font-semibold text-ink">{preset.title}</h3>
        <Chip
          color={preset.status === 'configured' ? 'success' : preset.status === 'invalid' ? 'danger' : 'warning'}
          size="sm"
          variant="soft"
        >
          {preset.status === 'configured' ? '已配置' : preset.status === 'invalid' ? '异常' : '待配置'}
        </Chip>
      </div>
      <p className="mb-4 text-xs text-muted">{preset.description}</p>

      <ModelSelectRow
        label="主模型"
        models={available}
        selectedModelId={preset.primary_model?.id ?? null}
        onSelect={(modelId) => onSave(preset.preset_key, modelId, preset.fallback_model?.id ?? null)}
      />
      <div className="mt-3">
        <ModelSelectRow
          label="Fallback 模型"
          models={available}
          selectedModelId={preset.fallback_model?.id ?? null}
          onSelect={(modelId) => onSave(preset.preset_key, preset.primary_model?.id ?? null, modelId)}
        />
      </div>

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="text-[11px] text-muted">
          {preset.validation_message ?? '选择后立即应用为该任务类别的主模型'}
        </span>
        <span className="text-[11px] text-muted">
          {isSaving ? '应用中...' : '选择即应用'}
        </span>
      </div>
    </div>
  );
}

interface ModelPresetCardItem {
  description: string;
  preset_key: ModelPresetKey;
  fallback_model: ModelProviderModel | null;
  primary_model: ModelProviderModel | null;
  status: ModelPresetStatus;
  title: string;
  validation_message: string | null;
}

function ModelSelectRow({
  label,
  models,
  selectedModelId,
  onSelect,
}: {
  label: string;
  models: Array<ModelProviderModel & { providerName: string }>;
  selectedModelId: number | null;
  onSelect: (modelId: number | null) => void;
}) {
  const selectedKey = selectedModelId === null ? 'none' : String(selectedModelId);
  const selectedModel = models.find((model) => model.id === selectedModelId) ?? null;

  return (
    <div>
      <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-normal text-muted">{label}</span>
      <Select
        aria-label="选择任务默认模型"
        selectedKey={selectedKey}
        onSelectionChange={(key) => {
          const nextKey = key === null ? 'none' : String(key);
          onSelect(nextKey === 'none' ? null : Number(nextKey));
        }}
      >
        <Select.Trigger className="w-full">
          <Select.Value>
            {selectedModel ? (
              <div className="flex min-w-0 items-center gap-2.5">
                <ProviderAvatar name={selectedModel.providerName} size={20} />
                <div className="min-w-0">
                  <div className="truncate text-[13px] font-medium text-ink">{selectedModel.model_name}</div>
                  <div className="truncate text-[11px] text-muted">{selectedModel.providerName}</div>
                </div>
              </div>
            ) : (
              <span className="text-[13px] text-muted">使用全局默认 / 不设置</span>
            )}
          </Select.Value>
          <Select.Indicator />
        </Select.Trigger>
        <Select.Popover>
          <ListBox aria-label="可选模型" className="max-h-80 overflow-y-auto">
            <ListBox.Item id="none" textValue="使用全局默认 / 不设置">
              <div className="py-1">
                <div className="text-[13px] font-medium text-ink">使用全局默认 / 不设置</div>
                <div className="text-[11px] text-muted">不为此任务单独指定模型</div>
              </div>
            </ListBox.Item>
            {models.map((model) => (
              <ListBox.Item key={model.id} id={String(model.id)} textValue={`${model.providerName} ${model.model_name}`}>
                <div className="flex min-w-0 items-center justify-between gap-3 py-1">
                  <div className="flex min-w-0 items-center gap-2.5">
                    <ProviderAvatar name={model.providerName} size={20} />
                    <div className="min-w-0">
                      <div className="truncate text-[13px] font-medium text-ink">{model.model_name}</div>
                      <div className="truncate text-[11px] text-muted">{model.providerName}</div>
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-1.5">
                    {model.is_global_default ? (
                      <span className="rounded-pill bg-primary px-1.5 py-0.5 text-[10px] font-bold text-on-primary">默认</span>
                    ) : null}
                    {model.supports_vision ? (
                      <span className="rounded-pill bg-violet-100 px-1.5 py-0.5 text-[10px] font-bold text-violet-700">视觉</span>
                    ) : null}
                  </div>
                </div>
              </ListBox.Item>
            ))}
          </ListBox>
        </Select.Popover>
      </Select>
      {models.length === 0 ? (
        <div className="mt-2 rounded-lg border border-hairline bg-canvas px-3 py-2 text-[12px] text-muted">
          当前没有可选模型。请先在供应商配置中获取模型列表或添加自定义模型。
        </div>
      ) : null}
    </div>
  );
}
