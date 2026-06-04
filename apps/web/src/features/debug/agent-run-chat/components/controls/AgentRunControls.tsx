import { Button } from '@heroui/react';

import type { AgentDebugFixtureSummary, AgentDebugScenario } from '../../api';
import type { AgentRunChatStatus } from '../../types';

interface AgentRunControlsProps {
  canStart: boolean;
  fixtures: readonly AgentDebugFixtureSummary[];
  selectedFixtureId: string;
  selectedScenario: AgentDebugScenario;
  status: AgentRunChatStatus;
  onAbort: () => void;
  onFixtureChange: (fixtureId: string) => void;
  onScenarioChange: (scenario: AgentDebugScenario) => void;
  onStart: () => void;
}

export function AgentRunControls({
  canStart,
  fixtures,
  selectedFixtureId,
  selectedScenario,
  status,
  onAbort,
  onFixtureChange,
  onScenarioChange,
  onStart,
}: AgentRunControlsProps) {
  const selectedFixture = fixtures.find((fixture) => fixture.fixture_id === selectedFixtureId);
  const scenarios = selectedFixture?.scenarios ?? ['primary'];

  return (
    <section className="rounded-xl border border-hairline bg-canvas px-4 py-3">
      <div className="grid gap-3 lg:grid-cols-[minmax(16rem,1.2fr)_minmax(12rem,0.7fr)_auto] lg:items-end">
        <label className="grid gap-1.5 text-[12px] font-medium text-muted-strong">
          Fixture
          <select
            aria-label="Agent debug fixture"
            className="rounded-lg border border-hairline bg-surface-card px-3 py-2 text-[13px] text-ink"
            value={selectedFixtureId}
            onChange={(event) => onFixtureChange(event.currentTarget.value)}
          >
            {fixtures.map((fixture) => (
              <option key={fixture.fixture_id} value={fixture.fixture_id}>
                {fixture.name}
              </option>
            ))}
          </select>
        </label>

        <label className="grid gap-1.5 text-[12px] font-medium text-muted-strong">
          Scenario
          <select
            aria-label="Agent debug scenario"
            className="rounded-lg border border-hairline bg-surface-card px-3 py-2 text-[13px] text-ink"
            value={selectedScenario}
            onChange={(event) => {
              const value = event.currentTarget.value;
              if (value === 'primary' || value === 'media_follow_up') onScenarioChange(value);
            }}
          >
            {scenarios.map((scenario) => (
              <option key={scenario} value={scenario}>
                {scenario}
              </option>
            ))}
          </select>
        </label>

        <div className="flex flex-wrap gap-2">
          <Button isDisabled={!canStart} size="sm" type="button" variant="primary" onPress={onStart}>
            启动流式运行
          </Button>
          <Button isDisabled={status !== 'streaming'} size="sm" type="button" variant="outline" onPress={onAbort}>
            停止
          </Button>
        </div>
      </div>
    </section>
  );
}
