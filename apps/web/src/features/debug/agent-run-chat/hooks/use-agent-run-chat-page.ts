import { useEffect, useMemo, useRef, useState } from 'react';

import { useAppRuntime } from '@/app/runtime';
import { ApiError } from '@/shared/api';

import { createAgentDebugApi, type AgentDebugScenario } from '../api';
import type { AgentRunChatPageModel, AgentRunChatState } from '../types';
import { useAgentDebugFixturesQuery } from '../queries';
import {
  applyAgentRunEvent,
  createInitialAgentRunChatState,
  markAgentRunAborted,
} from '../utils';

const DEFAULT_FIXTURE_ID = 'semiconductor-nvda-earnings';

function formatRunError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.requestId ? `${error.msg}（Request ID: ${error.requestId}）` : error.msg;
  }
  if (error instanceof DOMException && error.name === 'AbortError') {
    return 'Agent run stream 已停止。';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Agent run stream failed.';
}

export function useAgentRunChatPage(): AgentRunChatPageModel {
  const { apiClient } = useAppRuntime();
  const agentDebug = useMemo(() => createAgentDebugApi(apiClient), [apiClient]);
  const fixturesQuery = useAgentDebugFixturesQuery();
  const [selectedFixtureId, setSelectedFixtureId] = useState(DEFAULT_FIXTURE_ID);
  const [selectedScenario, setSelectedScenario] = useState<AgentDebugScenario>('primary');
  const [state, setState] = useState<AgentRunChatState>(() => createInitialAgentRunChatState('primary'));
  const abortControllerRef = useRef<AbortController | null>(null);

  const fixtures = fixturesQuery.data ?? [];
  const selectedFixture = useMemo(
    () => fixtures.find((fixture) => fixture.fixture_id === selectedFixtureId) ?? fixtures[0],
    [fixtures, selectedFixtureId],
  );

  useEffect(() => {
    if (!selectedFixture) return;
    if (selectedFixture.fixture_id !== selectedFixtureId) {
      setSelectedFixtureId(selectedFixture.fixture_id);
    }
    if (!selectedFixture.scenarios.includes(selectedScenario)) {
      setSelectedScenario(selectedFixture.scenarios[0] ?? 'primary');
    }
  }, [selectedFixture, selectedFixtureId, selectedScenario]);

  useEffect(() => () => {
    abortControllerRef.current?.abort();
  }, []);

  function abortRun() {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setState((current) => markAgentRunAborted(current));
  }

  function startRun() {
    const fixtureId = selectedFixture?.fixture_id ?? selectedFixtureId;
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;
    setState(createInitialAgentRunChatState(selectedScenario));

    void (async () => {
      try {
        for await (const event of agentDebug.streamFixtureRun({
          fixtureId,
          request: { scenario: selectedScenario },
          signal: controller.signal,
        })) {
          setState((current) => applyAgentRunEvent(current, event));
        }
      } catch (error) {
        if (controller.signal.aborted) {
          setState((current) => markAgentRunAborted(current));
          return;
        }
        setState((current) => ({
          ...current,
          errorSummary: formatRunError(error),
          status: 'failed',
        }));
      } finally {
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
      }
    })();
  }

  return {
    abortRun,
    canStart: Boolean(selectedFixture) && state.status !== 'streaming',
    fixtures,
    fixturesError: fixturesQuery.error ? formatRunError(fixturesQuery.error) : null,
    isLoadingFixtures: fixturesQuery.isLoading,
    selectedFixtureId: selectedFixture?.fixture_id ?? selectedFixtureId,
    selectedScenario,
    setSelectedFixtureId,
    setSelectedScenario,
    startRun,
    state,
  };
}
