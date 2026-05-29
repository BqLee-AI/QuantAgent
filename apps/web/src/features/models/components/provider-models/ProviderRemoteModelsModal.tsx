import { Button, Input, Modal, TextField, useOverlayState } from '@heroui/react';
import { Minus, Plus, RefreshCw } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import type { ModelProviderModel, RemoteProviderModel } from '../../api';
import type { ProviderCatalogModel } from './shared';

export function FetchProviderModelsModal({
  existingModels,
  onAddModel,
  onRefresh,
  onRemoveModel,
  providerName,
  remoteModels,
  state,
}: {
  existingModels: Map<string, ModelProviderModel>;
  onAddModel: (model: ProviderCatalogModel) => void;
  onRefresh: () => Promise<void>;
  onRemoveModel: (modelId: number) => void;
  providerName: string;
  remoteModels: RemoteProviderModel[];
  state: ReturnType<typeof useOverlayState>;
}) {
  const [keyword, setKeyword] = useState('');
  const models = useMemo(() => normalizeRemoteModels(remoteModels), [remoteModels]);
  const filteredModels = useMemo(() => {
    const query = keyword.trim().toLowerCase();
    if (!query) return models;
    return models.filter((model) => model.id.toLowerCase().includes(query) || model.name.toLowerCase().includes(query));
  }, [models, keyword]);

  useEffect(() => {
    if (!state.isOpen) {
      setKeyword('');
    }
  }, [state.isOpen]);

  return (
    <Modal state={state}>
      <Modal.Backdrop>
        <Modal.Container placement="center" size="lg">
          <Modal.Dialog className="w-full max-w-[min(42rem,calc(100vw-2rem))] overflow-hidden">
            <Modal.Header className="border-b border-hairline px-5 py-4">
              <Modal.Heading>{providerName} 模型</Modal.Heading>
              <Modal.CloseTrigger aria-label="关闭" />
            </Modal.Header>
            <Modal.Body className="px-5 py-4">
              <div className="grid gap-4">
                <div className="flex items-center gap-2">
                  <TextField className="min-w-0 flex-1" value={keyword} onChange={setKeyword}>
                    <Input className="h-10 w-full min-w-0" placeholder="搜索模型ID或名称" variant="secondary" />
                  </TextField>
                  <Button
                    isIconOnly
                    aria-label="重新获取模型列表"
                    className="shrink-0"
                    size="sm"
                    type="button"
                    variant="outline"
                    onPress={() => {
                      void onRefresh();
                    }}
                  >
                    <RefreshCw size={16} />
                  </Button>
                </div>

                {models.length === 0 ? (
                  <EmptyState />
                ) : filteredModels.length === 0 ? (
                  <EmptyState />
                ) : (
                  <div className="max-h-[22rem] overflow-y-auto rounded-lg border border-hairline bg-surface-soft">
                    {filteredModels.map((model) => {
                      const existingModel = existingModels.get(model.id.toLowerCase());
                      const alreadyAdded = Boolean(existingModel);
                      return (
                        <div
                          key={model.id}
                          className="flex items-center justify-between gap-3 border-b border-hairline bg-canvas px-4 py-2.5 last:border-b-0"
                        >
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="truncate text-[13px] font-medium text-ink">{model.id}</p>
                              {model.supportsVision ? (
                                <span className="rounded-pill bg-violet-100 px-1.5 py-0.5 text-[10px] font-bold text-violet-700">
                                  视觉
                                </span>
                              ) : null}
                            </div>
                            <p className="truncate text-[11px] text-muted">{model.name}</p>
                          </div>
                          <Button
                            isIconOnly
                            aria-label={alreadyAdded ? `移除 ${model.id}` : `添加 ${model.id}`}
                            size="sm"
                            type="button"
                            variant="outline"
                            onPress={() => {
                              if (existingModel) {
                                onRemoveModel(existingModel.id);
                                return;
                              }
                              onAddModel(model);
                            }}
                          >
                            {alreadyAdded ? <Minus size={16} /> : <Plus size={16} />}
                          </Button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </Modal.Body>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}

function normalizeRemoteModels(remoteModels: RemoteProviderModel[]): ProviderCatalogModel[] {
  return remoteModels
    .map((model) => ({
      id: model.id,
      name: model.id,
      supportsVision: Boolean(model.supports_vision),
    }))
    .sort((a, b) => a.id.localeCompare(b.id));
}

function EmptyState() {
  return (
    <div className="rounded-lg border border-hairline bg-surface-soft px-4 py-10 text-center text-[13px] text-muted">
      没有模型
    </div>
  );
}
