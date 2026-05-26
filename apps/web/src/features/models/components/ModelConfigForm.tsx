import { Button, Input, Label, Switch, TextField } from '@heroui/react';
import { useEffect, useState, type FormEvent } from 'react';

import type { ModelConfig, SaveModelConfigInput } from '../api';

interface ModelConfigFormProps {
  config: ModelConfig | undefined;
  isLoading: boolean;
  isSaving: boolean;
  isTesting: boolean;
  saveError: string | null;
  saveSuccess: boolean;
  testError: string | null;
  testSuccess: boolean;
  onSave: (input: SaveModelConfigInput) => void;
  onTest: () => void;
}

export function ModelConfigForm({
  config,
  isLoading,
  isSaving,
  isTesting,
  onSave,
  onTest,
  saveError,
  saveSuccess,
  testError,
  testSuccess,
}: ModelConfigFormProps) {
  const [name, setName] = useState('OpenAI Compatible');
  const [baseUrl, setBaseUrl] = useState('');
  const [model, setModel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    if (!config) {
      return;
    }

    setName(config.name);
    setBaseUrl(config.base_url ?? '');
    setModel(config.model);
    setEnabled(config.enabled);
    setApiKey('');
  }, [config]);

  function submitConfig(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSave({
      api_key: apiKey.trim() || null,
      base_url: baseUrl.trim() || null,
      enabled,
      model: model.trim(),
      name: name.trim(),
      provider_type: 'openai_compatible',
    });
  }

  const canSave = Boolean(name.trim() && model.trim()) && !isSaving;
  const canTest = config?.key_status === 'configured' && !isTesting;

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-5">
        <h2 className="text-base font-semibold text-slate-950">全局模型供应商</h2>
        <p className="mt-1 text-sm text-slate-500">
          API key 只用于写入更新；已配置时不会从后端读取明文。
        </p>
      </div>

      <form className="grid gap-4" onSubmit={submitConfig}>
        <ModelTextField isDisabled label="Provider type" value="openai_compatible" />
        <ModelTextField isRequired isDisabled={isLoading} label="显示名称" value={name} onChange={setName} />
        <ModelTextField
          isDisabled={isLoading}
          label="Base URL"
          placeholder="https://api.openai.com/v1"
          value={baseUrl}
          onChange={setBaseUrl}
        />
        <ModelTextField isRequired isDisabled={isLoading} label="Model" value={model} onChange={setModel} />
        <ModelTextField
          label="API key"
          placeholder={config?.masked_key ? '已配置，输入新 key 可覆盖' : '输入 API key'}
          type="password"
          value={apiKey}
          onChange={setApiKey}
        />
        <Switch isSelected={enabled} onChange={setEnabled}>
          启用模型配置
        </Switch>

        <div className="flex flex-wrap gap-3 pt-1">
          <Button isDisabled={!canSave} type="submit" variant="primary">
            {isSaving ? '保存中...' : '保存配置'}
          </Button>
          <Button isDisabled={!canTest} type="button" variant="outline" onPress={onTest}>
            {isTesting ? '检查中...' : '测试连接'}
          </Button>
        </div>

        <FeedbackMessage tone="success" value={saveSuccess ? '配置已保存。' : null} />
        <FeedbackMessage tone="success" value={testSuccess ? '连接检查完成。' : null} />
        <FeedbackMessage tone="danger" value={saveError} />
        <FeedbackMessage tone="danger" value={testError} />
      </form>
    </section>
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
