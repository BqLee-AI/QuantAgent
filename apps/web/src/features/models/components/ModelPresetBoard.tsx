import { Button, Chip } from '@heroui/react';

import type { ModelPresetBinding, ModelProviderDetail, ModelProviderModel } from '../api';

interface ModelPresetBoardProps {
  presets: readonly ModelPresetBinding[];
  providers: readonly ModelProviderDetail[];
  updateError: string | null;
  updatingPresetKey: string | null;
  onSavePreset: (presetKey: ModelPresetBinding['preset_key'], primaryModelId: number | null, fallbackModelId: number | null) => void;
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

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-5">
        <h2 className="text-base font-semibold text-slate-950">任务模型预设</h2>
        <p className="mt-1 text-sm text-slate-500">
          这些类别由系统固定定义。你只能为它们选择主模型和最基础 fallback。
        </p>
      </div>

      {updateError ? (
        <p className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {updateError}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {presets.map((preset) => (
          <ModelPresetCard
            key={preset.preset_key}
            candidateModels={candidateModels}
            isDisabled={updatingPresetKey !== null}
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
  isDisabled,
  isSaving,
  preset,
  onSave,
}: {
  candidateModels: Array<ModelProviderModel & { providerName: string }>;
  isDisabled: boolean;
  isSaving: boolean;
  preset: ModelPresetBinding;
  onSave: (presetKey: ModelPresetBinding['preset_key'], primaryModelId: number | null, fallbackModelId: number | null) => void;
}) {
  const supportsVisionOnly = preset.preset_key === 'multimodal';
  const availableModels = supportsVisionOnly
    ? candidateModels.filter((model) => model.supports_vision)
    : candidateModels;

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-950">{preset.title}</h3>
            <Chip color={preset.status === 'configured' ? 'success' : preset.status === 'invalid' ? 'danger' : 'warning'} size="sm" variant="soft">
              {preset.status === 'configured' ? '已配置' : preset.status === 'invalid' ? '异常' : '待配置'}
            </Chip>
          </div>
          <p className="mt-1 text-sm text-slate-500">{preset.description}</p>
        </div>
      </div>

      <div className="grid gap-3">
        <ModelSelectRow
          isDisabled={isDisabled}
          label="主模型"
          models={availableModels}
          selectedModelId={preset.primary_model?.id ?? null}
          onSelect={(modelId) => onSave(preset.preset_key, modelId, preset.fallback_model?.id ?? null)}
        />
        <ModelSelectRow
          isDisabled={isDisabled}
          label="Fallback"
          models={availableModels}
          selectedModelId={preset.fallback_model?.id ?? null}
          onSelect={(modelId) => onSave(preset.preset_key, preset.primary_model?.id ?? null, modelId)}
        />
      </div>

      <div className="mt-4 flex items-center justify-between gap-3">
        <div className="text-xs text-slate-500">
          {preset.validation_message ?? '运行顺序：主模型 -> fallback -> 全局默认模型'}
        </div>
        <Button isDisabled variant="outline">
          {isSaving ? '保存中...' : '已自动保存'}
        </Button>
      </div>
    </div>
  );
}

function ModelSelectRow({
  isDisabled,
  label,
  models,
  selectedModelId,
  onSelect,
}: {
  isDisabled: boolean;
  label: string;
  models: Array<ModelProviderModel & { providerName: string }>;
  selectedModelId: number | null;
  onSelect: (modelId: number | null) => void;
}) {
  return (
    <div>
      <p className="mb-2 text-xs font-medium uppercase tracking-normal text-slate-500">{label}</p>
      <div className="grid gap-2">
        <button
          className={
            selectedModelId === null
              ? 'rounded-md border border-blue-500 bg-blue-50 px-3 py-2 text-left text-sm text-slate-950'
              : 'rounded-md border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-600 hover:border-slate-300'
          }
          disabled={isDisabled}
          type="button"
          onClick={() => {
            if (isDisabled) {
              return;
            }
            onSelect(null);
          }}
        >
          不设置
        </button>
        {models.map((model) => (
          <button
            key={model.id}
            className={
              selectedModelId === model.id
                ? 'rounded-md border border-blue-500 bg-blue-50 px-3 py-2 text-left'
                : 'rounded-md border border-slate-200 bg-white px-3 py-2 text-left hover:border-slate-300'
            }
            disabled={isDisabled}
            type="button"
            onClick={() => {
              if (isDisabled) {
                return;
              }
              onSelect(model.id);
            }}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-slate-950">{model.model_name}</div>
                <div className="truncate text-xs text-slate-500">{model.providerName}</div>
              </div>
              <div className="flex shrink-0 gap-2">
                {model.is_global_default ? <Chip color="accent" size="sm" variant="soft">全局默认</Chip> : null}
                {model.supports_vision ? <Chip color="accent" size="sm" variant="soft">视觉</Chip> : null}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
