import { describe, expect, it } from 'vitest'

import {
  APPROVAL_APPROVE_CAPABILITY,
  PLUGIN_CONFIGURE_CAPABILITY,
  RUNTIME_INSPECT_CAPABILITY,
  SECRET_MANAGE_CAPABILITY,
} from './capabilities'
import {
  ACTION_POLICY,
  canAccessWorkspaceRoute,
  getActionAvailability,
  getDefaultWorkspaceEntry,
  getNavVisibility,
  listVisibleNavItems,
} from './policy'

describe('capability policy', () => {
  it('allows runtime routes when runtime.inspect is present', () => {
    const capabilities = new Set<string>([RUNTIME_INSPECT_CAPABILITY])

    expect(canAccessWorkspaceRoute(capabilities, '/events')).toMatchObject({
      allowed: true,
    })
    expect(getNavVisibility(capabilities, '/runtime')).toBe('visible')
  })

  it('treats missing route capability as forbidden instead of unauthorized', () => {
    const capabilities = new Set<string>([PLUGIN_CONFIGURE_CAPABILITY])

    expect(canAccessWorkspaceRoute(capabilities, '/events')).toEqual({
      allowed: false,
      missingAnyOf: [RUNTIME_INSPECT_CAPABILITY],
    })
  })

  it('returns only visible nav items from the shared policy', () => {
    const capabilities = new Set<string>([RUNTIME_INSPECT_CAPABILITY, APPROVAL_APPROVE_CAPABILITY])

    expect(listVisibleNavItems(capabilities).map((item) => item.to)).toEqual([
      '/events',
      '/runtime',
      '/approvals',
      '/skills',
      '/tools',
      '/industries',
    ])
  })

  it('chooses the first visible workspace entry as the default route', () => {
    const capabilities = new Set<string>([SECRET_MANAGE_CAPABILITY])

    expect(getDefaultWorkspaceEntry(capabilities)).toBe('/settings')
  })

  it('returns disabled-with-reason for forbidden actions', () => {
    const capabilities = new Set<string>([RUNTIME_INSPECT_CAPABILITY])

    expect(getActionAvailability(capabilities, ACTION_POLICY.secretManage)).toEqual({
      availability: 'disabled-with-reason',
      reason: '当前账号没有执行该操作的权限。',
    })
  })
})
