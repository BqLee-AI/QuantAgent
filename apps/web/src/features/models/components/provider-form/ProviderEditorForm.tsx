import { Button, Chip, Input, Switch, TextField, useOverlayState } from '@heroui/react';
import { type ReactNode } from 'react';

import type {
  CreateModelProviderInput,
  ModelProviderDetail,
  RemoteProviderModel,
  SaveProviderModelInput,
  UpdateModelProviderInput,
} from '../../api';
import { useProviderForm } from '../../hooks/useProviderForm';
import { type ProviderPresetDefinition } from '../../provider-presets';
import { ProviderModelManager } from '../provider-models/ProviderModelManager';
import { ConfirmActionModal } from '../shared/ConfirmActionModal';
import { ProviderAvatar } from '../shared/ProviderAvatar';

interface ProviderEditorFormProps {
  /** 是否处于新建模式（点击了未配置的预设） */
  isCreating: boolean;
  /** 当前选中的预设定义 */
  activePreset: ProviderPresetDefinition | undefined;
  createDraft?: {
    baseUrl: string;
    name: string;
  } | null;
  /** 后端返回的 provider 详情（编辑模式时非空） */
  provider: ModelProviderDetail | undefined;
  enabledOverride?: boolean;
  isLoading: boolean;
  isSaving: boolean;
  isTesting: boolean;
  isDeleting: boolean;
  isSettingDefault: boolean;
  saveError: string | null;
  statusPanel?: ReactNode;
  testError: string | null;
  testSuccess: boolean;
  onEnabledChange?: (enabled: boolean) => void;
  onDeleteProvider: () => void;
  onSetDefault: () => void;
  onSave: (input: UpdateModelProviderInput) => Promise<ModelProviderDetail>;
  onTest: (providerOverride?: ModelProviderDetail) => void;
  onCreateWithModel: (
    input: CreateModelProviderInput,
    model: SaveProviderModelInput | null,
  ) => Promise<ModelProviderDetail>;
  onCreateModel: (input: SaveProviderModelInput) => void;
  onDeleteModel: (modelId: number) => void;
  onFetchRemoteModels: () => Promise<RemoteProviderModel[]>;
  onUpdateModel: (modelId: number, input: SaveProviderModelInput) => void;
}

export function ProviderEditorForm({
  isCreating,
  activePreset,
  createDraft,
  provider,
  enabledOverride,
  isLoading,
  isSaving,
  isTesting,
  isDeleting,
  isSettingDefault,
  saveError,
  statusPanel,
  testError,
  testSuccess,
  onEnabledChange,
  onDeleteProvider,
  onSetDefault,
  onSave,
  onTest,
  onCreateWithModel,
  onCreateModel,
  onDeleteModel,
  onFetchRemoteModels,
  onUpdateModel,
}: ProviderEditorFormProps) {
  const deleteConfirmState = useOverlayState();
  const {
    apiKey,
    baseUrl,
    buildProviderInput,
    enabled,
    name,
    persistProviderIfNeeded,
    setApiKey,
    setBaseUrl,
    setEnabled,
    setName,
    submit,
  } = useProviderForm({
    activePreset,
    createDraft,
    enabledOverride,
    isCreating,
    onCreateWithModel,
    onSave,
    provider,
  });

  const canTest =
    !isTesting &&
    (isCreating || provider?.key_status === 'configured' || apiKey.trim().length > 0);
  const models = provider?.models ?? [];
  const displayName = isCreating ? (activePreset?.name ?? '自定义') : (provider?.name ?? '');
  const keyStatus = provider?.key_status;

  // 空状态
  if (!isCreating && !provider && !isLoading) {
    return (
      <section className="flex min-h-[24rem] items-center justify-center rounded-xl border border-hairline bg-canvas">
        <div className="flex flex-col items-center gap-3 py-20 text-center">
          <span className="text-3xl">📡</span>
          <p className="text-sm text-muted">选择左侧的供应商查看和编辑配置</p>
        </div>
      </section>
    );
  }

  return (
    <section className="flex min-h-[24rem] flex-col overflow-hidden rounded-xl border border-hairline bg-canvas">
      {/* Title bar */}
      <div className="flex flex-col gap-4 border-b border-hairline px-4 py-4 sm:px-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <ProviderAvatar name={displayName} size={28} />
          <h2 className="truncate text-[15px] font-semibold text-ink">{displayName}</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {!isCreating && provider ? (
            <Chip color={keyStatus === 'configured' ? 'success' : 'warning'} size="sm" variant="soft">
              {keyStatus === 'configured' ? 'Key 已配置' : '缺少 Key'}
            </Chip>
          ) : null}
          {!isCreating && provider ? (
            <Button
              isDisabled={provider.is_default || isSettingDefault || isSaving}
              size="sm"
              type="button"
              variant={provider.is_default ? 'outline' : 'primary'}
              onPress={onSetDefault}
            >
              {provider.is_default ? '默认供应商' : isSettingDefault ? '设置中...' : '设为默认'}
            </Button>
          ) : null}
          {!isCreating && provider ? (
            <Button
              isDisabled={isDeleting || isSaving}
              size="sm"
              type="button"
              variant="danger-soft"
              onPress={deleteConfirmState.open}
            >
              {isDeleting ? '删除中...' : '删除供应商'}
            </Button>
          ) : null}
          <Switch
            isSelected={enabled}
            size="sm"
            onChange={() => {
              const next = !enabled;
              setEnabled(next);
              onEnabledChange?.(next);
              void persistProviderIfNeeded({
                forceCreate: true,
                input: buildProviderInput({ enabled: next }),
              });
            }}
          >
            启用供应商
          </Switch>
        </div>
      </div>

      {!isCreating && provider ? (
        <ConfirmActionModal
          confirmLabel="删除供应商"
          description={
            <>
              确定删除供应商「{provider.name}」吗？
              <br />
              该操作会同时移除其模型配置，并清理相关预设绑定。
            </>
          }
          isConfirming={isDeleting}
          state={deleteConfirmState}
          title="删除供应商"
          tone="danger"
          onConfirm={onDeleteProvider}
        />
      ) : null}

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-4 py-5 sm:px-5">
        <form className="grid gap-6" onSubmit={submit}>
          {/* Provider Name */}
          <div>
            <SectionTitle>供应商名称</SectionTitle>
            <div className="mt-3">
              <TextField isDisabled={isLoading} value={name} onChange={(value) => setName(value)}>
                <Input
                  placeholder={activePreset?.draft.name ?? '输入供应商名称'}
                  variant="secondary"
                  onBlur={() => {
                    void persistProviderIfNeeded();
                  }}
                />
              </TextField>
            </div>
          </div>

          {/* API Host */}
          <div>
            <SectionTitle>API Host</SectionTitle>
            <div className="mt-3">
              <TextField isDisabled={isLoading} value={baseUrl} onChange={(v) => setBaseUrl(v)}>
                <Input
                  placeholder={activePreset?.draft.base_url ?? 'https://api.openai.com/v1'}
                  variant="secondary"
                  onBlur={() => {
                    void persistProviderIfNeeded();
                  }}
                />
              </TextField>
            </div>
          </div>

          {/* API Key */}
          <div>
            <SectionTitle>API Key</SectionTitle>
            <div className="mt-3">
              <TextField value={apiKey} onChange={(v) => setApiKey(v)}>
                <Input
                  onBlur={() => {
                    void persistProviderIfNeeded();
                  }}
                  placeholder="输入新的 API Key"
                  type="password"
                  variant="secondary"
                />
              </TextField>
            </div>
            {/* Check connection */}
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <Button
                isDisabled={!canTest}
                size="sm"
                type="button"
                variant="outline"
                onPress={async () => {
                  const persistedProvider = await persistProviderIfNeeded();
                  if (persistedProvider === false) return;
                  onTest(persistedProvider === true ? undefined : persistedProvider);
                }}
              >
                {isTesting ? '检测中...' : '检测连接'}
              </Button>
              {testSuccess ? (
                <span className="flex items-center gap-1.5 text-[12px] text-trading-up">
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-trading-up" />
                  连接正常
                </span>
              ) : null}
              {testError ? (
                <span className="flex items-center gap-1.5 text-[12px] text-trading-down">
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-trading-down" />
                  {testError}
                </span>
              ) : null}
            </div>
          </div>
        </form>

        <div className="mt-6 border-t border-hairline pt-6">
          {saveError ? (
            <div className="mb-3 rounded-lg border border-trading-down/25 bg-trading-down/5 px-3 py-2 text-[12px] text-trading-down">
              {saveError}
            </div>
          ) : null}
          <ProviderModelManager
            isBusy={isSaving}
            models={models}
            providerName={displayName}
            onCreateModel={onCreateModel}
            onDeleteModel={onDeleteModel}
            onFetchModelList={async () => {
              const isReady = await persistProviderIfNeeded({ forceCreate: true });
              return isReady !== false;
            }}
            onFetchRemoteModels={onFetchRemoteModels}
            onOpenAddModel={async () => {
              const isReady = await persistProviderIfNeeded({ forceCreate: true });
              return isReady !== false;
            }}
            onUpdateModel={onUpdateModel}
          />
          {statusPanel ? (
            <div className="mt-6 border-t border-hairline pt-6">
              {statusPanel}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function SectionTitle({ children }: { children: ReactNode }) {
  return <h3 className="text-sm font-semibold text-ink">{children}</h3>;
}
