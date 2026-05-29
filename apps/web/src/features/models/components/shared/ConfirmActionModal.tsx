import { Button, Modal, type ModalProps, useOverlayState } from '@heroui/react';
import type { ReactNode } from 'react';

interface ConfirmActionModalProps {
  cancelLabel?: string;
  confirmLabel?: string;
  description: ReactNode;
  isConfirming?: boolean;
  state: ReturnType<typeof useOverlayState>;
  title: string;
  tone?: 'default' | 'danger';
  onConfirm: () => void;
}

export function ConfirmActionModal({
  cancelLabel = '取消',
  confirmLabel = '确认',
  description,
  isConfirming = false,
  state,
  title,
  tone = 'default',
  onConfirm,
}: ConfirmActionModalProps) {
  const confirmVariant: ModalProps['children'] extends never ? never : 'primary' | 'danger-soft' = tone === 'danger' ? 'danger-soft' : 'primary';

  return (
    <Modal state={state}>
      <Modal.Backdrop>
        <Modal.Container placement="center" size="sm">
          <Modal.Dialog className="w-full max-w-[min(28rem,calc(100vw-2rem))] overflow-hidden">
            <Modal.Header className="border-b border-hairline px-5 py-4">
              <Modal.Heading>{title}</Modal.Heading>
              <Modal.CloseTrigger aria-label="关闭" />
            </Modal.Header>
            <Modal.Body className="px-5 py-4">
              <div className="text-sm leading-6 text-muted-strong">{description}</div>
            </Modal.Body>
            <Modal.Footer className="border-t border-hairline px-5 py-4">
              <Button isDisabled={isConfirming} variant="outline" onPress={state.close}>
                {cancelLabel}
              </Button>
              <Button isDisabled={isConfirming} variant={confirmVariant} onPress={onConfirm}>
                {isConfirming ? '处理中...' : confirmLabel}
              </Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
