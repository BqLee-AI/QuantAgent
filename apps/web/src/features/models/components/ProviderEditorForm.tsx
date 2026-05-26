import { Button, Chip, Input, Label, Switch, TextField } from '@heroui/react';
import { useEffect, useMemo, useState, type FormEvent } from 'react';

import type {
  CreateModelProviderInput,
  ModelProviderDetail,
  ModelProviderModel,
  SaveProviderModelInput,
  UpdateModelProviderInput,
} from '../api';
import { providerPresets } from '../provider-presets';

interface ProviderEditorFormProps {
  isCreating: boolean;
  isLoading: boolean;
  isSaving: boolean;
  isTesting: boolean;
  provider: ModelProviderDetail | undefined;
  saveError: string | null;
  saveSuccess: boolean;
  testError: string | null;
  testSuccess: boolean;
  onCreateModel: (input: SaveProviderModelInput) => void;
  onDeleteModel: (modelId: number) => void;
  onSave: (input: CreateModelProviderInput | UpdateModelProviderInput) => void;
  onTest: () => void;
  onUpdateModel: (modelId: number, input: SaveProviderModelInput) => void;
}

export function ProviderEditorForm({
  isCreating,
  isLoading,
  isSaving,
  isTesting,
  provider,
  saveError,
  saveSuccess,
  testError,
  testSuccess,
  onCreateModel,
  onDeleteModel,
  onSave,
  onTest,
  onUpdateModel,
}: ProviderEditorFormProps) {
  const [name, setName] = useState('OpenAI Compatible');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [enabled, setEnabled] = useState(true);
  const [isDefault, setIsDefault] = useState(false);
  const [selectedPresetId, setSelectedPresetId] = useState('openai');

  useEffect(() => {
    if (!provider) {
      const preset = providerPresets.find((item) => item.id === selectedPresetId) ?? providerPresets[0];
      setName(preset.draft.name);
      setBaseUrl(preset.draft.base_url ?? '');
      setApiKey('');
      setEnabled(true);
      setIsDefault(false);
      return;
    }

    setName(provider.name);
    setBaseUrl(provider.base_url ?? '');
    setApiKey('');
    setEnabled(provider.enabled);
    setIsDefault(provider.is_default);
  }, [provider, selectedPresetId]);

  useEffect(() => {
    if (!isCreating) {
      return;
    }
    const preset = providerPresets.find((item) => item.id === selectedPresetId);
    if (!preset) {
      return;
    }
    setName(preset.draft.name);
    setBaseUrl(preset.draft.base_url ?? '');
  }, [isCreating, selectedPresetId]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const baseInput = {
      api_key: apiKey.trim() || null,
      base_url: baseUrl.trim() || null,
      enabled,
      name: name.trim(),
      provider_type: 'openai_compatible' as const,
    };

    if (isCreating) {
      onSave({ ...baseInput, is_default: isDefault });
      return;
    }

    onSave(baseInput);
  }

  const canSave = Boolean(name.trim()) && !isSaving;
  const canTest = !isCreating && provider?.key_status === 'configured' && provider.model_count > 0 && !isTesting;
  const providerModels = useMemo(() => provider?.models ?? [], [provider]);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-5">
        <h2 className="text-base font-semibold text-slate-950">{isCreating ? '新增 Provider' : 'Provider 详情'}</h2>
        <p className="mt-1 text-sm text-slate-500">
          API key 只用于写入更新；模型列表独立维护，系统默认模型在下方选择。
        </p>
      </div>

      <form className="grid gap-4" onSubmit={submit}>
        {isCreating ? (
          <div className="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-950">选择 Provider 模板</h3>
              <p className="mt-1 text-sm text-slate-500">先用常见模板预填，再按你的网关和模型调整。</p>
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {providerPresets.map((preset) => (
                <button
                  key={preset.id}
                  className={
                    selectedPresetId === preset.id
                      ? 'rounded-lg border border-blue-500 bg-blue-50 px-3 py-3 text-left'
                      : 'rounded-lg border border-slate-200 bg-white px-3 py-3 text-left hover:border-slate-300'
                  }
                  type="button"
                  onClick={() => setSelectedPresetId(preset.id)}
                >
                  <div className="text-sm font-semibold text-slate-950">{preset.name}</div>
                  <div className="mt-1 text-xs text-slate-500">{preset.description}</div>
                  <div className="mt-2 text-xs text-slate-400">{preset.draft.base_url || '自定义地址'}</div>
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <ModelTextField isDisabled label="Provider type" value="openai_compatible" />
        <ModelTextField isRequired isDisabled={isLoading} label="显示名称" value={name} onChange={setName} />
        <ModelTextField
          isDisabled={isLoading}
          label="Base URL"
          placeholder="https://api.openai.com/v1"
          value={baseUrl}
          onChange={setBaseUrl}
        />
        {isCreating ? (
          <p className="text-xs text-slate-500">
            推荐模型：{providerPresets.find((item) => item.id === selectedPresetId)?.draft.example_model ?? 'custom-model'}
          </p>
        ) : null}
        <ModelTextField
          label="API key"
          placeholder={provider?.masked_key ? '已配置，输入新 key 可覆盖' : '输入 API key'}
          type="password"
          value={apiKey}
          onChange={setApiKey}
        />

        <div className="flex flex-wrap gap-6">
          <Switch isSelected={enabled} onChange={setEnabled}>
            启用 Provider
          </Switch>
          {isCreating ? (
            <Switch isSelected={isDefault} onChange={setIsDefault}>
              创建后设为默认 Provider
            </Switch>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-3 pt-1">
          <Button isDisabled={!canSave} type="submit" variant="primary">
            {isSaving ? '保存中...' : isCreating ? '创建 Provider' : '保存变更'}
          </Button>
          <Button isDisabled={!canTest} type="button" variant="outline" onPress={onTest}>
            {isTesting ? '检查中...' : '测试连接'}
          </Button>
        </div>

        <FeedbackMessage tone="success" value={saveSuccess ? 'Provider 已保存。' : null} />
        <FeedbackMessage tone="success" value={testSuccess ? '连接检查完成。' : null} />
        <FeedbackMessage tone="danger" value={saveError} />
        <FeedbackMessage tone="danger" value={testError} />
      </form>

      {!isCreating ? (
        <div className="mt-8 border-t border-slate-200 pt-6">
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-slate-950">模型列表</h3>
            <p className="mt-1 text-sm text-slate-500">每个 provider 下可以维护多个模型，并选择一个全局默认模型。</p>
          </div>
          <ProviderModelManager
            models={providerModels}
            onCreateModel={onCreateModel}
            onDeleteModel={onDeleteModel}
            onUpdateModel={onUpdateModel}
          />
        </div>
      ) : null}
    </section>
  );
}

function ProviderModelManager({
  models,
  onCreateModel,
  onDeleteModel,
  onUpdateModel,
}: {
  models: ModelProviderModel[];
  onCreateModel: (input: SaveProviderModelInput) => void;
  onDeleteModel: (modelId: number) => void;
  onUpdateModel: (modelId: number, input: SaveProviderModelInput) => void;
}) {
  const [newModelName, setNewModelName] = useState('');
  const [newModelVision, setNewModelVision] = useState(false);

  return (
    <div className="grid gap-4">
      <div className="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm font-medium text-slate-950">新增模型</span>
          <Button
            isDisabled={!newModelName.trim()}
            size="sm"
            type="button"
            variant="primary"
            onPress={() => {
              onCreateModel({
                model_name: newModelName.trim(),
                enabled: true,
                supports_vision: newModelVision,
                is_global_default: models.length === 0,
              });
              setNewModelName('');
              setNewModelVision(false);
            }}
          >
            添加模型
          </Button>
        </div>
        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_180px]">
          <ModelTextField
            label="模型名"
            placeholder="gpt-5.4 / deepseek-chat / qwen-plus"
            value={newModelName}
            onChange={setNewModelName}
          />
          <div className="flex items-center gap-3 rounded-md border border-slate-200 bg-white px-3 py-3">
            <Switch isSelected={newModelVision} onChange={setNewModelVision}>
              支持视觉
            </Switch>
          </div>
        </div>
      </div>

      {models.length === 0 ? (
        <p className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-4 text-sm text-slate-500">
          当前 provider 还没有模型，先添加至少一个模型后才能测试连接。
        </p>
      ) : (
        <div className="grid gap-3">
          {models.map((model) => (
            <ProviderModelRow
              key={model.id}
              model={model}
              onDelete={() => onDeleteModel(model.id)}
              onSave={(input) => onUpdateModel(model.id, input)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ProviderModelRow({
  model,
  onDelete,
  onSave,
}: {
  model: ModelProviderModel;
  onDelete: () => void;
  onSave: (input: SaveProviderModelInput) => void;
}) {
  const [modelName, setModelName] = useState(model.model_name);
  const [enabled, setEnabled] = useState(model.enabled);
  const [supportsVision, setSupportsVision] = useState(model.supports_vision);
  const [isGlobalDefault, setIsGlobalDefault] = useState(model.is_global_default);

  useEffect(() => {
    setModelName(model.model_name);
    setEnabled(model.enabled);
    setSupportsVision(model.supports_vision);
    setIsGlobalDefault(model.is_global_default);
  }, [model]);

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-slate-950">{model.model_name}</span>
          {model.is_global_default ? <Chip color="accent" size="sm" variant="soft">全局默认</Chip> : null}
          {model.supports_vision ? <Chip color="accent" size="sm" variant="soft">多模态</Chip> : null}
        </div>
        <Button size="sm" type="button" variant="danger-soft" onPress={onDelete}>
          删除
        </Button>
      </div>

      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto_auto_auto]">
        <ModelTextField label="模型名" value={modelName} onChange={setModelName} />
        <div className="flex items-center rounded-md border border-slate-200 bg-white px-3 py-3">
          <Switch isSelected={enabled} onChange={setEnabled}>启用</Switch>
        </div>
        <div className="flex items-center rounded-md border border-slate-200 bg-white px-3 py-3">
          <Switch isSelected={supportsVision} onChange={setSupportsVision}>视觉</Switch>
        </div>
        <div className="flex items-center rounded-md border border-slate-200 bg-white px-3 py-3">
          <Switch isSelected={isGlobalDefault} onChange={setIsGlobalDefault}>全局默认</Switch>
        </div>
      </div>

      <div className="mt-3 flex justify-end">
        <Button
          size="sm"
          type="button"
          variant="outline"
          onPress={() =>
            onSave({
              model_name: modelName.trim(),
              enabled,
              supports_vision: supportsVision,
              is_global_default: isGlobalDefault,
            })
          }
        >
          保存模型
        </Button>
      </div>
    </div>
  );
}

function ModelTextField({
  isDisabled,
  isRequired,
  label,
  onChange,
  placeholder,
  type = 'text',
  value,
}: {
  isDisabled?: boolean;
  isRequired?: boolean;
  label: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  type?: string;
  value: string;
}) {
  return (
    <TextField
      isDisabled={isDisabled}
      isRequired={isRequired}
      value={value}
      onChange={(nextValue) => onChange?.(nextValue)}
    >
      <Label>{label}</Label>
      <Input placeholder={placeholder} type={type} variant="secondary" />
    </TextField>
  );
}

function FeedbackMessage({ tone, value }: { tone: 'danger' | 'success'; value: string | null }) {
  if (!value) {
    return null;
  }

  return (
    <p className={tone === 'success' ? 'text-sm font-medium text-emerald-700' : 'text-sm font-medium text-red-700'}>
      {value}
    </p>
  );
}
