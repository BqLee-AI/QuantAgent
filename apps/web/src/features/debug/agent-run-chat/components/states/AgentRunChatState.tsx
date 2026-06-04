import { PageLoading } from '@/app/components/PageLoading';
import { PageEmpty } from '@/app/components/PageEmpty';

export function AgentRunFixtureLoadingState() {
  return <PageLoading message="正在加载 Agent debug fixtures..." />;
}

export function AgentRunFixtureErrorState({ message }: { message: string }) {
  return (
    <PageEmpty
      title="Agent debug API 不可用"
      description={message}
    />
  );
}
