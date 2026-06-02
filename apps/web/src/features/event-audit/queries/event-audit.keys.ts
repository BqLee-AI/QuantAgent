export const eventAuditKeys = {
  root: ['event-audit'] as const,
  timeline: (eventId: string) => [...eventAuditKeys.root, 'timeline', eventId] as const,
}
