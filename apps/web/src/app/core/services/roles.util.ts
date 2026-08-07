export const ROLE_SYSTEM_ADMIN = 'system_admin';
export const ROLE_ORGANIZATION_ADMIN = 'organization_admin';
export const ROLE_SUSTAINABILITY_MANAGER = 'sustainability_manager';
export const ROLE_ANALYST = 'analyst';
export const ROLE_VIEWER = 'viewer';

export function canManageStructure(roles: string[]): boolean {
  return hasAny(roles, ROLE_SYSTEM_ADMIN, ROLE_ORGANIZATION_ADMIN);
}

export function canManagePeriods(roles: string[]): boolean {
  return hasAny(roles, ROLE_SYSTEM_ADMIN, ROLE_ORGANIZATION_ADMIN, ROLE_SUSTAINABILITY_MANAGER);
}

export function canLockPeriod(roles: string[]): boolean {
  return canManagePeriods(roles);
}

export function canUnlockPeriod(roles: string[]): boolean {
  return hasAny(roles, ROLE_SYSTEM_ADMIN, ROLE_ORGANIZATION_ADMIN);
}

export function canWriteActivity(roles: string[]): boolean {
  return hasAny(
    roles,
    ROLE_SYSTEM_ADMIN,
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUSTAINABILITY_MANAGER,
    ROLE_ANALYST,
  );
}

export function canApproveActivity(roles: string[]): boolean {
  return hasAny(roles, ROLE_SYSTEM_ADMIN, ROLE_ORGANIZATION_ADMIN, ROLE_SUSTAINABILITY_MANAGER);
}

export function canRunImports(roles: string[]): boolean {
  return canWriteActivity(roles);
}

export function canManageReferenceData(roles: string[]): boolean {
  return hasAny(roles, ROLE_SYSTEM_ADMIN);
}

/** CBAM / SKDM view capability — baseline roles matching backend cbam:view. */
export function canViewCbam(roles: string[]): boolean {
  return hasAny(
    roles,
    ROLE_SYSTEM_ADMIN,
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUSTAINABILITY_MANAGER,
    ROLE_ANALYST,
    ROLE_VIEWER,
  );
}

export const CBAM_VIEW_ROLES = [
  ROLE_SYSTEM_ADMIN,
  ROLE_ORGANIZATION_ADMIN,
  ROLE_SUSTAINABILITY_MANAGER,
  ROLE_ANALYST,
  ROLE_VIEWER,
] as const;

export function canManageFactorPreferences(roles: string[]): boolean {
  return hasAny(roles, ROLE_SYSTEM_ADMIN, ROLE_ORGANIZATION_ADMIN, ROLE_SUSTAINABILITY_MANAGER);
}

export function canCalculateInventory(roles: string[]): boolean {
  return hasAny(roles, ROLE_SYSTEM_ADMIN, ROLE_ORGANIZATION_ADMIN, ROLE_SUSTAINABILITY_MANAGER);
}

export function canApproveInventory(roles: string[]): boolean {
  return hasAny(roles, ROLE_SYSTEM_ADMIN, ROLE_ORGANIZATION_ADMIN);
}

export function canCreateInventory(roles: string[]): boolean {
  return canWriteActivity(roles);
}

export function activityWorkflowActions(
  status: string,
  roles: string[],
): Array<'submit' | 'approve' | 'reject' | 'correct' | 'archive'> {
  const actions: Array<'submit' | 'approve' | 'reject' | 'correct' | 'archive'> = [];
  if (status === 'draft' && canWriteActivity(roles)) {
    actions.push('submit');
  }
  if (status === 'submitted' && canApproveActivity(roles)) {
    actions.push('approve', 'reject');
  }
  if (status === 'approved' && canApproveActivity(roles)) {
    actions.push('correct');
  }
  if (
    ['draft', 'rejected', 'approved', 'submitted'].includes(status) &&
    canApproveActivity(roles)
  ) {
    actions.push('archive');
  }
  return actions;
}

function hasAny(roles: string[], ...allowed: string[]): boolean {
  return allowed.some((role) => roles.includes(role));
}
