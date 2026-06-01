import {
  APPROVAL_AMEND_CAPABILITY,
  APPROVAL_APPROVE_CAPABILITY,
  BROKER_DRY_RUN_CAPABILITY,
  PLUGIN_CONFIGURE_CAPABILITY,
  PLUGIN_INSTALL_CAPABILITY,
  RUNTIME_INSPECT_CAPABILITY,
  SECRET_MANAGE_CAPABILITY,
  type Capability,
} from './capabilities'

export type WorkspaceRoutePath =
  | '/'
  | '/approvals'
  | '/events'
  | '/models'
  | '/plugins'
  | '/runtime'
  | '/settings'

export type NavVisibility = 'hidden' | 'visible'
export type ActionAvailability = 'allowed' | 'disabled-with-reason'

export interface CapabilityCheckResult {
  allowed: boolean
  missingAnyOf: Capability[]
}

export interface NavPolicyEntry {
  label: string
  requiredAnyOf: readonly Capability[]
  to: WorkspaceRoutePath
}

export interface ActionPolicyResult {
  availability: ActionAvailability
  reason?: string
}

const DEFAULT_FORBIDDEN_REASON = '当前账号没有执行该操作的权限。'

export const WORKSPACE_ROUTE_POLICY: Record<WorkspaceRoutePath, readonly Capability[]> = {
  '/': [],
  '/approvals': [APPROVAL_APPROVE_CAPABILITY, APPROVAL_AMEND_CAPABILITY],
  '/events': [RUNTIME_INSPECT_CAPABILITY],
  '/models': [SECRET_MANAGE_CAPABILITY],
  '/plugins': [PLUGIN_CONFIGURE_CAPABILITY, PLUGIN_INSTALL_CAPABILITY],
  '/runtime': [RUNTIME_INSPECT_CAPABILITY],
  '/settings': [],
}

export const NAV_POLICY: readonly NavPolicyEntry[] = [
  { label: '仪表盘', requiredAnyOf: WORKSPACE_ROUTE_POLICY['/'], to: '/' },
  { label: '事件', requiredAnyOf: WORKSPACE_ROUTE_POLICY['/events'], to: '/events' },
  { label: '审批', requiredAnyOf: WORKSPACE_ROUTE_POLICY['/approvals'], to: '/approvals' },
  { label: '运行态', requiredAnyOf: WORKSPACE_ROUTE_POLICY['/runtime'], to: '/runtime' },
  { label: '插件', requiredAnyOf: WORKSPACE_ROUTE_POLICY['/plugins'], to: '/plugins' },
  { label: '模型', requiredAnyOf: WORKSPACE_ROUTE_POLICY['/models'], to: '/models' },
  { label: '设置', requiredAnyOf: WORKSPACE_ROUTE_POLICY['/settings'], to: '/settings' },
] as const

export const ACTION_POLICY = {
  approvalAmend: [APPROVAL_AMEND_CAPABILITY],
  approvalApprove: [APPROVAL_APPROVE_CAPABILITY],
  brokerDryRun: [BROKER_DRY_RUN_CAPABILITY],
  pluginConfigure: [PLUGIN_CONFIGURE_CAPABILITY],
  pluginInstall: [PLUGIN_INSTALL_CAPABILITY],
  secretManage: [SECRET_MANAGE_CAPABILITY],
} as const

export function hasAnyCapability(
  capabilities: ReadonlySet<string>,
  requiredAnyOf: readonly Capability[],
): boolean {
  if (requiredAnyOf.length === 0) {
    return true
  }

  return requiredAnyOf.some((capability) => capabilities.has(capability))
}

export function resolveWorkspaceRoutePath(pathname: string): WorkspaceRoutePath | null {
  if (pathname === '/') {
    return '/'
  }

  const families = (Object.keys(WORKSPACE_ROUTE_POLICY) as WorkspaceRoutePath[]).filter(
    (route) => route !== '/',
  )

  const matchedFamily = families.find((family) => pathname === family || pathname.startsWith(`${family}/`))

  return matchedFamily ?? null
}

export function checkCapabilities(
  capabilities: ReadonlySet<string>,
  requiredAnyOf: readonly Capability[],
): CapabilityCheckResult {
  return {
    allowed: hasAnyCapability(capabilities, requiredAnyOf),
    missingAnyOf: requiredAnyOf.filter((capability) => !capabilities.has(capability)),
  }
}

export function canAccessWorkspaceRoute(
  capabilities: ReadonlySet<string>,
  route: WorkspaceRoutePath,
): CapabilityCheckResult {
  return checkCapabilities(capabilities, WORKSPACE_ROUTE_POLICY[route])
}

export function getNavVisibility(
  capabilities: ReadonlySet<string>,
  route: WorkspaceRoutePath,
): NavVisibility {
  return canAccessWorkspaceRoute(capabilities, route).allowed ? 'visible' : 'hidden'
}

export function listVisibleNavItems(capabilities: ReadonlySet<string>): readonly NavPolicyEntry[] {
  return NAV_POLICY.filter((item) => getNavVisibility(capabilities, item.to) === 'visible')
}

export function getActionAvailability(
  capabilities: ReadonlySet<string>,
  requiredAnyOf: readonly Capability[],
  reason = DEFAULT_FORBIDDEN_REASON,
): ActionPolicyResult {
  return hasAnyCapability(capabilities, requiredAnyOf)
    ? { availability: 'allowed' }
    : { availability: 'disabled-with-reason', reason }
}

export function getDefaultWorkspaceEntry(capabilities: ReadonlySet<string>): WorkspaceRoutePath | null {
  const firstVisible = NAV_POLICY.find((item) => getNavVisibility(capabilities, item.to) === 'visible')
  return firstVisible?.to ?? null
}
