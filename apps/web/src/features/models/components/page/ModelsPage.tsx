import { Button } from '@heroui/react';

import { useModelsPage } from '../../hooks/useModelsPage';
import { formatModelApiError } from '../../utils/format-model-api-error';
import { ModelPresetBoard } from '../preset-board/ModelPresetBoard';
import { ProviderEditorForm } from '../provider-form/ProviderEditorForm';
import { ProviderListPanel } from '../provider-list/ProviderListPanel';
import { ProviderStatusPanel } from '../provider-status/ProviderStatusPanel';

export function ModelsPage() {
  const page = useModelsPage();

  return (
    <div className="space-y-5">
      {/* Page header */}
      <section className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted">模型</p>
          <h1 className="mt-1 text-[28px] font-semibold tracking-[-0.03em] text-ink">模型配置</h1>
        </div>
      </section>

      {/* View switcher */}
      <div className="overflow-x-auto pb-1">
        <div className="inline-flex min-w-full gap-2 rounded-xl border border-hairline bg-canvas p-1 sm:min-w-0">
          <Button
            className="flex-1 sm:flex-none"
            type="button"
            variant={page.activeView === 'providers' ? 'primary' : 'outline'}
            onPress={() => page.setActiveView('providers')}
          >
            供应商配置
          </Button>
          <Button
            className="flex-1 sm:flex-none"
            type="button"
            variant={page.activeView === 'presets' ? 'primary' : 'outline'}
            onPress={() => page.setActiveView('presets')}
          >
            任务模型预设
          </Button>
        </div>
      </div>

      {/* Error banner */}
      {page.providersQuery.isError ? (
        <div className="rounded-lg border border-trading-down/30 bg-trading-down/5 px-4 py-2.5 text-[13px] text-trading-down">
          Provider 列表加载失败：{formatModelApiError(page.providersQuery.error) ?? '未知错误'}
        </div>
      ) : null}

      {page.activeView === 'providers' ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(18rem,22rem)_minmax(0,1fr)]">
          <div className="xl:sticky xl:top-0 xl:self-start">
            <ProviderListPanel
              isLoading={page.providersQuery.isLoading}
              onCreateProvider={page.handleCreateProvider}
              providerEnabledOverrides={page.providerEnabledOverrides}
              providers={page.providersQuery.data?.providers ?? []}
              searchValue={page.providerSearch}
              stateFilter={page.providerStateFilter}
              onSearchChange={page.setProviderSearch}
              onStateFilterChange={page.setProviderStateFilter}
              selectedKey={page.selectedKey}
              onSelectItem={page.handleSelectItem}
            />
          </div>

          <ProviderEditorForm
            isCreating={page.isCreating}
            activePreset={page.activePreset}
            createDraft={page.createDraft}
            enabledOverride={page.selectedKey ? page.providerEnabledOverrides[page.selectedKey] : undefined}
            provider={page.providerQuery.data}
            isLoading={page.providerQuery.isLoading}
            isSaving={
              page.createMutation.isPending ||
              page.createModelForProviderMutation.isPending ||
              page.updateMutation.isPending
            }
            isTesting={page.testMutation.isPending}
            isDeleting={page.deleteProviderMutation.isPending}
            isSettingDefault={page.setDefaultProviderMutation.isPending}
            saveError={
              formatModelApiError(page.createMutation.error) ??
              formatModelApiError(page.updateMutation.error) ??
              formatModelApiError(page.deleteProviderMutation.error) ??
              formatModelApiError(page.setDefaultProviderMutation.error)
            }
            testError={formatModelApiError(page.testMutation.error)}
            testSuccess={page.testMutation.isSuccess}
            onEnabledChange={page.handleEnabledChange}
            onDeleteProvider={page.handleDeleteProvider}
            onCreateWithModel={page.handleCreateWithModel}
            onSave={(input) => page.updateMutation.mutateAsync(input)}
            onSetDefault={() => {
              if (page.activeProviderId === null) return;
              page.setDefaultProviderMutation.mutate(page.activeProviderId);
            }}
            onTest={(providerOverride) => {
              void page.handleTestConnection(providerOverride);
            }}
            onCreateModel={(input) => page.createProviderModelMutation.mutate(input)}
            onDeleteModel={(modelId) => page.deleteProviderModelMutation.mutate(modelId)}
            onFetchRemoteModels={async () => {
              const provider = await page.ensureProviderForTesting();
              if (!provider) return [];
              return page.remoteModelsMutation.mutateAsync(provider.id);
            }}
            onUpdateModel={(modelId, input) => page.updateProviderModelMutation.mutate({ input, modelId })}
            statusPanel={(
              <ProviderStatusPanel
                invocations={page.invocationsQuery.data ?? []}
                invocationsError={page.invocationsQuery.isError}
                invocationsLoading={page.invocationsQuery.isLoading}
                provider={page.providerQuery.data}
              />
            )}
          />
        </div>
      ) : (
        <ModelPresetBoard
          presets={page.presetsQuery.data ?? []}
          providers={page.providerDetails}
          updateError={formatModelApiError(page.updatePresetMutation.error)}
          updatingPresetKey={page.updatePresetMutation.isPending ? (page.updatePresetMutation.variables?.presetKey ?? null) : null}
          onSavePreset={(presetKey, primaryModelId, fallbackModelId) =>
            page.updatePresetMutation.mutate({
              presetKey,
              input: { primary_model_id: primaryModelId, fallback_model_id: fallbackModelId },
            })
          }
        />
      )}
    </div>
  );
}
