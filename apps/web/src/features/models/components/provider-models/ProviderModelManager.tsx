import { Button, Chip, Input, TextField, useOverlayState } from '@heroui/react';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import { useMemo, useState } from 'react';

import type { ModelProviderModel, RemoteProviderModel, SaveProviderModelInput } from '../../api';
import { AddProviderModelModal } from './ProviderModelModal';
import { FetchProviderModelsModal } from './ProviderRemoteModelsModal';

interface ProviderModelManagerProps {
  isBusy: boolean;
  models: ModelProviderModel[];
  providerName: string;
  onCreateModel: (input: SaveProviderModelInput) => void;
  onDeleteModel: (modelId: number) => void;
  onFetchModelList: () => Promise<boolean>;
  onFetchRemoteModels: () => Promise<RemoteProviderModel[]>;
  onOpenAddModel: () => Promise<boolean>;
  onUpdateModel: (modelId: number, input: SaveProviderModelInput) => void;
}

export function ProviderModelManager({
  isBusy,
  models,
  providerName,
  onCreateModel,
  onDeleteModel,
  onFetchModelList,
  onFetchRemoteModels,
  onOpenAddModel,
  onUpdateModel,
}: ProviderModelManagerProps) {
  const [searchText, setSearchText] = useState('');
  const [editingModel, setEditingModel] = useState<ModelProviderModel | null>(null);
  const [remoteModels, setRemoteModels] = useState<RemoteProviderModel[]>([]);
  const addModelState = useOverlayState();
  const editModelState = useOverlayState();
  const fetchModelsState = useOverlayState();

  const filteredModels = useMemo(() => {
    const keyword = searchText.trim().toLowerCase();
    if (!keyword) return models;
    return models.filter((model) => model.model_name.toLowerCase().includes(keyword));
  }, [models, searchText]);

  return (
    <div className="grid gap-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <SectionTitle>模型列表</SectionTitle>
          <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-surface-card px-1.5 text-[11px] font-semibold text-muted-strong">
            {models.length}
          </span>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
          {models.length > 0 ? (
            <TextField value={searchText} onChange={setSearchText}>
              <Input className="h-8 w-full sm:w-52" placeholder="搜索模型" variant="secondary" />
            </TextField>
          ) : null}
          <div className="flex items-center gap-2">
            <Button
              isDisabled={isBusy}
              size="sm"
              type="button"
              variant="outline"
              onPress={async () => {
                const isReady = await onFetchModelList();
                if (!isReady) return;
                const fetchedModels = await onFetchRemoteModels();
                setRemoteModels(fetchedModels);
                fetchModelsState.open();
              }}
            >
              获取模型列表
            </Button>
            <Button
              isIconOnly
              aria-label="添加模型"
              isDisabled={isBusy}
              size="sm"
              type="button"
              variant="primary"
              onPress={() => {
                void onOpenAddModel().then((isReady) => {
                  if (isReady) {
                    addModelState.open();
                  }
                });
              }}
            >
              <Plus size={16} />
            </Button>
          </div>
        </div>
      </div>

      {models.length === 0 ? (
        <div className="rounded-lg border border-hairline bg-surface-soft px-4 py-8 text-center">
          <p className="text-[13px] text-muted">还没有模型。可先获取模型列表，或点右上角 + 添加自定义模型。</p>
        </div>
      ) : filteredModels.length === 0 ? (
        <div className="rounded-lg border border-hairline bg-surface-soft px-4 py-8 text-center">
          <p className="text-[13px] text-muted">没有匹配的模型</p>
        </div>
      ) : (
        <div className="grid gap-1.5 rounded-lg border border-hairline bg-surface-soft p-2">
          {filteredModels.map((model) => (
            <ProviderModelRow
              key={model.id}
              model={model}
              onDelete={() => onDeleteModel(model.id)}
              onEdit={() => {
                setEditingModel(model);
                editModelState.open();
              }}
            />
          ))}
        </div>
      )}

      <AddProviderModelModal
        existingModelNames={models.map((model) => model.model_name)}
        state={addModelState}
        onSubmit={(input) => {
          onCreateModel({
            ...input,
            is_global_default: models.length === 0,
          });
        }}
      />
      <AddProviderModelModal
        editingModel={editingModel}
        existingModelNames={models.map((model) => model.model_name)}
        state={editModelState}
        onSubmit={(input) => {
          if (!editingModel) return;
          onUpdateModel(editingModel.id, {
            ...input,
            is_global_default: editingModel.is_global_default,
          });
          setEditingModel(null);
        }}
      />
      <FetchProviderModelsModal
        existingModels={new Map(models.map((model) => [model.model_name.toLowerCase(), model]))}
        providerName={providerName}
        remoteModels={remoteModels}
        state={fetchModelsState}
        onRefresh={async () => {
          const fetchedModels = await onFetchRemoteModels();
          setRemoteModels(fetchedModels);
        }}
        onAddModel={(model) => {
          if (models.some((item) => item.model_name.toLowerCase() === model.id.toLowerCase())) return;
          onCreateModel({
            enabled: true,
            is_global_default: models.length === 0,
            model_name: model.id,
            supports_vision: model.supportsVision,
          });
        }}
        onRemoveModel={(modelId) => {
          onDeleteModel(modelId);
        }}
      />
    </div>
  );
}

function ProviderModelRow({
  model,
  onDelete,
  onEdit,
}: {
  model: ModelProviderModel;
  onDelete: () => void;
  onEdit: () => void;
}) {
  return (
    <div className="group rounded-lg bg-canvas px-3 py-2.5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 flex items-start gap-2.5">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-card text-[11px] font-semibold text-muted-strong">
            {model.model_name.charAt(0).toUpperCase()}
          </span>
          <div className="min-w-0">
            <span className="block truncate text-[13px] font-medium text-ink">{model.model_name}</span>
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              {model.is_global_default ? (
                <Chip className="bg-primary text-on-primary" size="sm" variant="soft">默认</Chip>
              ) : null}
              {model.supports_vision ? (
                <Chip size="sm" variant="soft">视觉</Chip>
              ) : null}
              {!model.enabled ? <Chip size="sm" variant="soft">已禁用</Chip> : null}
            </div>
          </div>
        </div>
        <div className="flex shrink-0 gap-1.5">
          <Button isIconOnly aria-label={`编辑模型 ${model.model_name}`} size="sm" type="button" variant="outline" onPress={onEdit}>
            <Pencil size={15} />
          </Button>
          <Button isIconOnly aria-label={`删除模型 ${model.model_name}`} size="sm" type="button" variant="danger-soft" onPress={onDelete}>
            <Trash2 size={15} />
          </Button>
        </div>
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-semibold text-ink">{children}</h3>;
}
