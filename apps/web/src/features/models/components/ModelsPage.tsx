import { Button } from '@heroui/react';

import { useModelProviderPage } from '../hooks';
import { ModelPresetBoard } from './ModelPresetBoard';
import { ProviderEditorForm } from './ProviderEditorForm';
import { ProviderListPanel } from './ProviderListPanel';
import { ProviderStatusPanel } from './ProviderStatusPanel';

export function ModelsPage() {
  const page = useModelProviderPage();
  const {
    activeView,
    filteredProviders,
    hasSelectedProvider,
    invocationsQuery,
    isCreating,
    mutations,
    presetsQuery,
    providerDetails,
    providerErrorText,
    providerFilter,
    providerQuery,
    providerSearch,
    providersQuery,
    selectedProviderId,
    setActiveView,
    setProviderFilter,
    setProviderSearch,
    setSelectedProviderId,
    startCreating,
    stopCreating,
  } = page;

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">模型</p>
        <h1 className="page-title">模型配置</h1>
        <p className="page-description">
          管理多个供应商、供应商下模型，以及系统固定任务类别的默认模型与基础 fallback。
        </p>
      </section>

      <div className="mb-5 flex gap-3">
        <Button
          type="button"
          variant={activeView === 'providers' ? 'primary' : 'outline'}
          onPress={() => setActiveView('providers')}
        >
          供应商配置
        </Button>
        <Button
          type="button"
          variant={activeView === 'presets' ? 'primary' : 'outline'}
          onPress={() => setActiveView('presets')}
        >
          任务模型预设
        </Button>
      </div>

      {providerErrorText ? (
        <p className="mb-4 rounded-md border border-red-900 bg-red-950/60 px-3 py-2 text-sm text-red-300">
          Provider 列表加载失败：{providerErrorText}
        </p>
      ) : null}

      {activeView === 'providers' ? (
        <section className="grid gap-4 xl:grid-cols-[340px_minmax(460px,0.95fr)_minmax(0,1.05fr)]">
          <ProviderListPanel
            currentFilter={providerFilter}
            isLoading={providersQuery.isLoading}
            onCreate={startCreating}
            onFilterChange={setProviderFilter}
            onSearchChange={setProviderSearch}
            onSelect={(providerId) => {
              stopCreating();
              setSelectedProviderId(providerId);
            }}
            onSetDefault={(providerId) => mutations.setDefaultProvider.mutate(providerId)}
            providers={filteredProviders}
            searchValue={providerSearch}
            selectedProviderId={selectedProviderId}
            settingDefaultProviderId={mutations.setDefaultProvider.variables ?? null}
          />

          <ProviderEditorForm
            canManageModels={hasSelectedProvider}
            isCreating={isCreating}
            isLoading={providerQuery.isLoading}
            isSaving={mutations.createProvider.isPending || mutations.updateProvider.isPending}
            isTesting={mutations.testConnection.isPending}
            provider={providerQuery.data}
            saveError={mutations.createProviderErrorText ?? mutations.updateProviderErrorText}
            saveSuccess={mutations.createProvider.isSuccess || mutations.updateProvider.isSuccess}
            testError={mutations.testConnectionErrorText}
            testSuccess={mutations.testConnection.isSuccess}
            onCreateModel={(input) => mutations.createModel.mutate(input)}
            onDeleteModel={(modelId) => mutations.deleteModel.mutate(modelId)}
            onSave={(input) => {
              if (isCreating) {
                mutations.createProvider.mutate(input as never, {
                  onSuccess: (provider) => {
                    stopCreating();
                    setSelectedProviderId(provider.id);
                  },
                });
                return;
              }
              mutations.updateProvider.mutate(input as never);
            }}
            onTest={() => mutations.testConnection.mutate()}
            onUpdateModel={(modelId, input) => mutations.updateModel.mutate({ input, modelId })}
          />

          <ProviderStatusPanel
            invocations={invocationsQuery.data ?? []}
            invocationsError={invocationsQuery.isError}
            invocationsLoading={invocationsQuery.isLoading}
            provider={providerQuery.data}
          />
        </section>
      ) : (
        <ModelPresetBoard
          presets={presetsQuery.data ?? []}
          providers={providerDetails}
          updateError={mutations.updatePresetErrorText}
          updatingPresetKey={mutations.updatePreset.variables?.presetKey ?? null}
          onSavePreset={(presetKey, primaryModelId, fallbackModelId) =>
            mutations.updatePreset.mutate({
              presetKey,
              input: { primary_model_id: primaryModelId, fallback_model_id: fallbackModelId },
            })
          }
        />
      )}
    </>
  );
}
