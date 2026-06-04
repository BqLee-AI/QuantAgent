import { expect, test } from '@playwright/experimental-ct-react';

import { AgentRunChatPage } from '@/features/debug/agent-run-chat';
import { renderWithProviders } from '@/test/render';

const fixturesResponse = {
  code: 0,
  data: [
    {
      fixture_id: 'semiconductor-nvda-earnings',
      name: 'Semiconductor NVDA earnings chain',
      description: 'Runs the semiconductor MainAgent NVDA earnings primary/follow-up fixture.',
      scenarios: ['primary', 'media_follow_up'],
    },
  ],
  msg: 'ok',
};

const sseBody = [
  eventFrame('run.started', {
    event_id: 'evt-start',
    type: 'run.started',
    seq: 1,
    safe_summary: 'AgentRun started.',
  }),
  eventFrame('todo.updated', {
    event_id: 'evt-todo',
    type: 'todo.updated',
    seq: 2,
    payload: { todos: [{ content: 'Collect evidence', status: 'in_progress' }] },
    safe_summary: 'Todo updated.',
  }),
  eventFrame('tool.completed', {
    event_id: 'evt-tool',
    type: 'tool.completed',
    seq: 3,
    payload: { tool_name: 'search_web' },
    safe_summary: 'Public evidence search completed.',
  }),
  eventFrame('subagent.completed', {
    event_id: 'evt-subagent',
    type: 'subagent.completed',
    seq: 4,
    payload: { subagent_id: 'research', name: 'evidence_research_analyst' },
    safe_summary: 'EvidenceResearchAnalyst completed.',
  }),
  eventFrame('artifact.created', {
    event_id: 'evt-artifact',
    type: 'artifact.created',
    seq: 5,
    payload: { artifact_id: 'artifact-analysis', kind: 'industry_analysis' },
    safe_summary: 'IndustryAnalysis: NVDA 一手财报支持小仓位 dry-run 做多计划。',
  }),
  eventFrame('run.output', {
    event_id: 'evt-output',
    type: 'run.output',
    seq: 6,
    payload: { trade_decision: 'submit_dry_run_open_long' },
    safe_summary: 'NVDA first-party earnings run produced dry-run action submission.',
  }),
  eventFrame('run.completed', {
    event_id: 'evt-completed',
    type: 'run.completed',
    seq: 7,
    safe_summary: 'AgentRun completed.',
  }),
].join('');

function eventFrame(eventName: string, overrides: Record<string, unknown>): string {
  const event = {
    agent_run_id: 'run-nvda',
    created_at: '2026-06-04T20:00:00Z',
    event_id: 'evt',
    payload: {},
    safe_summary: null,
    seq: 1,
    trace_id: 'trace-nvda',
    type: eventName,
    ...overrides,
  };
  return `event: ${eventName}\nid: ${event.event_id}\ndata: ${JSON.stringify(event)}\n\n`;
}

test('streams NVDA fixture events into chat-like cards', async ({ mount, page }) => {
  await page.route('http://debug-api.test/api/v1/debug/agent-runs/fixtures', async (route) => {
    await route.fulfill({
      body: JSON.stringify(fixturesResponse),
      contentType: 'application/json',
      status: 200,
    });
  });
  await page.route('http://debug-api.test/api/v1/debug/agent-runs/fixtures/semiconductor-nvda-earnings/stream', async (route) => {
    await route.fulfill({
      body: sseBody,
      contentType: 'text/event-stream',
      status: 200,
    });
  });

  const component = await renderWithProviders(mount, <AgentRunChatPage />, {
    runtimeConfig: {
      apiBaseUrl: 'http://debug-api.test/api/v1',
    },
  });

  await expect(component.getByText('Agent Debug Chat')).toBeVisible();
  await component.getByRole('button', { name: '启动流式运行' }).click();

  await expect(component.getByText('search_web')).toBeVisible();
  await expect(component.getByText('evidence_research_analyst')).toBeVisible();
  await expect(component.getByText('industry_analysis')).toBeVisible();
  await expect(component.getByText('trade_decision: submit_dry_run_open_long')).toBeVisible();
  await expect(component.getByText('已完成')).toBeVisible();
  await expect(component.getByText(/sk-/)).toHaveCount(0);
});
