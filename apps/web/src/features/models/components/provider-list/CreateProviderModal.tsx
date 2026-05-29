import { Button, Input, Label, ListBox, Modal, Select, TextField, useOverlayState } from '@heroui/react';
import { useEffect, useMemo, useState } from 'react';

const providerTypeOptions = [
  { key: 'openai', label: 'OpenAI', draftName: 'OpenAI', presetId: 'openai', baseUrl: 'https://api.openai.com/v1' },
  { key: 'openai-response', label: 'OpenAI-Response', draftName: 'OpenAI Response', presetId: 'custom', baseUrl: '' },
  { key: 'gemini', label: 'Gemini', draftName: 'Gemini', presetId: 'custom', baseUrl: '' },
  { key: 'anthropic', label: 'Anthropic', draftName: 'Anthropic', presetId: 'anthropic', baseUrl: 'https://api.anthropic.com/v1' },
  { key: 'azure-openai', label: 'Azure OpenAI', draftName: 'Azure OpenAI', presetId: 'custom', baseUrl: '' },
  { key: 'new-api', label: 'New API', draftName: 'New API', presetId: 'custom', baseUrl: '' },
  { key: 'cherry-studio', label: 'CherryIN', draftName: 'CherryIN', presetId: 'custom', baseUrl: '' },
  { key: 'ollama', label: 'Ollama', draftName: 'Ollama', presetId: 'custom', baseUrl: 'http://localhost:11434/v1' },
] as const;

export interface CreateProviderDraft {
  baseUrl: string;
  name: string;
  presetId: string;
  providerTypeKey: string;
}

interface CreateProviderModalProps {
  existingNames: string[];
  onSubmit: (draft: CreateProviderDraft) => void;
  state: ReturnType<typeof useOverlayState>;
}

export function CreateProviderModal({
  existingNames,
  onSubmit,
  state,
}: CreateProviderModalProps) {
  const [name, setName] = useState('');
  const [providerTypeKey, setProviderTypeKey] = useState<string>(providerTypeOptions[0].key);

  const normalizedExistingNames = useMemo(
    () => new Set(existingNames.map((item) => item.trim().toLowerCase())),
    [existingNames],
  );

  const trimmedName = name.trim();
  const isDuplicate = trimmedName ? normalizedExistingNames.has(trimmedName.toLowerCase()) : false;
  const selectedType = providerTypeOptions.find((item) => item.key === providerTypeKey) ?? providerTypeOptions[0];

  useEffect(() => {
    if (!state.isOpen) return;
    const fallback = providerTypeOptions[0];
    setProviderTypeKey(fallback.key);
    setName(fallback.draftName);
  }, [state.isOpen]);

  function submit() {
    if (!trimmedName || isDuplicate) return;
    onSubmit({
      baseUrl: selectedType.baseUrl,
      name: trimmedName,
      presetId: selectedType.presetId,
      providerTypeKey,
    });
    state.close();
  }

  return (
    <Modal state={state}>
      <Modal.Backdrop>
        <Modal.Container placement="center" size="lg">
          <Modal.Dialog className="w-full max-w-[min(36rem,calc(100vw-2rem))] overflow-hidden">
            <Modal.Header className="border-b border-hairline px-5 py-4">
              <Modal.Heading>新增供应商</Modal.Heading>
              <Modal.CloseTrigger aria-label="关闭" />
            </Modal.Header>
            <Modal.Body className="px-5 py-5">
              <div className="grid gap-4">
                <TextField className="grid gap-2" value={name} onChange={setName}>
                  <Label className="text-[13px] font-medium text-ink">提供商名称</Label>
                  <Input placeholder="输入提供商名称" variant="secondary" />
                </TextField>

                <div className="grid gap-2">
                  <Label className="text-[13px] font-medium text-ink">类型</Label>
                  <Select
                    aria-label="选择提供商类型"
                    selectedKey={providerTypeKey}
                    onSelectionChange={(key) => {
                      const nextKey = key === null ? providerTypeOptions[0].key : String(key);
                      const nextType = providerTypeOptions.find((item) => item.key === nextKey) ?? providerTypeOptions[0];
                      setProviderTypeKey(nextKey);
                      if (!trimmedName || providerTypeOptions.some((item) => item.draftName === trimmedName)) {
                        setName(nextType.draftName);
                      }
                    }}
                  >
                    <Select.Trigger className="w-full">
                      <Select.Value>
                        <span className="text-[13px] text-ink">{selectedType.label}</span>
                      </Select.Value>
                      <Select.Indicator />
                    </Select.Trigger>
                    <Select.Popover>
                      <ListBox aria-label="提供商类型列表">
                        {providerTypeOptions.map((item) => (
                          <ListBox.Item key={item.key} id={item.key} textValue={item.label}>
                            <div className="py-1 text-[13px] text-ink">{item.label}</div>
                          </ListBox.Item>
                        ))}
                      </ListBox>
                    </Select.Popover>
                  </Select>
                </div>

                {isDuplicate ? (
                  <p className="text-[12px] text-trading-down">这个提供商名称已经存在。</p>
                ) : null}
              </div>
            </Modal.Body>
            <Modal.Footer className="border-t border-hairline px-5 py-4">
              <Button isDisabled={!trimmedName || isDuplicate} variant="primary" onPress={submit}>
                创建
              </Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
