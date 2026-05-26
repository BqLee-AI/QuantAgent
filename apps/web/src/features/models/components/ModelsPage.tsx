import { ModelConfigForm } from './ModelConfigForm';
import { ModelStatusPanel } from './ModelStatusPanel';
import { formatModelApiError } from '../errors';
import {
  useModelConfigQuery,
  useModelInvocationsQuery,
  useSaveModelConfigMutation,
  useTestModelConnectionMutation,
} from '../queries';

export function ModelsPage() {
  const configQuery = useModelConfigQuery();
  const invocationsQuery = useModelInvocationsQuery();
  const saveMutation = useSaveModelConfigMutation();
  const testMutation = useTestModelConnectionMutation();

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">模型</p>
        <h1 className="page-title">模型配置</h1>
        <p className="page-description">
          配置全局 OpenAI-compatible 模型供应商，执行固定连接检查并查看基础 token 统计。
        </p>
      </section>

      {configQuery.isError ? (
        <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          模型配置加载失败：{formatModelApiError(configQuery.error) ?? '未知错误'}
        </p>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[minmax(360px,0.8fr)_minmax(0,1.2fr)]">
        <ModelConfigForm
          config={configQuery.data}
          isLoading={configQuery.isLoading}
          isSaving={saveMutation.isPending}
          isTesting={testMutation.isPending}
          saveError={formatModelApiError(saveMutation.error)}
          saveSuccess={saveMutation.isSuccess}
          testError={formatModelApiError(testMutation.error)}
          testSuccess={testMutation.isSuccess}
          onSave={(input) => saveMutation.mutate(input)}
          onTest={() => testMutation.mutate()}
        />
        <ModelStatusPanel
          config={configQuery.data}
          invocations={invocationsQuery.data ?? []}
          invocationsError={invocationsQuery.isError}
          invocationsLoading={invocationsQuery.isLoading}
        />
      </section>
    </>
  );
}
