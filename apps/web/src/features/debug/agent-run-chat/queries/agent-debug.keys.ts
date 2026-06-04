export const agentDebugQueryKeys = {
  all: ['debug', 'agent-run-chat'] as const,
  fixtures: () => [...agentDebugQueryKeys.all, 'fixtures'] as const,
};
