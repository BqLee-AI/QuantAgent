import { useAgentRunChatPage } from '../../hooks';
import { AgentRunControls } from '../controls/AgentRunControls';
import { AgentRunMessageList } from '../conversation/AgentRunMessageList';
import { AgentRunStatusBar } from '../status/AgentRunStatusBar';
import { AgentRunFixtureErrorState, AgentRunFixtureLoadingState } from '../states/AgentRunChatState';

export function AgentRunChatPage() {
  const page = useAgentRunChatPage();

  return (
    <div className="grid gap-4">
      <section className="page-header">
        <p className="page-kicker">仅开发环境</p>
        <h1 className="page-title">Agent Debug Chat</h1>
        <p className="page-description">
          以对话流观察 NVDA earnings fixture 的 MainAgent、SubAgent、tool、artifact 和最终输出。
        </p>
      </section>

      {page.isLoadingFixtures ? <AgentRunFixtureLoadingState /> : null}
      {page.fixturesError ? <AgentRunFixtureErrorState message={page.fixturesError} /> : null}

      {!page.isLoadingFixtures && !page.fixturesError ? (
        <>
          <AgentRunControls
            canStart={page.canStart}
            fixtures={page.fixtures}
            selectedFixtureId={page.selectedFixtureId}
            selectedScenario={page.selectedScenario}
            status={page.state.status}
            onAbort={page.abortRun}
            onFixtureChange={page.setSelectedFixtureId}
            onScenarioChange={page.setSelectedScenario}
            onStart={page.startRun}
          />
          <AgentRunStatusBar state={page.state} />
          <section className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_18rem]">
            <div className="min-h-[26rem] rounded-xl border border-hairline bg-surface-soft p-3">
              <AgentRunMessageList messages={page.state.messages} />
            </div>
            <aside className="rounded-xl border border-hairline bg-canvas px-4 py-3 text-[13px] text-muted-strong">
              <h2 className="m-0 text-[14px] font-semibold text-ink">调试边界</h2>
              <div className="mt-3 grid gap-2">
                <p className="m-0">仅使用后端 safe summary 和 allowlisted payload。</p>
                <p className="m-0">不展示完整 prompt、CoT、secret、provider raw response。</p>
                <p className="m-0">当前页面只运行 dry-run fixture，不代表真实交易执行。</p>
              </div>
            </aside>
          </section>
        </>
      ) : null}
    </div>
  );
}
