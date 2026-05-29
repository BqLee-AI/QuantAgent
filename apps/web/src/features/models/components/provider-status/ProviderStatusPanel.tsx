import { Button, Chip, Modal, useOverlayState } from '@heroui/react';

import type { ModelInvocation, ModelProviderDetail } from '../../api';
import { ModelInvocationTable } from './ModelInvocationTable';

interface ProviderStatusPanelProps {
  invocations: readonly ModelInvocation[];
  invocationsError: boolean;
  invocationsLoading: boolean;
  provider: ModelProviderDetail | undefined;
}

export function ProviderStatusPanel({
  invocations,
  invocationsError,
  invocationsLoading,
  provider,
}: ProviderStatusPanelProps) {
  const detailState = useOverlayState();
  const latestInvocation = invocations[0] ?? null;
  const previewInvocations = invocations.slice(0, 2);
  const tokenTotal = invocations.reduce((sum, item) => sum + (item.token_usage.total_tokens ?? 0), 0);

  return (
    <section className="rounded-xl border border-hairline bg-canvas p-4 sm:p-5">
      <div className="mb-5">
        <h2 className="text-[15px] font-semibold text-ink">状态与统计</h2>
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-2">
        <Stat label="配置状态" value={<StatusChip value={provider?.status ?? 'loading'} />} />
        <Stat label="Key 状态" value={<StatusChip value={provider?.key_status ?? 'loading'} />} />
        <Stat label="默认 Provider" value={provider?.is_default ? '是' : '否'} />
        <Stat label="模型数量" value={String(provider?.model_count ?? 0)} />
        <Stat label="Masked key" value={provider?.masked_key ?? '-'} />
        <Stat label="累计 total tokens" value={String(tokenTotal)} />
        <Stat label="最近错误" value={provider?.last_error ?? latestInvocation?.error_summary ?? '-'} />
        <Stat label="最近预设" value={latestInvocation?.preset_key ?? '-'} />
      </div>

      <div className="rounded-lg border border-hairline bg-surface-soft p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-ink">最近调用</h3>
          </div>
          <Button
            size="sm"
            type="button"
            variant="outline"
            onPress={detailState.open}
          >
            查看更多
          </Button>
        </div>

        <div className="mt-4 grid gap-3">
          {invocationsError ? (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">模型调用记录加载失败。</p>
          ) : previewInvocations.length === 0 ? (
            <p className="rounded-md border border-hairline bg-canvas px-3 py-4 text-sm text-muted">
              {invocationsLoading ? '加载模型调用记录...' : '暂无模型调用记录。'}
            </p>
          ) : (
            previewInvocations.map((item) => (
              <InvocationPreviewCard key={`${item.id ?? item.created_at}-${item.request_id ?? 'none'}`} item={item} />
            ))
          )}
        </div>
      </div>

      <Modal state={detailState}>
        <Modal.Backdrop>
          <Modal.Container placement="center" size="lg">
            <Modal.Dialog className="w-full max-w-[min(72rem,calc(100vw-2rem))] overflow-hidden">
              <Modal.Header className="border-b border-hairline px-5 py-4">
                <Modal.Heading>模型调用记录</Modal.Heading>
                <Modal.CloseTrigger aria-label="关闭" />
              </Modal.Header>
              <Modal.Body className="px-5 py-4">
                <ModelInvocationTable
                  invocations={invocations}
                  isError={invocationsError}
                  isLoading={invocationsLoading}
                />
              </Modal.Body>
            </Modal.Dialog>
          </Modal.Container>
        </Modal.Backdrop>
      </Modal>
    </section>
  );
}

function InvocationPreviewCard({ item }: { item: ModelInvocation }) {
  return (
    <article className="rounded-lg border border-hairline bg-canvas px-4 py-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-ink">{item.model || '未记录模型'}</span>
            <StatusChip value={item.status} />
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
            <span>{item.provider_name}</span>
            <span>{new Date(item.created_at).toLocaleString()}</span>
            <span>总 tokens {item.token_usage.total_tokens ?? 0}</span>
          </div>
        </div>
        <span className="truncate text-xs text-muted sm:max-w-[16rem]">
          {item.request_id ?? '无请求 ID'}
        </span>
      </div>
      {item.error_summary ? (
        <p className="mt-3 rounded-md bg-trading-down/6 px-3 py-2 text-xs text-trading-down">
          {item.error_summary}
        </p>
      ) : null}
    </article>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-hairline bg-surface-soft px-3 py-3">
      <span className="block text-xs font-medium uppercase tracking-normal text-muted">{label}</span>
      <span className="mt-1 block break-words text-sm font-semibold text-ink">{value}</span>
    </div>
  );
}

function StatusChip({ value }: { value: string }) {
  const color = value === 'configured' || value === 'succeeded' ? 'success' : value === 'failed' ? 'danger' : 'warning';

  return (
    <Chip color={color} size="sm" variant="soft">
      {value}
    </Chip>
  );
}
