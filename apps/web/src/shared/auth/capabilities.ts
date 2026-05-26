export const RUNTIME_INSPECT_CAPABILITY = 'runtime.inspect'
export const PLUGIN_CONFIGURE_CAPABILITY = 'plugin.configure'
export const PLUGIN_INSTALL_CAPABILITY = 'plugin.install'
export const SECRET_MANAGE_CAPABILITY = 'secret.manage'
export const APPROVAL_APPROVE_CAPABILITY = 'approval.approve'
export const APPROVAL_AMEND_CAPABILITY = 'approval.amend'
export const BROKER_DRY_RUN_CAPABILITY = 'broker.dry_run'

export const ALL_CAPABILITIES = [
  RUNTIME_INSPECT_CAPABILITY,
  PLUGIN_CONFIGURE_CAPABILITY,
  PLUGIN_INSTALL_CAPABILITY,
  SECRET_MANAGE_CAPABILITY,
  APPROVAL_APPROVE_CAPABILITY,
  APPROVAL_AMEND_CAPABILITY,
  BROKER_DRY_RUN_CAPABILITY,
] as const

export type Capability = (typeof ALL_CAPABILITIES)[number]
