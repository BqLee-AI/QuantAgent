import { Button, Input, Label, Modal, Switch, TextField, useOverlayState } from '@heroui/react';
import { useEffect, useMemo, useState } from 'react';

import type { ModelProviderModel, SaveProviderModelInput } from '../../api';

export function AddProviderModelModal({
  editingModel,
  existingModelNames,
  onSubmit,
  state,
}: {
  editingModel?: ModelProviderModel | null;
  existingModelNames: string[];
  onSubmit: (input: SaveProviderModelInput) => void;
  state: ReturnType<typeof useOverlayState>;
}) {
  const [modelId, setModelId] = useState('');
  const [supportsVision, setSupportsVision] = useState(false);
  const [enabled, setEnabled] = useState(true);

  const normalizedExistingNames = useMemo(
    () => new Set(existingModelNames.map((name) => name.toLowerCase())),
    [existingModelNames],
  );
  const trimmedModelId = modelId.trim();
  const isEditing = Boolean(editingModel);
  const isDuplicate = !isEditing && trimmedModelId ? normalizedExistingNames.has(trimmedModelId.toLowerCase()) : false;

  useEffect(() => {
    if (!state.isOpen) return;
    if (!editingModel) {
      setModelId('');
      setSupportsVision(false);
      setEnabled(true);
      return;
    }
    setModelId(editingModel.model_name);
    setSupportsVision(editingModel.supports_vision);
    setEnabled(editingModel.enabled);
  }, [editingModel, state.isOpen]);

  function submit() {
    if (!trimmedModelId || isDuplicate) return;
    onSubmit({
      enabled,
      is_global_default: editingModel?.is_global_default ?? false,
      model_name: trimmedModelId,
      supports_vision: supportsVision,
    });
    state.close();
  }

  return (
    <Modal state={state}>
      <Modal.Backdrop>
        <Modal.Container placement="center" size="lg">
          <Modal.Dialog className="w-full max-w-[min(34rem,calc(100vw-2rem))] overflow-hidden">
            <Modal.Header className="border-b border-hairline px-5 py-4">
              <Modal.Heading>{isEditing ? '编辑模型' : '添加模型'}</Modal.Heading>
              <Modal.CloseTrigger aria-label="关闭" />
            </Modal.Header>
            <Modal.Body className="px-5 py-5">
              <div className="grid gap-4">
                <InlineField
                  isDisabled={isEditing}
                  isRequired
                  label="模型ID"
                  value={modelId}
                  onChange={setModelId}
                />
                {isDuplicate ? (
                  <p className="pl-[88px] text-[12px] text-trading-down">这个模型 ID 已经存在。</p>
                ) : null}
                <Switch
                  className="items-start gap-3 rounded-lg border border-hairline bg-surface-soft px-3 py-3"
                  isSelected={enabled}
                  onChange={() => {
                    setEnabled((current) => !current);
                  }}
                >
                  <Switch.Control>
                    <Switch.Thumb />
                  </Switch.Control>
                  <Switch.Content className="gap-1">
                    <Label className="text-[13px] font-medium text-ink">启用模型</Label>
                  </Switch.Content>
                </Switch>
                <Switch
                  className="items-start gap-3 rounded-lg border border-hairline bg-surface-soft px-3 py-3"
                  isSelected={supportsVision}
                  onChange={() => {
                    setSupportsVision((current) => !current);
                  }}
                >
                  <Switch.Control>
                    <Switch.Thumb />
                  </Switch.Control>
                  <Switch.Content className="gap-1">
                    <Label className="text-[13px] font-medium text-ink">支持视觉输入</Label>
                  </Switch.Content>
                </Switch>
              </div>
            </Modal.Body>
            <Modal.Footer className="border-t border-hairline px-5 py-4">
              <Button isDisabled={!trimmedModelId || isDuplicate} variant="primary" onPress={submit}>
                {isEditing ? '完成' : '添加模型'}
              </Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}

function InlineField({
  isDisabled = false,
  isRequired = false,
  label,
  onChange,
  value,
}: {
  isDisabled?: boolean;
  isRequired?: boolean;
  label: string;
  onChange: (value: string) => void;
  value: string;
}) {
  return (
    <TextField
      className="grid items-center gap-2 sm:grid-cols-[76px_minmax(0,1fr)] sm:gap-3"
      isDisabled={isDisabled}
      value={value}
      onChange={onChange}
    >
      <Label className="text-[13px] font-medium text-ink">
        {label}
        {isRequired ? <span className="ml-1 text-trading-down">*</span> : null}
      </Label>
      <Input className={`w-full min-w-0 ${isDisabled ? 'opacity-60' : ''}`} variant="secondary" />
    </TextField>
  );
}
